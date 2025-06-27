"""
Subtask management blueprint
"""

from flask import Blueprint, request, session, jsonify

from core.db_import import db
from models import Task
from services.activity_logging_service import ActivityLoggingService as ActivityService
from utils.session_helpers import get_session_firm_id, get_session_user_id

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
    """Reorder subtasks within a parent task"""
    parent_task = Task.query.get_or_404(task_id)
    
    # Check access
    if parent_task.project and parent_task.project.firm_id != get_session_firm_id():
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    elif not parent_task.project and parent_task.firm_id != get_session_firm_id():
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        subtask_ids = request.json.get('subtask_ids', [])
        
        # Update order for each subtask
        for index, subtask_id in enumerate(subtask_ids):
            subtask = Task.query.get(subtask_id)
            if subtask and subtask.parent_task_id == task_id:
                subtask.subtask_order = index + 1
        
        # TODO: Move to service layer
        # db.session.commit()
        
        return jsonify({'success': True, 'message': 'Subtasks reordered successfully'})
        
    except Exception as e:
        # TODO: Move to service layer
        # db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@subtasks_bp.route('/<int:task_id>/convert-to-subtask', methods=['POST'])
def convert_to_subtask(task_id):
    """Convert an existing task to a subtask of another task"""
    task = Task.query.get_or_404(task_id)
    
    # Check access
    if task.project and task.project.firm_id != get_session_firm_id():
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    elif not task.project and task.firm_id != get_session_firm_id():
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        parent_task_id = request.json.get('parent_task_id')
        
        if not parent_task_id:
            return jsonify({'success': False, 'message': 'Parent task ID is required'}), 400
        
        parent_task = Task.query.get(parent_task_id)
        if not parent_task:
            return jsonify({'success': False, 'message': 'Parent task not found'}), 404
        
        # Check that parent task belongs to same firm
        if parent_task.project and parent_task.project.firm_id != get_session_firm_id():
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        elif not parent_task.project and parent_task.firm_id != get_session_firm_id():
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        # Prevent circular relationships
        if parent_task_id == task_id:
            return jsonify({'success': False, 'message': 'Cannot make task a subtask of itself'}), 400
        
        # Check if parent task is already a subtask of this task (prevent circular)
        current = parent_task
        while current.parent_task:
            if current.parent_task.id == task_id:
                return jsonify({'success': False, 'message': 'Cannot create circular subtask relationship'}), 400
            current = current.parent_task
        
        # Get next subtask order
        max_order = db.session.query(db.func.max(Task.subtask_order)).filter_by(parent_task_id=parent_task_id).scalar() or 0
        
        # Convert to subtask
        task.parent_task_id = parent_task_id
        task.subtask_order = max_order + 1
        
        # TODO: Move to service layer
        # db.session.commit()
        
        # Activity log
        ActivityService.create_activity_log(
            f'Task "{task.title}" converted to subtask of "{parent_task.title}"',
            session['user_id'],
            parent_task.project_id,
            parent_task.id
        )
        
        return jsonify({'success': True, 'message': 'Task converted to subtask successfully'})
        
    except Exception as e:
        # TODO: Move to service layer
        # db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500