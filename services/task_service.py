"""
TaskService: Handles all business logic for tasks and subtasks.
"""

from core.db_import import db
from models import Task
from services.activity_logging_service import ActivityLoggingService as ActivityService

class TaskService:
    def __init__(self):
        self.activity_logger = ActivityService()

    def create_subtask(self, parent_task_id, title, description, user_id):
        try:
            parent_task = Task.query.get_or_404(parent_task_id)
            max_order = db.session.query(db.func.max(Task.subtask_order)).filter_by(parent_task_id=parent_task_id).scalar() or 0
            subtask = Task(
                title=title,
                description=description,
                parent_task_id=parent_task_id,
                subtask_order=max_order + 1,
                project_id=parent_task.project_id,
                firm_id=parent_task.firm_id,
                assignee_id=parent_task.assignee_id,
                priority=parent_task.priority,
                status_id=parent_task.status_id,
                status=parent_task.status if not parent_task.status_id else 'Not Started'
            )
            db.session.add(subtask)
            db.session.commit()
            self.activity_logger.create_activity_log(
                f'Subtask "{title}" created for task "{parent_task.title}"',
                user_id,
                parent_task.project_id,
                parent_task.id
            )
            return {
                'success': True,
                'subtask': {
                    'id': subtask.id,
                    'title': subtask.title,
                    'description': subtask.description,
                    'status': subtask.current_status,
                    'assignee_name': subtask.assignee.name if subtask.assignee else 'Unassigned',
                    'created_at': subtask.created_at.strftime('%m/%d/%Y %I:%M %p')
                }
            }
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}

    def reorder_subtasks(self, task_id, subtask_ids, user_id):
        try:
            for index, subtask_id in enumerate(subtask_ids):
                subtask = Task.query.get(subtask_id)
                if subtask and subtask.parent_task_id == task_id:
                    subtask.subtask_order = index + 1
            db.session.commit()
            return {'success': True, 'message': 'Subtasks reordered successfully'}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}

    def convert_to_subtask(self, task_id, parent_task_id, user_id):
        try:
            task = Task.query.get_or_404(task_id)
            parent_task = Task.query.get(parent_task_id)
            if not parent_task:
                return {'success': False, 'message': 'Parent task not found'}, 404
            # Prevent circular relationships
            if parent_task_id == task_id:
                return {'success': False, 'message': 'Cannot make task a subtask of itself'}, 400
            current = parent_task
            while current.parent_task:
                if current.parent_task.id == task_id:
                    return {'success': False, 'message': 'Cannot create circular subtask relationship'}, 400
                current = current.parent_task
            max_order = db.session.query(db.func.max(Task.subtask_order)).filter_by(parent_task_id=parent_task_id).scalar() or 0
            task.parent_task_id = parent_task_id
            task.subtask_order = max_order + 1
            db.session.commit()
            self.activity_logger.create_activity_log(
                f'Task \"{task.title}\" converted to subtask of \"{parent_task.title}\"',
                user_id,
                parent_task.project_id,
                parent_task.id
            )
            return {'success': True, 'message': 'Task converted to subtask successfully'}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}