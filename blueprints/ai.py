"""
AI Document Analysis blueprint
"""

from flask import Blueprint, request, session, jsonify, send_file, render_template, current_app
from datetime import datetime
import os
import json
from pathlib import Path

from core.db_import import db
from models import (
    ClientDocument, ChecklistItem, DocumentChecklist, Client, 
    IncomeWorksheet, User, Attachment
)
from services.activity_logging_service import ActivityLoggingService as ActivityService
from services.ai_service import AIService
from utils.consolidated import get_session_firm_id, get_session_user_id

ai_bp = Blueprint('ai', __name__)


@ai_bp.route('/api/ai-services/status', methods=['GET'])
def ai_services_status():
    """Check the status of AI services"""
    try:
        status = AIService.get_ai_services_status(current_app.config)
        status_code = 500 if 'error' in status else 200
        return jsonify(status), status_code
        
    except Exception as e:
        return jsonify({
            'ai_services_available': False,
            'error': f'Failed to check AI service status: {str(e)}'
        }), 500


@ai_bp.route('/analyze-document/<int:document_id>', methods=['POST'])
def analyze_document(document_id):
    """Analyze a client document using AI (Azure + Gemini)"""
    from utils.consolidated import get_session_firm_id
    
    try:
        firm_id = get_session_firm_id()
        
        # Initialize AI service and perform analysis
        ai_service = AIService(current_app.config)
        results = ai_service.get_or_analyze_document(document_id, firm_id, force_reanalysis=True)
        
        return jsonify({
            'success': True,
            'message': 'Document analysis completed',
            'document_id': document_id,
            'status': results.get('status', 'completed'),
            'services_used': results.get('services_used', []),
            'confidence_score': results.get('confidence_score', 0.0)
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': f'Analysis failed: {str(e)}'}), 500


@ai_bp.route('/api/document-analysis/<int:document_id>', methods=['GET', 'POST'])
def get_document_analysis(document_id):
    """Get or trigger analysis for a document"""
    from utils.consolidated import get_session_firm_id
    
    try:
        firm_id = get_session_firm_id()
        force_reanalysis = request.args.get('force_reanalysis', 'false').lower() == 'true'
        
        # Use AI service for business logic
        ai_service = AIService(current_app.config)
        response_data = ai_service.get_or_analyze_document(document_id, firm_id, force_reanalysis)
        
        # Transform new data structure to old format for frontend compatibility
        if response_data.get('success') and 'analysis_results' in response_data:
            analysis_results = response_data['analysis_results']
            
            # Handle both string (from database) and dict (fresh analysis) formats
            if isinstance(analysis_results, str):
                try:
                    analysis_results = json.loads(analysis_results)
                except json.JSONDecodeError:
                    analysis_results = {}
            
            # Transform new structure to old format expected by frontend
            transformed_data = _transform_analysis_to_old_format(analysis_results)
            
            # Add metadata
            transformed_data.update({
                'status': 'completed',
                'cached': response_data.get('was_cached', False),
                'filename': _get_document_filename(document_id),
                'processing_notes': f"Analysis completed at {datetime.utcnow().isoformat()}"
            })
            
            return jsonify(transformed_data)
        
        return jsonify(response_data)
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500


def _transform_analysis_to_old_format(analysis_results):
    """Transform new AI service data structure to old format expected by frontend"""
    transformed = {
        'azure_result': {},
        'gemini_result': {}
    }
    
    if not analysis_results:
        return transformed
    
    # Extract from new structure
    provider_results = analysis_results.get('provider_results', {})
    combined_analysis = analysis_results.get('combined_analysis', {})
    
    # Map Azure results to original format
    azure_data = provider_results.get('Azure Document Intelligence', {})
    if azure_data and 'error' not in azure_data:
        raw_results = azure_data.get('raw_results', {})
        
        # Get structured fields from raw results
        azure_fields = raw_results.get('fields', {})
        tables_data = raw_results.get('entities', [])
        extracted_text = raw_results.get('text', '')
        confidence = raw_results.get('confidence', azure_data.get('confidence_score', 0.9))
        
        # Convert fields to key-value pairs array (original format)
        key_value_pairs = []
        if isinstance(azure_fields, dict):
            for field_name, field_data in azure_fields.items():
                if isinstance(field_data, dict):
                    value = field_data.get('value', field_data.get('content', str(field_data)))
                    key_value_pairs.append({
                        'key': field_name,
                        'value': str(value)
                    })
                else:
                    key_value_pairs.append({
                        'key': field_name,
                        'value': str(field_data)
                    })
        
        # If no structured fields found, parse key information from extracted text
        if not key_value_pairs and extracted_text:
            # Parse tax document information from OCR text
            text_lines = extracted_text.split('\n')
            
            for line in text_lines:
                line = line.strip()
                if not line:
                    continue
                
                # Parse common tax form patterns
                
                # Box amounts with $ signs (e.g., "1 Unemployment compensation $ 123,456.00")
                import re
                amount_match = re.search(r'(\d+)\s+([^$]+)\s*\$\s*([\d,]+\.?\d*)', line)
                if amount_match:
                    box_num = amount_match.group(1)
                    description = amount_match.group(2).strip()
                    amount = amount_match.group(3)
                    key_value_pairs.append({
                        'key': f'Box {box_num} - {description}',
                        'value': f'${amount}'
                    })
                    continue
                
                # TIN numbers (e.g., "PAYER'S TIN 12-3456789")
                tin_match = re.search(r"(PAYER'S TIN|RECIPIENT'S TIN)\s+([\d-]+)", line)
                if tin_match:
                    tin_type = tin_match.group(1)
                    tin_value = tin_match.group(2)
                    key_value_pairs.append({
                        'key': tin_type,
                        'value': tin_value
                    })
                    continue
                
                # Names (e.g., "RECIPIENT'S name" followed by actual name)
                if "RECIPIENT'S name" in line:
                    continue  # Skip the label line, get the actual name from next lines
                    
                # Look for recipient name (typically all caps after the label)
                if line.isupper() and len(line.split()) <= 4 and len(line) > 5:
                    # Likely a name
                    if 'RECIPIENT' not in line and 'PAYER' not in line and 'STATE' not in line:
                        key_value_pairs.append({
                            'key': "Recipient's Name",
                            'value': line
                        })
                        continue
                
                # Addresses (lines with numbers and state abbreviations)
                address_match = re.search(r'(\d+\s+[^,]+(?:,\s*APT\.?\s*\d+)?)', line)
                if address_match and any(state in line for state in [' WA ', ' CA ', ' NY ', ' TX ', ' FL ']):
                    key_value_pairs.append({
                        'key': 'Address',
                        'value': line
                    })
                    continue
                
                # Form identification
                form_match = re.search(r'Form\s+([\d-]+[A-Z]*)', line)
                if form_match:
                    key_value_pairs.append({
                        'key': 'Form Type',
                        'value': form_match.group(1)
                    })
                    continue
                
                # Tax year
                year_match = re.search(r'(?:calendar year|tax year)\s*(\d{4})', line, re.IGNORECASE)
                if year_match:
                    key_value_pairs.append({
                        'key': 'Tax Year',
                        'value': year_match.group(1)
                    })
                    continue
            
            # If still no key-value pairs, add basic summary info
            if not key_value_pairs:
                key_value_pairs.append({
                    'key': 'Document Type',
                    'value': raw_results.get('document_type', 'Tax Document')
                })
                key_value_pairs.append({
                    'key': 'Text Length',
                    'value': f'{len(extracted_text)} characters'
                })
        
        # Convert tables to original format
        tables = []
        for table in tables_data:
            if isinstance(table, dict):
                tables.append({
                    'row_count': table.get('row_count', 0),
                    'column_count': table.get('column_count', 0),
                    'cells': table.get('cells', [])
                })
        
        transformed['azure_result'] = {
            'key_value_pairs': key_value_pairs,
            'tables': tables,
            'confidence_score': confidence,
            'text_content': extracted_text
        }
    
    # Map Gemini results to original format
    gemini_data = provider_results.get('Google Gemini', {})
    if gemini_data and 'error' not in gemini_data:
        raw_results = gemini_data.get('raw_results', gemini_data)
        
        transformed['gemini_result'] = {
            'document_type': raw_results.get('document_type', 'general_document'),
            'summary': raw_results.get('summary', ''),
            'key_findings': raw_results.get('key_findings', []),
            'confidence_score': raw_results.get('confidence', gemini_data.get('confidence_score', 0.85)),
            'analysis_text': raw_results.get('analysis_text', '')
        }
    
    # Use combined analysis as fallback
    if not transformed['azure_result'] and not transformed['gemini_result'] and combined_analysis:
        # Extract from combined analysis if available
        combined_raw = combined_analysis.get('raw_results', combined_analysis)
        
        # Try to get Azure-like data from combined
        if 'text' in combined_raw or 'extracted_text' in combined_raw:
            text = combined_raw.get('text', combined_raw.get('extracted_text', ''))
            transformed['azure_result'] = {
                'key_value_pairs': _extract_fields_as_kv_pairs(combined_raw.get('fields', {})),
                'tables': [],
                'confidence_score': combined_raw.get('confidence_score', 0.8),
                'text_content': text
            }
        
        # Try to get Gemini-like data from combined
        if 'document_type' in combined_raw:
            transformed['gemini_result'] = {
                'document_type': combined_raw.get('document_type', 'general_document'),
                'summary': combined_raw.get('summary', 'Combined analysis result'),
                'key_findings': combined_raw.get('key_findings', []),
                'confidence_score': combined_raw.get('confidence_score', 0.8)
            }
    
    return transformed


def _extract_fields_as_kv_pairs(fields):
    """Convert fields dictionary to key-value pairs list"""
    kv_pairs = []
    if isinstance(fields, dict):
        for key, value_data in fields.items():
            if isinstance(value_data, dict):
                kv_pairs.append({
                    'key': key,
                    'value': value_data.get('value', str(value_data)),
                    'confidence': value_data.get('confidence', 0)
                })
            else:
                kv_pairs.append({
                    'key': key,
                    'value': str(value_data),
                    'confidence': 1.0
                })
    return kv_pairs


def _get_document_filename(document_id):
    """Get document filename from database"""
    try:
        document = ClientDocument.query.get(document_id)
        return document.original_filename if document else f'document_{document_id}'
    except:
        return f'document_{document_id}'


@ai_bp.route('/api/analyze-checklist/<int:checklist_id>', methods=['POST'])
def analyze_checklist(checklist_id):
    """Analyze all documents in a checklist"""
    from utils.consolidated import get_session_firm_id
    
    try:
        firm_id = get_session_firm_id()
        
        # Get force_reanalysis flag
        request_data = request.get_json(silent=True) or {}
        force_reanalysis = request_data.get('force_reanalysis', False)
        
        # Use AI service for business logic
        ai_service = AIService(current_app.config)
        
        # Check if AI services are available first
        if not ai_service.is_available():
            return jsonify({
                'success': False,
                'error': 'AI services not configured',
                'message': 'Please configure GEMINI_API_KEY or Azure Document Intelligence API keys to enable AI analysis',
                'ai_services_available': False,
                'analyzed_count': 0,
                'total_documents': 0
            }), 503  # Service Unavailable
        
        # Analyze all documents in checklist
        results = ai_service.analyze_checklist_documents(checklist_id, firm_id, force_reanalysis)
        
        # If no real analysis was performed, return 422 (Unprocessable Entity)
        if not results.get('success') and results.get('real_analysis_count', 0) == 0:
            return jsonify(results), 422
        
        return jsonify(results)
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': f'Analysis failed: {str(e)}'}), 500


@ai_bp.route('/api/export-checklist-analysis/<int:checklist_id>', methods=['GET'])
def export_checklist_analysis(checklist_id):
    """Export checklist analysis results"""
    from utils.consolidated import get_session_firm_id
    import tempfile
    
    try:
        firm_id = get_session_firm_id()
        
        # Use AI service for business logic
        result = AIService.export_checklist_analysis(checklist_id, firm_id)
        
        if not result['success']:
            return jsonify(result), 500
        
        # Create temporary JSON file for download
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(result['data'], temp_file, indent=2)
            temp_path = temp_file.name
        
        return send_file(
            temp_path,
            as_attachment=True,
            download_name=result['filename'],
            mimetype='application/json'
        )
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': f'Export failed: {str(e)}'}), 500


@ai_bp.route('/api/generate-income-worksheet/<int:checklist_id>', methods=['POST'])
def generate_income_worksheet(checklist_id):
    """Generate income worksheet from analyzed documents"""
    from utils.consolidated import get_session_firm_id, get_session_user_id
    
    try:
        firm_id = get_session_firm_id()
        user_id = get_session_user_id()
        
        # Use AI service for business logic
        ai_service = AIService(current_app.config)
        results = ai_service.generate_income_worksheet(checklist_id, firm_id, user_id)
        
        return jsonify(results)
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': f'Worksheet generation failed: {str(e)}'}), 500


@ai_bp.route('/download-income-worksheet/<int:checklist_id>')
def download_income_worksheet(checklist_id):
    """Download generated income worksheet"""
    from utils.consolidated import get_session_firm_id
    import tempfile
    
    try:
        firm_id = get_session_firm_id()
        
        # Use AI service for business logic
        result = AIService.get_income_worksheet_for_download(checklist_id, firm_id)
        
        if not result['success']:
            return jsonify(result), 500
        
        # Create temporary file for download
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(result['data'], temp_file, indent=2)
            temp_path = temp_file.name
        
        return send_file(
            temp_path,
            as_attachment=True,
            download_name=result['filename'],
            mimetype='application/json'
        )
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': f'Download failed: {str(e)}'}), 500


@ai_bp.route('/api/saved-income-worksheet/<int:checklist_id>')
def get_saved_income_worksheet(checklist_id):
    """Get saved income worksheet data"""
    from utils.consolidated import get_session_firm_id
    
    try:
        firm_id = get_session_firm_id()
        
        # Use AI service for business logic
        ai_service = AIService(current_app.config)
        results = ai_service.get_saved_income_worksheet(checklist_id, firm_id)
        
        if not results['success']:
            return jsonify({'error': results['message']}), 404
        
        return jsonify(results)
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': f'Failed to load worksheet: {str(e)}'}), 500


@ai_bp.route('/download-saved-worksheet/<int:worksheet_id>')
def download_saved_worksheet(worksheet_id):
    """Download a specific saved worksheet"""
    from utils.consolidated import get_session_firm_id
    import tempfile
    
    try:
        firm_id = get_session_firm_id()
        
        # Get worksheet and verify access
        worksheet = IncomeWorksheet.query.get_or_404(worksheet_id)
        checklist = worksheet.checklist
        if checklist.client.firm_id != firm_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Create temporary file for download
        worksheet_data = json.loads(worksheet.worksheet_data)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(worksheet_data, temp_file, indent=2)
            temp_path = temp_file.name
        
        return send_file(
            temp_path,
            as_attachment=True,
            download_name=f'worksheet_{worksheet_id}.json',
            mimetype='application/json'
        )
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Download failed: {str(e)}'}), 500


# Additional AI routes for document visualization and workpaper generation would go here
# These are placeholder implementations for the remaining AI features

@ai_bp.route('/create-document-visualization/<int:document_id>', methods=['POST'])
def create_document_visualization(document_id):
    """Create visualization for document analysis"""
    # Placeholder implementation
    return jsonify({
        'success': True,
        'message': 'Document visualization created',
        'visualization_id': document_id
    })


@ai_bp.route('/document-visualization/<int:document_id>')
def document_visualization(document_id):
    """Display document visualization"""
    # Placeholder implementation
    return render_template('ai/document_visualization.html', document_id=document_id)


@ai_bp.route('/generate-bulk-workpaper', methods=['POST'])
def generate_bulk_workpaper():
    """Generate bulk workpaper from multiple documents"""
    # Placeholder implementation
    return jsonify({
        'success': True,
        'message': 'Bulk workpaper generation started'
    })


@ai_bp.route('/api/chat-with-document', methods=['POST'])
def chat_with_document():
    """Chat interface with document analysis"""
    # Placeholder implementation
    question = request.json.get('question', '')
    document_id = request.json.get('document_id')
    
    return jsonify({
        'success': True,
        'response': f'Mock response to: {question}',
        'confidence': 0.85
    })


@ai_bp.route('/generate-workpaper/<int:document_id>', methods=['POST'])
def generate_workpaper(document_id):
    """Generate workpaper for specific document"""
    # Placeholder implementation
    return jsonify({
        'success': True,
        'message': 'Workpaper generation started',
        'document_id': document_id
    })