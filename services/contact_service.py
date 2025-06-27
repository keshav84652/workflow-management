"""
ContactService: Handles all business logic for contacts, including creation, updates, associations, and activity logging.
"""

from core.db_import import db
from models import Contact
from services.activity_logging_service import ActivityLoggingService as ActivityService

class ContactService:
    def __init__(self):
        self.activity_logger = ActivityService()

    def create_contact(self, form_data, user_id):
        try:
            contact = Contact(
                first_name=form_data.get('first_name'),
                last_name=form_data.get('last_name'),
                email=form_data.get('email'),
                phone=form_data.get('phone'),
                title=form_data.get('title'),
                company=form_data.get('company'),
                address=form_data.get('address')
            )
            db.session.add(contact)
            db.session.commit()
            self.activity_logger.create_activity_log(
                f'Contact "{contact.full_name}" created.',
                user_id
            )
            return {'success': True, 'message': 'Contact created successfully!', 'contact': contact}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}

    def update_contact(self, contact_id, form_data, user_id):
        try:
            contact = Contact.query.get_or_404(contact_id)
            contact.first_name = form_data.get('first_name')
            contact.last_name = form_data.get('last_name')
            contact.email = form_data.get('email')
            contact.phone = form_data.get('phone')
            contact.title = form_data.get('title')
            contact.company = form_data.get('company')
            contact.address = form_data.get('address')
            db.session.commit()
            self.activity_logger.create_activity_log(
                f'Contact "{contact.full_name}" updated.',
                user_id
            )
            return {'success': True, 'message': 'Contact updated successfully!', 'contact': contact}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}