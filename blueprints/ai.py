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


@ai_bp.route('/api/ai-services/status', methods=['GET'])
def ai_services_status():
    """Check the status of AI services"""
    try:
        ai_service = AIService(current_app.config)
        
        status = {
            'ai_services_available': ai_service.is_available(),
            'azure_available': ai_service.azure_client is not None,
            'gemini_available': ai_service.gemini_client is not None,
            'services_configured': []
        }
        
        if ai_service.azure_client:
            status['services_configured'].append('Azure Document Intelligence')
        if ai_service.gemini_client:
            status['services_configured'].append('Google Gemini')
            
        if not status['ai_services_available']:
            status['message'] = 'No AI services configured. Please add GEMINI_API_KEY or Azure Document Intelligence credentials.'
        else:
            status['message'] = f"AI services ready: {', '.join(status['services_configured'])}"
            
        return jsonify(status)
        
    except Exception as e:
        return jsonify({
            'ai_services_available': False,
            'error': f'Failed to check AI service status: {str(e)}'
        }), 500


@ai_bp.route('/analyze-document/<int:document_id>', methods=['POST'])
def analyze_document(document_id):
    """Analyze a client document using AI (Azure + Gemini)"""
    firm_id = session['firm_id']
    
    try:
        # Initialize AI service
        ai_service = AIService(current_app.config)
        
        # Perform analysis
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
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404
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
    
    # Check for force_reanalysis parameter
    force_reanalysis = request.args.get('force_reanalysis', 'false').lower() == 'true'
    
    try:
        # Initialize AI service
        ai_service = AIService(current_app.config)
        
        # Get or perform analysis
        response_data = ai_service.get_or_analyze_document(document_id, firm_id, force_reanalysis)
        
        return jsonify(response_data)
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500


@ai_bp.route('/api/analyze-checklist/<int:checklist_id>', methods=['POST'])
def analyze_checklist(checklist_id):
    """Analyze all documents in a checklist"""
    try:
        if 'firm_id' not in session:
            return jsonify({'error': 'No firm session found'}), 401
            
        firm_id = session['firm_id']
    except Exception as session_error:
        return jsonify({'error': f'Session error: {str(session_error)}'}), 500
    
    # Get force_reanalysis flag
    request_data = request.get_json(silent=True) or {}
    force_reanalysis = request_data.get('force_reanalysis', False)
    
    try:
        # Initialize AI service
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
    user_id = session['user_id']
    
    try:
        # Initialize AI service
        ai_service = AIService(current_app.config)
        
        # Generate income worksheet
        results = ai_service.generate_income_worksheet(checklist_id, firm_id, user_id)
        
        return jsonify(results)
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': f'Worksheet generation failed: {str(e)}'}), 500


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
    
    try:
        # Initialize AI service
        ai_service = AIService(current_app.config)
        
        # Get saved worksheet
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