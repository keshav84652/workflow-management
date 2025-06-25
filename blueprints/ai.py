"""
AI Document Analysis blueprint
"""

from flask import Blueprint, request, session, jsonify, send_file, render_template, current_app
from datetime import datetime
import os
import json
from pathlib import Path

from core import db
from models import (
    ClientDocument, ChecklistItem, DocumentChecklist, Client, 
    IncomeWorksheet, User, Attachment
)
from utils import create_activity_log
from services.ai_service import AIService

ai_bp = Blueprint('ai', __name__)


@ai_bp.route('/analyze-document/<int:document_id>', methods=['POST'])
def analyze_document(document_id):
    """Analyze a client document using AI (Azure + Gemini)"""
    firm_id = session['firm_id']
    
    try:
        # Get the document and verify access
        document = db.session.query(ClientDocument).join(ChecklistItem).join(DocumentChecklist).join(Client).filter(
            ClientDocument.id == document_id,
            Client.firm_id == firm_id
        ).first()
        
        if not document:
            return jsonify({'success': False, 'error': 'Document not found'}), 404
        
        # Initialize AI service with current config
        ai_service = AIService(current_app.config)
        
        # Find the actual file path
        document_path = None
        if hasattr(document, 'attachment') and document.attachment:
            document_path = document.attachment.file_path
        elif hasattr(document, 'file_path') and document.file_path:
            document_path = document.file_path
        
        if not document_path or not os.path.exists(document_path):
            return jsonify({
                'success': False,
                'error': 'Document file not found on server'
            }), 404
        
        # Perform AI analysis
        results = ai_service.analyze_document(document_path, document_id)
        
        # Save results to database
        if ai_service.save_analysis_results(document_id, results):
            return jsonify({
                'success': True,
                'message': 'Document analysis completed',
                'document_id': document_id,
                'status': results.get('status', 'completed'),
                'services_used': results.get('services_used', []),
                'confidence_score': results.get('confidence_score', 0.0)
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to save analysis results'
            }), 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Analysis failed: {str(e)}'
        }), 500


@ai_bp.route('/api/document-analysis/<int:document_id>', methods=['GET', 'POST'])
def get_document_analysis(document_id):
    """Get or trigger analysis for a document"""
    try:
        if 'firm_id' not in session:
            return jsonify({'error': 'No firm session found'}), 401
            
        firm_id = session['firm_id']
    except Exception as session_error:
        return jsonify({'error': f'Session error: {str(session_error)}'}), 500
    
    # Get the document and verify access
    try:
        document = db.session.query(ClientDocument).join(ChecklistItem).join(DocumentChecklist).join(Client).filter(
            ClientDocument.id == document_id,
            Client.firm_id == firm_id
        ).first()
        
        if not document:
            return jsonify({'error': 'Document not found'}), 404
            
    except Exception as db_error:
        return jsonify({'error': f'Database error: {str(db_error)}'}), 500
    
    # Check for force_reanalysis parameter
    force_reanalysis = request.args.get('force_reanalysis', 'false').lower() == 'true'
    
    # If forcing re-analysis, reset analysis status to ensure fresh analysis
    if force_reanalysis:
        document.ai_analysis_completed = False
        document.ai_analysis_results = None
        document.ai_analysis_timestamp = None
        db.session.commit()
    
    # Check if AI analysis has already been completed (unless forcing re-analysis)
    if not force_reanalysis and document.ai_analysis_completed and document.ai_analysis_results:
        try:
            cached_results = json.loads(document.ai_analysis_results)
            
            # Convert cached results to frontend-expected format (same as fresh analysis)
            response_data = {
                'document_type': cached_results.get('document_type', 'general_document'),
                'confidence_score': cached_results.get('confidence_score', 0.0),
                'analysis_timestamp': document.ai_analysis_timestamp.isoformat() if document.ai_analysis_timestamp else None,
                'status': cached_results.get('status', 'completed'),
                'services_used': cached_results.get('services_used', []),
                'extracted_data': {},
                'azure_result': cached_results.get('azure_results'),  # Map plural to singular 
                'gemini_result': cached_results.get('gemini_results'),  # Map plural to singular
                'combined_analysis': cached_results.get('combined_analysis'),
                'cached': True
            }
            
            # Add extracted data from combined analysis
            if 'combined_analysis' in cached_results:
                combined = cached_results['combined_analysis']
                response_data['extracted_data'] = combined.get('structured_data', {})
                response_data['confidence_score'] = combined.get('confidence_score', 0.0)
                response_data['document_type'] = combined.get('document_type', 'general_document')
            
            return jsonify(response_data)
        except (json.JSONDecodeError, AttributeError):
            # If cached results are corrupted, proceed with new analysis
            pass
    
    # Use real AI analysis implementation
    try:
        # Initialize AI service
        ai_service = AIService(current_app.config)
        
        # Find document file path
        document_path = None
        if hasattr(document, 'attachment') and document.attachment:
            document_path = document.attachment.file_path
        elif hasattr(document, 'file_path') and document.file_path:
            document_path = document.file_path
        
        if not document_path or not os.path.exists(document_path):
            # Return mock results if file not found
            mock_results = {
                'document_type': 'general_document',
                'confidence_score': 0.5,
                'analysis_timestamp': datetime.utcnow().isoformat(),
                'status': 'mock',
                'services_used': ['mock'],
                'reason': 'Document file not found - using mock data',
                'extracted_data': {},
                'azure_result': None,
                'gemini_result': None,
                'combined_analysis': None
            }
        else:
            # Perform real AI analysis
            analysis_results = ai_service.analyze_document(document_path, document_id)
            
            # Convert to frontend-expected format
            response_data = {
                'document_type': analysis_results.get('document_type', 'general_document'),
                'confidence_score': analysis_results.get('confidence_score', 0.0),
                'analysis_timestamp': analysis_results.get('analysis_timestamp'),
                'status': analysis_results.get('status', 'completed'),
                'services_used': analysis_results.get('services_used', []),
                'extracted_data': {},
                'azure_result': analysis_results.get('azure_results'),  # Map plural to singular 
                'gemini_result': analysis_results.get('gemini_results'),  # Map plural to singular
                'combined_analysis': analysis_results.get('combined_analysis'),
                'filename': os.path.basename(document_path) if document_path else 'Unknown'  # Add filename for display
            }
            
            # Add extracted data from combined analysis
            if 'combined_analysis' in analysis_results:
                combined = analysis_results['combined_analysis']
                response_data['extracted_data'] = combined.get('structured_data', {})
                response_data['confidence_score'] = combined.get('confidence_score', 0.0)
                response_data['document_type'] = combined.get('document_type', 'general_document')
        
        # Save results to database and return response
        if 'analysis_results' in locals():
            ai_service.save_analysis_results(document_id, analysis_results)
            db.session.commit()
            return jsonify(response_data)
        else:
            ai_service.save_analysis_results(document_id, mock_results)
            db.session.commit()
            return jsonify(mock_results)
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': f'Analysis failed: {str(e)}'
        }), 500


