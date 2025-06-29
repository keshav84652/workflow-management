"""
ContactService: Handles all business logic for contacts, including creation, updates, associations, and activity logging.
"""

from core.db_import import db
from src.models import Contact, ClientContact, Client
from services.activity_logging_service import ActivityLoggingService as ActivityService
from services.base import BaseService, transactional
from .repository import ClientRepository


class ContactService(BaseService):
    def __init__(self):
        super().__init__()
        self.client_repository = ClientRepository()

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
            ActivityService.log_entity_operation(
                entity_type='CONTACT',
                operation='CREATE',
                entity_id=contact.id,
                entity_name=contact.full_name,
                details='Contact created',
                user_id=user_id
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
            ActivityService.log_entity_operation(
                entity_type='CONTACT',
                operation='UPDATE',
                entity_id=contact.id,
                entity_name=contact.full_name,
                details='Contact information updated',
                user_id=user_id
            )
            return {'success': True, 'message': 'Contact updated successfully!', 'contact': contact}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}

    def associate_contact_with_client(self, contact_id, client_id, firm_id, user_id):
        try:
            client = self.client_repository.get_by_id_and_firm(client_id, firm_id)
            if not client:
                return {'success': False, 'message': 'Client not found or access denied'}
            contact = Contact.query.get_or_404(contact_id)
            existing = ClientContact.query.filter_by(contact_id=contact_id, client_id=client_id).first()
            if existing:
                return {'success': False, 'message': 'Contact already associated with this client'}
            association = ClientContact(contact_id=contact_id, client_id=client_id)
            db.session.add(association)
            db.session.commit()
            ActivityService.log_entity_operation(
                entity_type='CONTACT',
                operation='ASSIGN',
                entity_id=contact.id,
                entity_name=contact.full_name,
                details=f'Associated with client "{client.name}"',
                user_id=user_id
            )
            return {'success': True, 'message': f'Contact {contact.full_name} associated with {client.name}'}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}

    def disassociate_contact_from_client(self, contact_id, client_id, firm_id, user_id):
        try:
            client = self.client_repository.get_by_id_and_firm(client_id, firm_id)
            if not client:
                return {'success': False, 'message': 'Client not found or access denied'}
            contact = Contact.query.get_or_404(contact_id)
            association = ClientContact.query.filter_by(contact_id=contact_id, client_id=client_id).first()
            if association:
                db.session.delete(association)
                db.session.commit()
                ActivityService.log_entity_operation(
                    entity_type='CONTACT',
                    operation='UNASSIGN',
                    entity_id=contact.id,
                    entity_name=contact.full_name,
                    details=f'Disassociated from client "{client.name}"',
                    user_id=user_id
                )
                return {'success': True, 'message': f'Contact {contact.full_name} disassociated from {client.name}'}
            else:
                return {'success': False, 'message': 'No association found'}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}

    def link_contact_to_client(self, contact_id, client_id, relationship_type, is_primary, firm_id, user_id):
        try:
            contact = Contact.query.get_or_404(contact_id)
            client = self.client_repository.get_by_id_and_firm(client_id, firm_id)
            if not client:
                return {'success': False, 'message': 'Client not found or access denied'}
            existing = ClientContact.query.filter_by(client_id=client_id, contact_id=contact_id).first()
            if existing:
                return {'success': False, 'message': 'Contact is already associated with this client'}
            if is_primary:
                ClientContact.query.filter_by(client_id=client_id, is_primary=True).update({'is_primary': False})
            client_contact = ClientContact(
                client_id=client_id,
                contact_id=contact_id,
                relationship_type=relationship_type,
                is_primary=is_primary
            )
            db.session.add(client_contact)
            db.session.commit()
            ActivityService.log_entity_operation(
                entity_type='CONTACT',
                operation='ASSIGN',
                entity_id=contact.id,
                entity_name=contact.full_name,
                details=f'Linked to client "{client.name}" as {relationship_type}',
                user_id=user_id
            )
            return {'success': True, 'message': 'Client linked successfully!'}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}
    
    def list_contacts(self, firm_id):
        """Get all contacts for a firm with client count"""
        contacts_query = db.session.query(Contact).join(ClientContact).join(Client).filter(
            Client.firm_id == firm_id
        ).distinct()
        
        contacts = contacts_query.all()
        
        # Add client count for each contact (only count clients from this firm)
        for contact in contacts:
            contact.client_count = db.session.query(ClientContact).join(Client).filter(
                ClientContact.contact_id == contact.id,
                Client.firm_id == firm_id
            ).count()
        
        return contacts
    
    def view_contact(self, contact_id, firm_id):
        """Get contact details with associated clients for a firm"""
        contact = Contact.query.get_or_404(contact_id)
        
        # Get clients associated with this contact for this firm
        associated_clients = db.session.query(Client).join(ClientContact).filter(
            ClientContact.contact_id == contact_id,
            Client.firm_id == firm_id
        ).all()
        
        return {
            'contact': contact,
            'associated_clients': associated_clients
        }
