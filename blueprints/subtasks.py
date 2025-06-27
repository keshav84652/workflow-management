"""
Subtask management blueprint
"""

from flask import Blueprint, request, session, jsonify

from core.db_import import db
from models import Task
from services.activity_logging_service import ActivityLoggingService as ActivityService
from utils.consolidated import get_session_firm_id, get_session_user_id

subtasks_bp = Blueprint('subtasks', __name__, url_prefix='/tasks')


from services.task_service import TaskService

@subtasks_bp.route('/<int:task_id>/subtasks/create', methods=['POST'])
def create_subtask(task_id):
    user_id = get_session_user_id()
    title = request.json.get('title', '').strip()
    description = request.json.get('description', '').strip()
    if not title:
        return jsonify({'success': False, 'message': 'Title is required'}), 400
    result = TaskService().create_subtask(task_id, title, description, user_id)
    return jsonify(result)


@subtasks_bp.route('/<int:task_id>/subtasks/reorder', methods=['POST'])
def reorder_subtasks(task_id):
    user_id = get_session_user_id()
    subtask_ids = request.json.get('subtask_ids', [])
    result = TaskService().reorder_subtasks(task_id, subtask_ids, user_id)
    return jsonify(result)


@subtasks_bp.route('/<int:task_id>/convert-to-subtask', methods=['POST'])
def convert_to_subtask(task_id):
    user_id = get_session_user_id()
    parent_task_id = request.json.get('parent_task_id')
    if not parent_task_id:
        return jsonify({'success': False, 'message': 'Parent task ID is required'}), 400
    result = TaskService().convert_to_subtask(task_id, parent_task_id, user_id)
    if isinstance(result, tuple):
        return jsonify(result[0]), result[1]
    return jsonify(result)