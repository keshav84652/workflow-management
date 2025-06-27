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