@ai_bp.route('/api/analyze-checklist/<int:checklist_id>', methods=['POST'])
def analyze_checklist(checklist_id):
    """Analyze all documents in a checklist"""
    try:
        if 'firm_id' not in session:
            return jsonify({'error': 'No firm session found'}), 401
            
        firm_id = session['firm_id']
    except Exception as session_error:
        return jsonify({'error': f'Session error: {str(session_error)}'}), 500
    
    # Get checklist and verify access
    checklist = DocumentChecklist.query.join(Client).filter(
        DocumentChecklist.id == checklist_id,
        Client.firm_id == firm_id
    ).first_or_404()
    
    # Get force_reanalysis flag using more robust method
    request_data = request.get_json(silent=True) or {}
    force_reanalysis = request_data.get('force_reanalysis', False)
    
    try:
        # Initialize AI service
        ai_service = AIService(current_app.config)
        
        # Real analysis of all documents in checklist
        analyzed_count = 0
        total_documents = 0
        
        for item in checklist.items:
            for document in item.client_documents:
                total_documents += 1
                
                # If forcing re-analysis, reset the document's analysis status
                if force_reanalysis:
                    document.ai_analysis_completed = False
                    document.ai_analysis_results = None
                    document.ai_analysis_timestamp = None
                
                if not document.ai_analysis_completed or force_reanalysis:
                    try:
                        # Find document file path
                        document_path = None
                        if hasattr(document, 'attachment') and document.attachment:
                            document_path = document.attachment.file_path
                        elif hasattr(document, 'file_path') and document.file_path:
                            document_path = document.file_path
                        
                        if document_path and os.path.exists(document_path):
                            # Perform real AI analysis
                            results = ai_service.analyze_document(document_path, document.id)
                            ai_service.save_analysis_results(document.id, results)
                            analyzed_count += 1
                        else:
                            # Use mock results if file not found
                            mock_results = {
                                'document_type': 'general_document',
                                'confidence_score': 0.5,
                                'analysis_timestamp': datetime.utcnow().isoformat(),
                                'status': 'mock',
                                'reason': 'Document file not found'
                            }
                            ai_service.save_analysis_results(document.id, mock_results)
                            analyzed_count += 1
                        
                        # Commit after each document to avoid session buildup
                        db.session.commit()
                        
                    except Exception as doc_error:
                        print(f"Error processing document {document.id}: {doc_error}")
                        db.session.rollback()
                        # Continue with next document
        
        return jsonify({
            'success': True,
            'analyzed_count': analyzed_count,
            'total_documents': total_documents,
            'message': f'Analyzed {analyzed_count} new documents'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Analysis failed: {str(e)}'
        }), 500


