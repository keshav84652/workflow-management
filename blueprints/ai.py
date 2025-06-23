"""
AI Document Analysis blueprint
"""

from flask import Blueprint, request, session, jsonify, send_file, render_template
from datetime import datetime
import os
import json
from pathlib import Path

from core import db
from models import (
    ClientDocument, ChecklistItem, DocumentChecklist, Client, 
    IncomeWorksheet, User
)
from utils import create_activity_log

ai_bp = Blueprint('ai', __name__)

# AI services availability is now determined by configuration
from flask import current_app


@ai_bp.route('/analyze-document/<int:document_id>', methods=['POST'])
def analyze_document(document_id):
    """Analyze a client document using AI (Azure + Gemini)"""
    if not current_app.config.AI_SERVICES_AVAILABLE:
        return jsonify({
            'success': False,
            'error': 'AI services not available. Please configure environment and install dependencies.'
        }), 503
    
    firm_id = session['firm_id']
    
    try:
        # Get the document and verify access
        document = db.session.query(ClientDocument).join(ChecklistItem).join(DocumentChecklist).join(Client).filter(
            ClientDocument.id == document_id,
            Client.firm_id == firm_id
        ).first()
        
        if not document:
            return jsonify({'success': False, 'error': 'Document not found'}), 404
        
        # For now, return success to show the UI works
        return jsonify({
            'success': True,
            'message': 'Document analysis started',
            'document_id': document_id,
            'status': 'processing'
        })
        
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
    
    # Check if AI analysis has already been completed (unless forcing re-analysis)
    if not force_reanalysis and document.ai_analysis_completed and document.ai_analysis_results:
        try:
            cached_results = json.loads(document.ai_analysis_results)
            cached_results['cached'] = True
            cached_results['analysis_timestamp'] = document.ai_analysis_timestamp.isoformat() if document.ai_analysis_timestamp else None
            return jsonify(cached_results)
        except (json.JSONDecodeError, AttributeError):
            # If cached results are corrupted, proceed with new analysis
            pass
    
    # Placeholder for AI analysis implementation
    try:
        # This would contain the actual AI analysis logic
        mock_results = {
            'document_type': 'tax_document',
            'confidence_score': 0.95,
            'extracted_data': {
                'total_income': 50000,
                'deductions': 5000,
                'tax_year': 2024
            },
            'analysis_timestamp': datetime.utcnow().isoformat(),
            'status': 'completed'
        }
        
        # Save results to database
        document.ai_analysis_completed = True
        document.ai_analysis_results = json.dumps(mock_results)
        document.ai_analysis_timestamp = datetime.utcnow()
        db.session.commit()
        
        return jsonify(mock_results)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Analysis failed: {str(e)}'
        }), 500


@ai_bp.route('/api/analyze-checklist/<int:checklist_id>', methods=['POST'])
def analyze_checklist(checklist_id):
    """Analyze all documents in a checklist"""
    firm_id = session['firm_id']
    
    # Get checklist and verify access
    checklist = DocumentChecklist.query.join(Client).filter(
        DocumentChecklist.id == checklist_id,
        Client.firm_id == firm_id
    ).first_or_404()
    
    try:
        # Mock analysis of all documents in checklist
        analyzed_count = 0
        total_documents = 0
        
        for item in checklist.items:
            for document in item.client_documents:
                total_documents += 1
                if not document.ai_analysis_completed:
                    # Mock analysis
                    mock_results = {
                        'document_type': 'general_document',
                        'confidence_score': 0.85,
                        'analysis_timestamp': datetime.utcnow().isoformat(),
                        'status': 'completed'
                    }
                    
                    document.ai_analysis_completed = True
                    document.ai_analysis_results = json.dumps(mock_results)
                    document.ai_analysis_timestamp = datetime.utcnow()
                    analyzed_count += 1
        
        db.session.commit()
        
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