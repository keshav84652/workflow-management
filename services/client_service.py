"""
Client service layer for business logic
"""

from typing import Optional, List, Dict, Any
from flask import session

from core.db_import import db
from models import Client, Project, Contact, ActivityLog, ClientContact, ClientUser
from services.activity_service import ActivityService
from utils import get_session_firm_id, get_session_user_id


class ClientService:
    """Service class for client-related business operations"""
    
    @staticmethod
    def get_clients_for_firm(firm_id: int, active_only: bool = False) -> List[Client]:
        """Get all clients for a firm"""
        query = Client.query.filter_by(firm_id=firm_id)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.all()
    
    @staticmethod
    def get_client_by_id(client_id: int, firm_id: int) -> Optional[Client]:
        """Get a client by ID, ensuring it belongs to the firm"""
        return Client.query.filter_by(id=client_id, firm_id=firm_id).first()
    
    @staticmethod
    def create_client(
        name: str,
        entity_type: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        address: Optional[str] = None,
        contact_person: Optional[str] = None,
        tax_id: Optional[str] = None,
        notes: Optional[str] = None,
        firm_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a new client"""
        if firm_id is None:
            firm_id = get_session_firm_id()
        
        try:
            client = Client(
                name=name,
                entity_type=entity_type,
                email=email,
                phone=phone,
                address=address,
                contact_person=contact_person,
                tax_id=tax_id,
                notes=notes,
                firm_id=firm_id
            )
            db.session.add(client)
            db.session.commit()
            
            # Create activity log
            ActivityService.create_activity_log(
                action=f'Created client "{client.name}"',
                user_id=session.get('user_id')
            )
            
            return {
                'success': True,
                'client_id': client.id,
                'message': f'Client "{client.name}" created successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': f'Error creating client: {str(e)}'}
    
    @staticmethod
    def update_client(
        client_id: int,
        name: str,
        entity_type: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        address: Optional[str] = None,
        contact_person: Optional[str] = None,
        tax_id: Optional[str] = None,
        notes: Optional[str] = None,
        firm_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Update an existing client"""
        if firm_id is None:
            firm_id = get_session_firm_id()
        
        try:
            client = ClientService.get_client_by_id(client_id, firm_id)
            if not client:
                return {'success': False, 'message': 'Client not found'}
            
            client.name = name
            client.entity_type = entity_type
            client.email = email
            client.phone = phone
            client.address = address
            client.contact_person = contact_person
            client.tax_id = tax_id
            client.notes = notes
            
            db.session.commit()
            
            # Create activity log
            ActivityService.create_activity_log(
                action=f'Updated client "{client.name}"',
                user_id=session.get('user_id')
            )
            
            return {'success': True, 'message': 'Client updated successfully'}
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': f'Error updating client: {str(e)}'}
    
    @staticmethod
    def delete_client(client_id: int, firm_id: Optional[int] = None) -> Dict[str, Any]:
        """Delete a client and all associated data"""
        if firm_id is None:
            firm_id = get_session_firm_id()
        
        try:
            client = ClientService.get_client_by_id(client_id, firm_id)
            if not client:
                return {'success': False, 'message': 'Client not found'}
            
            client_name = client.name
            
            # Count associated projects for logging
            project_count = len(client.projects)
            
            # Delete the client (cascade should handle projects and tasks)
            db.session.delete(client)
            db.session.commit()
            
            # Create activity log
            ActivityService.create_activity_log(
                action=f'Deleted client "{client_name}" and {project_count} associated projects',
                user_id=session.get('user_id')
            )
            
            return {
                'success': True,
                'message': f'Client "{client_name}" and all associated data deleted successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': f'Error deleting client: {str(e)}'}
    
    @staticmethod
    def get_client_statistics(firm_id: Optional[int] = None) -> Dict[str, Any]:
        """Get client statistics for dashboard"""
        if firm_id is None:
            firm_id = get_session_firm_id()
        
        clients = ClientService.get_clients_for_firm(firm_id)
        
        stats = {
            'total': len(clients),
            'active': len([c for c in clients if c.is_active]),
            'inactive': len([c for c in clients if not c.is_active]),
        }
        
        return stats
    
    @staticmethod
    def find_or_create_client(client_name: str, firm_id: int) -> Client:
        """Find existing client or create a new one with minimal info"""
        # Check if client already exists
        client = Client.query.filter_by(name=client_name.strip(), firm_id=firm_id).first()
        
        if not client:
            # Create new client with basic info
            client = Client(
                name=client_name.strip(),
                firm_id=firm_id,
                entity_type='Individual'  # Default
            )
            db.session.add(client)
            db.session.flush()  # Get the ID
        
        return client
    
    @staticmethod
    def toggle_client_status(client_id: int, firm_id: Optional[int] = None) -> Dict[str, Any]:
        """Toggle client active status and update associated projects"""
        if firm_id is None:
            firm_id = get_session_firm_id()
        
        try:
            client = ClientService.get_client_by_id(client_id, firm_id)
            if not client:
                return {'success': False, 'message': 'Client not found or access denied'}
            
            client_name = client.name
            previous_status = "Active" if client.is_active else "Inactive"
            
            # Toggle active status
            client.is_active = not client.is_active
            new_status = "Active" if client.is_active else "Inactive"
            
            # Update all associated projects to match client status
            projects = Project.query.filter_by(client_id=client_id).all()
            for project in projects:
                if client.is_active:
                    # If activating client, set projects to Active if they were inactive
                    if project.status in ['Inactive', 'On Hold']:
                        project.status = 'Active'
                else:
                    # If deactivating client, set active projects to On Hold
                    if project.status == 'Active':
                        project.status = 'On Hold'
            
            db.session.commit()
            
            # Create activity log
            action = f'Client "{client_name}" marked as {new_status} (was {previous_status})'
            if not client.is_active:
                action += f' - {len(projects)} projects set to On Hold'
            else:
                action += f' - {len(projects)} projects reactivated'
            
            ActivityService.create_activity_log(action, get_session_user_id())
            
            return {
                'success': True,
                'message': f'Client "{client_name}" marked as {new_status}',
                'new_status': new_status,
                'is_active': client.is_active
            }
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': f'Error updating client status: {str(e)}'}
    
    @staticmethod
    def associate_contact(
        client_id: int, 
        contact_id: int, 
        relationship_type: str, 
        is_primary: bool = False,
        firm_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Associate a contact with a client"""
        if firm_id is None:
            firm_id = get_session_firm_id()
        
        try:
            client = ClientService.get_client_by_id(client_id, firm_id)
            if not client:
                return {'success': False, 'message': 'Client not found or access denied'}
            
            # Check if association already exists
            existing = ClientContact.query.filter_by(client_id=client_id, contact_id=contact_id).first()
            if existing:
                return {'success': False, 'message': 'Contact is already associated with this client'}
            
            # If setting as primary, remove primary status from other contacts
            if is_primary:
                ClientContact.query.filter_by(client_id=client_id, is_primary=True).update({'is_primary': False})
            
            # Create new association
            client_contact = ClientContact(
                client_id=client_id,
                contact_id=contact_id,
                relationship_type=relationship_type,
                is_primary=is_primary
            )
            
            db.session.add(client_contact)
            db.session.commit()
            
            contact = Contact.query.get(contact_id)
            ActivityService.create_activity_log(
                f'Contact "{contact.full_name}" linked to client "{client.name}" as {relationship_type}',
                get_session_user_id()
            )
            
            return {'success': True, 'message': 'Contact linked successfully!'}
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': f'Error linking contact: {str(e)}'}
    
    @staticmethod
    def get_client_with_projects_and_contacts(client_id: int, firm_id: Optional[int] = None) -> Dict[str, Any]:
        """Get client with associated projects and available contacts for association"""
        if firm_id is None:
            firm_id = get_session_firm_id()
        
        client = ClientService.get_client_by_id(client_id, firm_id)
        if not client:
            return {'success': False, 'message': 'Client not found or access denied', 'client': None}
        
        # Get projects for this client
        projects = Project.query.filter_by(client_id=client_id).order_by(Project.created_at.desc()).all()
        
        # Get available contacts (not already associated with this client)
        associated_contact_ids = db.session.query(ClientContact.contact_id).filter_by(client_id=client_id).subquery()
        available_contacts = Contact.query.filter(~Contact.id.in_(associated_contact_ids)).all()
        
        return {
            'success': True,
            'client': client,
            'projects': projects,
            'available_contacts': available_contacts
        }
    
    @staticmethod
    def create_client_portal_user(client_id: int, email: Optional[str] = None, firm_id: Optional[int] = None) -> Dict[str, Any]:
        """Create client portal access for a client"""
        if firm_id is None:
            firm_id = get_session_firm_id()
        
        try:
            client = ClientService.get_client_by_id(client_id, firm_id)
            if not client:
                return {'success': False, 'message': 'Client not found or access denied'}
            
            # Check if client user already exists
            existing_client_user = ClientUser.query.filter_by(client_id=client_id).first()
            if existing_client_user:
                return {'success': False, 'message': 'Client portal access already exists'}
            
            # Use provided email or fallback to client email
            portal_email = email or client.email
            if not portal_email:
                return {
                    'success': False, 
                    'message': 'Client must have an email address to create portal access. Please update client information first.'
                }
            
            client_user = ClientUser(
                client_id=client_id,
                email=portal_email,
                is_active=True
            )
            # Generate 8-character access code
            client_user.generate_access_code()
            
            db.session.add(client_user)
            db.session.commit()
            
            return {
                'success': True,
                'message': f'Client portal access created successfully! Access code: {client_user.access_code}',
                'access_code': client_user.access_code
            }
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': f'Error creating client portal access: {str(e)}'}
    
    @staticmethod
    def regenerate_client_access_code(client_id: int, firm_id: Optional[int] = None) -> Dict[str, Any]:
        """Regenerate access code for client portal user"""
        if firm_id is None:
            firm_id = get_session_firm_id()
        
        try:
            client = ClientService.get_client_by_id(client_id, firm_id)
            if not client:
                return {'success': False, 'message': 'Client not found or access denied'}
            
            client_user = ClientUser.query.filter_by(client_id=client_id).first()
            if not client_user:
                return {'success': False, 'message': 'Client portal access does not exist'}
            
            old_code = client_user.access_code
            client_user.generate_access_code()
            db.session.commit()
            
            return {
                'success': True,
                'message': f'New access code generated: {client_user.access_code}',
                'access_code': client_user.access_code
            }
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': f'Error regenerating access code: {str(e)}'}
    
    @staticmethod
    def toggle_client_portal_status(client_id: int, firm_id: Optional[int] = None) -> Dict[str, Any]:
        """Toggle client portal user active status"""
        if firm_id is None:
            firm_id = get_session_firm_id()
        
        try:
            client = ClientService.get_client_by_id(client_id, firm_id)
            if not client:
                return {'success': False, 'message': 'Client not found or access denied'}
            
            client_user = ClientUser.query.filter_by(client_id=client_id).first()
            if not client_user:
                return {'success': False, 'message': 'Client portal access does not exist'}
            
            client_user.is_active = not client_user.is_active
            db.session.commit()
            
            status = 'activated' if client_user.is_active else 'deactivated'
            return {
                'success': True,
                'message': f'Client portal access {status}',
                'is_active': client_user.is_active
            }
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': f'Error toggling portal status: {str(e)}'}
    
    @staticmethod
    def get_client_portal_info(client_id: int, firm_id: Optional[int] = None) -> Dict[str, Any]:
        """Get client portal information"""
        if firm_id is None:
            firm_id = get_session_firm_id()
        
        client = ClientService.get_client_by_id(client_id, firm_id)
        if not client:
            return {'success': False, 'message': 'Client not found or access denied', 'client': None, 'client_user': None}
        
        client_user = ClientUser.query.filter_by(client_id=client_id).first()
        
        return {
            'success': True,
            'client': client,
            'client_user': client_user
        }