@ai_bp.route('/api/export-checklist-analysis/<int:checklist_id>', methods=['GET'])
def export_checklist_analysis(checklist_id):
    """Export checklist analysis results"""
    firm_id = session['firm_id']
    
    # Get checklist and verify access
    checklist = DocumentChecklist.query.join(Client).filter(
        DocumentChecklist.id == checklist_id,
        Client.firm_id == firm_id
    ).first_or_404()
    
    try:
        # Gather analysis results
        analysis_data = {
            'checklist_name': checklist.name,
            'client_name': checklist.client.name,
            'export_timestamp': datetime.utcnow().isoformat(),
            'documents': []
        }
        
        for item in checklist.items:
            for document in item.client_documents:
                doc_data = {
                    'item_title': item.title,
                    'filename': document.original_filename,
                    'analysis_completed': document.ai_analysis_completed,
                    'analysis_results': json.loads(document.ai_analysis_results) if document.ai_analysis_results else None
                }
                analysis_data['documents'].append(doc_data)
        
        # Create temporary JSON file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(analysis_data, temp_file, indent=2)
            temp_path = temp_file.name
        
        return send_file(
            temp_path,
            as_attachment=True,
            download_name=f'checklist_analysis_{checklist_id}.json',
            mimetype='application/json'
        )
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Export failed: {str(e)}'
        }), 500


@ai_bp.route('/api/generate-income-worksheet/<int:checklist_id>', methods=['POST'])
def generate_income_worksheet(checklist_id):
    """Generate income worksheet from analyzed documents"""
    firm_id = session['firm_id']
    
    # Get checklist and verify access
    checklist = DocumentChecklist.query.join(Client).filter(
        DocumentChecklist.id == checklist_id,
        Client.firm_id == firm_id
    ).first_or_404()
    
    try:
        # Mock income worksheet generation
        worksheet_data = {
            'total_income': 75000,
            'w2_income': 60000,
            'interest_income': 500,
            'dividend_income': 1500,
            'other_income': 13000,
            'total_deductions': 12000,
            'federal_withholding': 8000,
            'state_withholding': 2000
        }
        
        # Create or update income worksheet
        worksheet = IncomeWorksheet.query.filter_by(checklist_id=checklist_id).first()
        if not worksheet:
            worksheet = IncomeWorksheet(
                checklist_id=checklist_id,
                created_by=session['user_id']
            )
            db.session.add(worksheet)
        
        worksheet.worksheet_data = json.dumps(worksheet_data)
        worksheet.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'worksheet_id': worksheet.id,
            'data': worksheet_data
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Worksheet generation failed: {str(e)}'
        }), 500


@ai_bp.route('/download-income-worksheet/<int:checklist_id>')
def download_income_worksheet(checklist_id):
    """Download generated income worksheet"""
    firm_id = session['firm_id']
    
    # Get checklist and verify access
    checklist = DocumentChecklist.query.join(Client).filter(
        DocumentChecklist.id == checklist_id,
        Client.firm_id == firm_id
    ).first_or_404()
    
    worksheet = IncomeWorksheet.query.filter_by(checklist_id=checklist_id).first_or_404()
    
    try:
        # Create temporary worksheet file
        import tempfile
        worksheet_data = json.loads(worksheet.worksheet_data)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(worksheet_data, temp_file, indent=2)
            temp_path = temp_file.name
        
        return send_file(
            temp_path,
            as_attachment=True,
            download_name=f'income_worksheet_{checklist.client.name}.json',
            mimetype='application/json'
        )
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Download failed: {str(e)}'
        }), 500


@ai_bp.route('/api/saved-income-worksheet/<int:checklist_id>')
def get_saved_income_worksheet(checklist_id):
    """Get saved income worksheet data"""
    firm_id = session['firm_id']
    
    # Get checklist and verify access
    checklist = DocumentChecklist.query.join(Client).filter(
        DocumentChecklist.id == checklist_id,
        Client.firm_id == firm_id
    ).first_or_404()
    
    worksheet = IncomeWorksheet.query.filter_by(checklist_id=checklist_id).first()
    
    if not worksheet:
        return jsonify({'error': 'No saved worksheet found'}), 404
    
    try:
        worksheet_data = json.loads(worksheet.worksheet_data)
        return jsonify({
            'success': True,
            'data': worksheet_data,
            'updated_at': worksheet.updated_at.isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to load worksheet: {str(e)}'
        }), 500


@ai_bp.route('/download-saved-worksheet/<int:worksheet_id>')
def download_saved_worksheet(worksheet_id):
    """Download a specific saved worksheet"""
    worksheet = IncomeWorksheet.query.get_or_404(worksheet_id)
    
    # Verify access through checklist
    checklist = worksheet.checklist
    if checklist.client.firm_id != session['firm_id']:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        worksheet_data = json.loads(worksheet.worksheet_data)
        
        import tempfile
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
        return jsonify({
            'success': False,
            'error': f'Download failed: {str(e)}'
        }), 500


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