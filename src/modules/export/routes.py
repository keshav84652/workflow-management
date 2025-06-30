"""
Export routes for data export functionality
"""

from flask import Blueprint, jsonify

from src.shared.utils.consolidated import get_session_firm_id
from .interface import IExportService
from src.shared.di_container import get_service
from .service import ExportService  # Fallback import

export_bp = Blueprint('export', __name__, url_prefix='/export')


@export_bp.route('/projects/<format>')
def export_projects(format):
    """Export projects in specified format"""
    try:
        firm_id = get_session_firm_id()
        
        # Get service from DI container or fallback to direct instantiation
        try:
            export_service = get_service(IExportService)
        except (ValueError, ImportError):
            export_service = ExportService()
        
        if format.lower() == 'csv':
            result = export_service.export_projects_csv(firm_id)
        elif format.lower() == 'json':
            result = export_service.export_projects_json(firm_id)
        else:
            return jsonify({'error': 'Unsupported format'}), 400
        
        # Check if result is an error dict
        if isinstance(result, dict) and not result.get('success', True):
            return jsonify({'error': result.get('error', 'Export failed')}), 500
        
        return result
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@export_bp.route('/clients/<format>')
def export_clients(format):
    """Export clients in specified format"""
    try:
        firm_id = get_session_firm_id()
        
        # Get service from DI container or fallback to direct instantiation
        try:
            export_service = get_service(IExportService)
        except (ValueError, ImportError):
            export_service = ExportService()
        
        if format.lower() == 'csv':
            result = export_service.export_clients_csv(firm_id)
        elif format.lower() == 'json':
            result = export_service.export_clients_json(firm_id)
        else:
            return jsonify({'error': 'Unsupported format'}), 400
        
        # Check if result is an error dict
        if isinstance(result, dict) and not result.get('success', True):
            return jsonify({'error': result.get('error', 'Export failed')}), 500
        
        return result
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@export_bp.route('/tasks/<format>')
def export_tasks(format):
    """Export tasks in specified format"""
    try:
        firm_id = get_session_firm_id()
        
        # Get service from DI container or fallback to direct instantiation
        try:
            export_service = get_service(IExportService)
        except (ValueError, ImportError):
            export_service = ExportService()
        
        if format.lower() == 'csv':
            result = export_service.export_tasks_csv(firm_id)
        elif format.lower() == 'json':
            result = export_service.export_tasks_json(firm_id)
        else:
            return jsonify({'error': 'Unsupported format'}), 400
        
        # Check if result is an error dict
        if isinstance(result, dict) and not result.get('success', True):
            return jsonify({'error': result.get('error', 'Export failed')}), 500
        
        return result
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

