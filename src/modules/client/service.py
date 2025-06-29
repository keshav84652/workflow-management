"""
ClientService: Handles all business logic for clients, including search and retrieval.
"""

from core.db_import import db
from models import Client
from services.activity_logging_service import ActivityLoggingService as ActivityService
from services.base import BaseService, transactional
from .repository import ClientRepository


class ClientService(BaseService):
    def __init__(self):
        super().__init__()
        self.client_repository = ClientRepository()
    
    def search_clients(self, firm_id, query, limit=20):
        """
        Search clients by name, email, and contact person for a specific firm
        This replaces direct database access in blueprints
        """
        if not query:
            return []
        
        # Use repository search method
        return self.client_repository.search_by_name(firm_id, query, limit)

    def get_clients_by_firm(self, firm_id):
        """Get all clients for a specific firm (raw objects)"""
        return self.client_repository.get_by_firm(firm_id)
    
    def get_active_clients_by_firm(self, firm_id):
        """Get all active clients for a specific firm"""
        return self.client_repository.get_by_firm(firm_id, include_inactive=False)
    
    def get_client_by_id_and_firm(self, client_id, firm_id):
        """Get client by ID with firm access check"""
        return self.client_repository.get_by_id_and_firm(client_id, firm_id)
        
    def get_clients_for_firm(self, firm_id):
        """Get all clients for a firm (formatted for API)"""
        clients = self.client_repository.get_by_firm(firm_id)
        return [{
            'id': client.id,
            'name': client.name,
            'entity_type': client.entity_type,
            'email': client.email,
            'phone': client.phone,
            'is_active': client.is_active
        } for client in clients]
    
    @transactional
    def create_client(self, name, email=None, phone=None, entity_type=None, firm_id=None, user_id=None):
        """Create a new client"""
        if not name or not name.strip():
            return {'success': False, 'message': 'Client name is required'}
        
        client = Client(
            name=name.strip(),
            email=email.strip() if email else None,
            phone=phone.strip() if phone else None,
            entity_type=entity_type,
            firm_id=firm_id,
            is_active=True
        )
        
        db.session.add(client)
        
        # Log activity
        ActivityService.log_entity_operation(
            entity_type='CLIENT',
            operation='CREATE',
            entity_id=client.id,
            entity_name=client.name,
            details=f'Client created - Type: {entity_type}',
            user_id=user_id
        )
        
        # Publish client creation event
        from ...shared.events.schemas import ClientCreatedEvent
        from ...shared.events.publisher import publish_event
        event = ClientCreatedEvent(
            client_id=client.id,
            firm_id=firm_id,
            name=client.name,
            is_active=client.is_active
        )
        publish_event(event)
        
        return {
            'success': True,
            'message': 'Client created successfully',
            'client_id': client.id
        }
    
    def get_client_by_id(self, client_id, firm_id):
        """Get client by ID with firm access check"""
        return self.client_repository.get_by_id_and_firm(client_id, firm_id)
    
    @transactional
    def update_client(self, client_id, updates, firm_id, user_id):
        """Update client information"""
        client = self.get_client_by_id(client_id, firm_id)
        if not client:
            return {'success': False, 'message': 'Client not found or access denied'}
        
        # Update fields
        for field, value in updates.items():
            if hasattr(client, field):
                setattr(client, field, value)
        
        # Log activity
        ActivityService.log_entity_operation(
            entity_type='CLIENT',
            operation='UPDATE',
            entity_id=client.id,
            entity_name=client.name,
            details='Client information updated',
            user_id=user_id
        )
        
        return {'success': True, 'message': 'Client updated successfully'}
    
    def get_clients_by_firm_raw(self, firm_id):
        """Get all clients for a firm (alias for get_clients_for_firm)"""
        return self.client_repository.get_by_firm(firm_id)
