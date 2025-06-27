"""
DocumentService: Handles all business logic for documents and checklists, including sharing.
"""

from core.db_import import db
from models import DocumentChecklist, Client
import secrets

class DocumentService:
    @staticmethod
    def generate_share_token(checklist_id, firm_id):
        checklist = DocumentChecklist.query.join(Client).filter(
            DocumentChecklist.id == checklist_id,
            Client.firm_id == firm_id
        ).first_or_404()
        if not checklist.public_access_token:
            checklist.public_access_token = secrets.token_urlsafe(32)
            checklist.public_access_enabled = True
            db.session.commit()
        return checklist

    @staticmethod
    def revoke_share(checklist_id, firm_id):
        checklist = DocumentChecklist.query.join(Client).filter(
            DocumentChecklist.id == checklist_id,
            Client.firm_id == firm_id
        ).first_or_404()
        checklist.public_access_enabled = False
        db.session.commit()
        return checklist

    @staticmethod
    def regenerate_share_token(checklist_id, firm_id):
        checklist = DocumentChecklist.query.join(Client).filter(
            DocumentChecklist.id == checklist_id,
            Client.firm_id == firm_id
        ).first_or_404()
        checklist.public_access_token = secrets.token_urlsafe(32)
        checklist.public_access_enabled = True
        db.session.commit()
        return checklist