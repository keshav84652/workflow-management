"""
API endpoints blueprint

UPDATED: Modernized with standardized session management and clean imports.
"""

from flask import Blueprint, jsonify, request
from core.db_import import db
from models import Client, Project, Task
from services.base import SessionService

api_bp = Blueprint('api', __name__, url_prefix='/api')


from services.client_service import ClientService

@api_bp.route('/clients/search')
def search_clients():
    firm_id = SessionService.get_current_firm_id()
    query = request.args.get('q', '').strip()
    results = ClientService.search_clients(firm_id, query)
    return jsonify(results)


from services.project_service import ProjectService

@api_bp.route('/project/<int:project_id>/progress', methods=['GET'])
def get_project_progress(project_id):
    firm_id = SessionService.get_current_firm_id()
    result = ProjectService.get_project_progress(project_id, firm_id)
    if isinstance(result, tuple):
        # Error with status code
        return jsonify(result[0]), result[1]
    return jsonify(result)


@api_bp.route('/clients')
def api_clients():
    firm_id = SessionService.get_current_firm_id()
    results = ClientService.get_clients_for_firm(firm_id)
    return jsonify(results)
