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
    
    # Map Azure results - check both direct fields and raw_results
    azure_data = provider_results.get('Azure Document Intelligence', {})
    if azure_data and 'error' not in azure_data:
        # Check if data is in raw_results (new structure)
        raw_results = azure_data.get('raw_results', {})
        if raw_results and 'fields' in raw_results:
            azure_fields = raw_results['fields']
            azure_entities = raw_results.get('entities', [])
            azure_confidence = raw_results.get('confidence', azure_data.get('confidence_score', 0))
        else:
            # Fallback to direct fields (old structure)
            azure_fields = azure_data.get('fields', {})
            azure_entities = azure_data.get('entities', [])
            azure_confidence = azure_data.get('confidence_score', 0)
        
        # Get extracted text as fallback if no structured fields
        extracted_text = raw_results.get('text', azure_data.get('extracted_text', ''))
        
        # Create key-value pairs from fields, or fallback content
        kv_pairs = _extract_fields_as_kv_pairs(azure_fields)
        if not kv_pairs and extracted_text:
            # If no structured fields, show document type and text length as basic info
            kv_pairs = [
                {'key': 'Document Type', 'value': raw_results.get('document_type', 'Unknown'), 'confidence': 1.0},
                {'key': 'Text Extracted', 'value': f'{len(extracted_text)} characters', 'confidence': 1.0},
                {'key': 'Text Preview', 'value': extracted_text[:200] + ('...' if len(extracted_text) > 200 else ''), 'confidence': 1.0}
            ]
        
        transformed['azure_result'] = {
            'key_value_pairs': kv_pairs,
            'tables': azure_entities,
            'confidence': azure_confidence,
            'provider': 'Azure Document Intelligence',
            'extracted_text': extracted_text
        }
    
    # Map Gemini results - only if no error
    gemini_data = provider_results.get('Google Gemini', {})
    if gemini_data and 'error' not in gemini_data:
        # Check if data is in raw_results
        raw_results = gemini_data.get('raw_results', {})
        if raw_results:
            transformed['gemini_result'] = {
                'document_type': raw_results.get('document_type', ''),
                'summary': raw_results.get('summary', ''),
                'key_findings': raw_results.get('key_findings', []),
                'recommendations': raw_results.get('recommendations', []),
                'confidence': raw_results.get('confidence', gemini_data.get('confidence_score', 0)),
                'provider': 'Google Gemini'
            }
        else:
            # Fallback to direct fields
            transformed['gemini_result'] = {
                'document_type': gemini_data.get('document_type', ''),
                'summary': gemini_data.get('summary', ''),
                'key_findings': gemini_data.get('key_findings', []),
                'recommendations': gemini_data.get('recommendations', []),
                'confidence': gemini_data.get('confidence_score', 0),
                'provider': 'Google Gemini'
            }
    
    # Fall back to combined analysis if provider-specific data is missing
    if not transformed['azure_result'] and not transformed['gemini_result']:
        if combined_analysis:
            # Check if combined analysis has raw_results
            combined_raw = combined_analysis.get('raw_results', combined_analysis)
            transformed['azure_result'] = {
                'key_value_pairs': _extract_fields_as_kv_pairs(combined_raw.get('fields', {})),
                'tables': combined_raw.get('entities', []),
                'confidence': combined_raw.get('confidence_score', combined_analysis.get('confidence_score', 0)),
                'provider': 'Combined Analysis'
            }
            transformed['gemini_result'] = {
                'document_type': combined_raw.get('document_type', ''),
                'summary': 'Combined analysis result',
                'key_findings': [],
                'recommendations': [],
                'confidence': combined_raw.get('confidence_score', combined_analysis.get('confidence_score', 0)),
                'provider': 'Combined Analysis'
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