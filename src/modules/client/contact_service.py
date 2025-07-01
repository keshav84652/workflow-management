"""
ContactService: Handles all business logic for contacts, including creation, updates, associations, and activity logging.
"""

from src.shared.database.db_import import db
from .models import Contact, ClientContact, Client
from src.shared.services import ActivityLoggingService as ActivityService
from src.shared.base import BaseService, transactional
from .repository import ClientRepository
from .contact_repository import ContactRepository


class ContactService(BaseService):
    def __init__(self):
        super().__init__()
        self.client_repository = ClientRepository()
        self.contact_repository = ContactRepository()

    @transactional
    def create_contact(self, form_data, user_id):
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
            ActivityService.log_entity_operation(
                entity_type='CONTACT',
                operation='CREATE',
                entity_id=contact.id,
                entity_name=contact.full_name,
                details='Contact created',
                user_id=user_id
            )
            return {'success': True, 'message': 'Contact created successfully!', 'contact': contact}

    @transactional
    def update_contact(self, contact_id, form_data, user_id):
            contact = self.contact_repository.get_by_id(contact_id)
            if not contact:
                return {'success': False, 'message': 'Contact not found'}
            contact.first_name = form_data.get('first_name')
            contact.last_name = form_data.get('last_name')
            contact.email = form_data.get('email')
            contact.phone = form_data.get('phone')
            contact.title = form_data.get('title')
            contact.company = form_data.get('company')
            contact.address = form_data.get('address')
            ActivityService.log_entity_operation(
                entity_type='CONTACT',
                operation='UPDATE',
                entity_id=contact.id,
                entity_name=contact.full_name,
                details='Contact information updated',
                user_id=user_id
            )
            return {'success': True, 'message': 'Contact updated successfully!', 'contact': contact}

    @transactional
    def associate_contact_with_client(self, contact_id, client_id, firm_id, user_id):
            client = self.client_repository.get_by_id_and_firm(client_id, firm_id)
            if not client:
                return {'success': False, 'message': 'Client not found or access denied'}
            contact = self.contact_repository.get_by_id(contact_id)
            if not contact:
                return {'success': False, 'message': 'Contact not found'}
            existing = self.contact_repository.get_association_by_contact_and_client(contact_id, client_id)
            if existing:
                return {'success': False, 'message': 'Contact already associated with this client'}
            association = ClientContact(contact_id=contact_id, client_id=client_id)
            db.session.add(association)
            ActivityService.log_entity_operation(
                entity_type='CONTACT',
                operation='ASSIGN',
                entity_id=contact.id,
                entity_name=contact.full_name,
                details=f'Associated with client "{client.name}"',
                user_id=user_id
            )
            return {'success': True, 'message': f'Contact {contact.full_name} associated with {client.name}'}

    @transactional
    def disassociate_contact_from_client(self, contact_id, client_id, firm_id, user_id):
            client = self.client_repository.get_by_id_and_firm(client_id, firm_id)
            if not client:
                return {'success': False, 'message': 'Client not found or access denied'}
            contact = self.contact_repository.get_by_id(contact_id)
            if not contact:
                return {'success': False, 'message': 'Contact not found'}
            association = self.contact_repository.get_association_by_contact_and_client(contact_id, client_id)
            if association:
                db.session.delete(association)
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

    @transactional
    def link_contact_to_client(self, contact_id, client_id, relationship_type, is_primary, firm_id, user_id):
            contact = self.contact_repository.get_by_id(contact_id)
            if not contact:
                return {'success': False, 'message': 'Contact not found'}
            client = self.client_repository.get_by_id_and_firm(client_id, firm_id)
            if not client:
                return {'success': False, 'message': 'Client not found or access denied'}
            existing = self.contact_repository.get_association_by_contact_and_client(contact_id, client_id)
            if existing:
                return {'success': False, 'message': 'Contact is already associated with this client'}
            if is_primary:
                self.contact_repository.update_primary_contacts_for_client(client_id)
            client_contact = ClientContact(
                client_id=client_id,
                contact_id=contact_id,
                relationship_type=relationship_type,
                is_primary=is_primary
            )
            db.session.add(client_contact)
            ActivityService.log_entity_operation(
                entity_type='CONTACT',
                operation='ASSIGN',
                entity_id=contact.id,
                entity_name=contact.full_name,
                details=f'Linked to client "{client.name}" as {relationship_type}',
                user_id=user_id
            )
            return {'success': True, 'message': 'Client linked successfully!'}
    
    def list_contacts(self, firm_id):
        """Get all contacts for a firm with client count"""
        return self.contact_repository.get_contacts_for_firm(firm_id)
    
    def view_contact(self, contact_id, firm_id):
        """Get contact details with associated clients for a firm"""
        contact = self.contact_repository.get_by_id(contact_id)
        if not contact:
            return {'success': False, 'message': 'Contact not found'}
        
        # Get clients associated with this contact for this firm
        associated_clients = self.contact_repository.get_clients_for_contact_and_firm(contact_id, firm_id)
        
        return {
            'contact': contact,
            'associated_clients': associated_clients
        }
