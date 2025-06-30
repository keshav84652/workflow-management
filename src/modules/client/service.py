"""
ClientService: Handles all business logic for clients, including search and retrieval.
"""

from typing import Dict, Any, Optional
from src.shared.database.db_import import db
from .models import Client
# ActivityService import removed to break circular dependency
from src.shared.base import BaseService, transactional
from .interface import IClientService
from .repository import ClientRepository


class ClientService(BaseService, IClientService):
    def __init__(self, client_repository=None):
        super().__init__()
        # Use dependency injection - accept repository as constructor parameter
        if client_repository is None:
            # Fallback for legacy instantiation - will be removed once DI is fully implemented
            client_repository = ClientRepository()
        self.client_repository = client_repository
    
    def search_clients(self, firm_id, query, limit=20):
        """
        Search clients by name, email, and contact person for a specific firm
        This replaces direct database access in blueprints
        """
        if not query:
            return {'success': True, 'clients': []}
        
        try:
            # Use repository search method
            clients = self.client_repository.search_by_name(firm_id, query, limit)
            return {
                'success': True,
                'clients': [{
                    'id': client.id,
                    'name': client.name,
                    'email': client.email,
                    'phone': client.phone,
                    'entity_type': client.entity_type,
                    'is_active': client.is_active
                } for client in clients]
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e),
                'clients': []
            }

    def get_clients_by_firm(self, firm_id):
        """Get all clients for a specific firm (raw objects)"""
        return self.client_repository.get_by_firm(firm_id)
    
    def get_active_clients_by_firm(self, firm_id):
        """Get all active clients for a specific firm"""
        clients = self.client_repository.get_by_firm(firm_id, include_inactive=False)
        return [{
            'id': client.id,
            'name': client.name,
            'email': client.email,
            'phone': client.phone,
            'address': client.address,
            'entity_type': client.entity_type,
            'is_active': client.is_active,
            'firm_id': client.firm_id,
            'created_at': client.created_at.strftime('%Y-%m-%d %H:%M') if client.created_at else None
        } for client in clients]
    
    def get_client_by_id_and_firm(self, client_id, firm_id):
        """Get client by ID with firm access check"""
        client = self.client_repository.get_by_id_and_firm(client_id, firm_id)
        if not client:
            return None
        
        # Return DTO instead of raw model to prevent N+1 queries in templates
        return {
            'id': client.id,
            'name': client.name,
            'email': client.email,
            'phone': client.phone,
            'address': client.address,
            'entity_type': client.entity_type,
            'is_active': client.is_active,
            'firm_id': client.firm_id,
            'created_at': client.created_at.strftime('%Y-%m-%d %H:%M') if client.created_at else None
        }
        
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
    def create_client(self, client_data: Dict[str, Any], firm_id: int, user_id: int) -> Dict[str, Any]:
        """Create a new client"""
        name = client_data.get('name', '').strip()
        if not name:
            return {'success': False, 'message': 'Client name is required'}
        
        client = Client(
            name=name,
            email=client_data.get('email', '').strip() if client_data.get('email') else None,
            phone=client_data.get('phone', '').strip() if client_data.get('phone') else None,
            entity_type=client_data.get('entity_type'),
            firm_id=firm_id,
            is_active=True
        )
        
        db.session.add(client)
        
        # Log activity - direct import to avoid circular dependency
        try:
            from src.shared.services.activity_service import ActivityService
            ActivityService.log_entity_operation(
                entity_type='CLIENT',
                operation='CREATE',
                entity_id=client.id,
                entity_name=client.name,
                details=f'Client created - Type: {entity_type}',
                user_id=user_id
            )
        except ImportError:
            pass  # ActivityService not available
        
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
            'client': {
                'id': client.id,
                'name': client.name,
                'email': client.email,
                'phone': client.phone,
                'entity_type': client.entity_type,
                'is_active': client.is_active,
                'firm_id': client.firm_id
            }
        }
    
    def get_client_by_id(self, client_id, firm_id):
        """Get client by ID with firm access check"""
        return self.get_client_by_id_and_firm(client_id, firm_id)  # Use the DTO method
    
    @transactional
    def update_client(self, client_id: int, client_data: Dict[str, Any], firm_id: int, user_id: int) -> Dict[str, Any]:
        """Update client information"""
        # Get raw model for updates, not DTO
        client = self.client_repository.get_by_id_and_firm(client_id, firm_id)
        if not client:
            return {'success': False, 'message': 'Client not found or access denied'}
        
        # Update fields
        for field, value in client_data.items():
            if hasattr(client, field):
                setattr(client, field, value)
        
        # Log activity - direct import to avoid circular dependency
        try:
            from src.shared.services.activity_service import ActivityService
            ActivityService.log_entity_operation(
                entity_type='CLIENT',
                operation='UPDATE',
                entity_id=client.id,
                entity_name=client.name,
                details='Client information updated',
                user_id=user_id
            )
        except ImportError:
            pass  # ActivityService not available
        
        return {'success': True, 'message': 'Client updated successfully'}
    
    def get_clients_by_firm_raw(self, firm_id):
        """Get all clients for a firm (alias for get_clients_for_firm)"""
        return self.client_repository.get_by_firm(firm_id)
    
    def get_client_statistics(self, firm_id: int) -> dict:
        """Get client statistics for dashboard"""
        try:
            from src.models import Client
            
            total = Client.query.filter_by(firm_id=firm_id).count()
            # For now, consider all clients as active (can add is_active field later)
            active = total
            
            return {
                'success': True,
                'statistics': {
                    'total': total,
                    'active': active
                }
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to get client statistics: {str(e)}',
                'statistics': {}
            }
    
    def get_clients_for_api(self, firm_id: int) -> dict:
        """Get all clients for a firm formatted for API response"""
        try:
            clients_raw = self.client_repository.get_by_firm(firm_id)
            
            clients = []
            for client in clients_raw:
                client_dict = {
                    'id': client.id,
                    'name': client.name,
                    'email': client.email,
                    'phone': client.phone,
                    'address': client.address,
                    'status': 'Active',  # Default status for now
                    'created_at': client.created_at.strftime('%Y-%m-%d %H:%M') if client.created_at else ''
                }
                clients.append(client_dict)
            
            return {
                'success': True,
                'clients': clients
            }
        except Exception as e:
            return {
                'success': False,
                'clients': [],
                'message': str(e)
            }
    
    def _get_client_model_by_id_and_firm(self, client_id, firm_id):
        """Get raw client model for internal operations (updates/deletes)"""
        return self.client_repository.get_by_id_and_firm(client_id, firm_id)
    
    # Legacy wrapper methods for backward compatibility
    def create_client_legacy(self, name, email=None, phone=None, entity_type=None, firm_id=None, user_id=None):
        """Legacy wrapper for create_client with individual parameters"""
        client_data = {
            'name': name,
            'email': email,
            'phone': phone,
            'entity_type': entity_type
        }
        return self.create_client(client_data, firm_id, user_id)
    
    def update_client_legacy(self, client_id, updates, firm_id, user_id):
        """Legacy wrapper for update_client with updates dict"""
        return self.update_client(client_id, updates, firm_id, user_id)
