"""
ProjectService: Handles all business logic for projects, including progress calculation.
"""

from models import Project, Task

class ProjectService:
    @staticmethod
    def get_project_progress(project_id, firm_id):
        project = Project.query.get_or_404(project_id)
        if project.firm_id != firm_id:
            return {'error': 'Access denied'}, 403
        total_tasks = Task.query.filter_by(project_id=project_id).count()
        completed_tasks = Task.query.filter_by(project_id=project_id, status='Completed').count()
        progress_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        return {
            'project_id': project.id,
            'project_name': project.name,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'progress_percentage': round(progress_percentage, 1)
        }