from typing import List, Optional
from models.documents import Attachment
from core.db_import import db

class AttachmentRepository:
    def get_by_firm(self, firm_id: int) -> List[Attachment]:
        return Attachment.query.filter_by(firm_id=firm_id).all()

    def get_by_task(self, task_id: int) -> List[Attachment]:
        return Attachment.query.filter_by(task_id=task_id).all()

    def get_by_project(self, project_id: int) -> List[Attachment]:
        return Attachment.query.filter_by(project_id=project_id).all()

    def create(self, **kwargs) -> Attachment:
        attachment = Attachment(**kwargs)
        db.session.add(attachment)
        db.session.commit()
        return attachment

    def delete(self, attachment_id: int) -> bool:
        attachment = Attachment.query.get(attachment_id)
        if not attachment:
            return False
        db.session.delete(attachment)
        db.session.commit()
        return True