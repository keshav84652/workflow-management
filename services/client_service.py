"""
Client service layer for business logic
"""

from typing import Optional, List, Dict, Any
from flask import session
from core import db
from models import Client, Project, Contact, ActivityLog
from utils import create_activity_log


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
            firm_id = session['firm_id']
        
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
            create_activity_log(
                user_id=session.get('user_id'),
                firm_id=firm_id,
                action='create',
                details=f'Created client "{client.name}"'
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
            firm_id = session['firm_id']
        
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
            create_activity_log(
                user_id=session.get('user_id'),
                firm_id=firm_id,
                action='update',
                details=f'Updated client "{client.name}"'
            )
            
            return {'success': True, 'message': 'Client updated successfully'}
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': f'Error updating client: {str(e)}'}
    
    @staticmethod
    def delete_client(client_id: int, firm_id: Optional[int] = None) -> Dict[str, Any]:
        """Delete a client and all associated data"""
        if firm_id is None:
            firm_id = session['firm_id']
        
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
            create_activity_log(
                user_id=session.get('user_id'),
                firm_id=firm_id,
                action='delete',
                details=f'Deleted client "{client_name}" and {project_count} associated projects'
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
            firm_id = session['firm_id']
        
        clients = ClientService.get_clients_for_firm(firm_id)
        
        stats = {
            'total': len(clients),
            'active': len([c for c in clients if c.is_active]),
            'inactive': len([c for c in clients if not c.is_active]),
        }
        
        return stats