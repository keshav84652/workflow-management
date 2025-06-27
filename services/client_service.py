"""
ClientService: Handles all business logic for clients, including search and retrieval.
"""

from core.db_import import db
from models import Client
from services.activity_logging_service import ActivityLoggingService as ActivityService


class ClientService:
    @staticmethod
    def search_clients(firm_id, query, limit=20):
        """
        Search clients by name, email, and contact person for a specific firm
        This replaces direct database access in blueprints
        """
        if not query:
            return []
        
        # Build search filters
        client_filters = db.or_(
            Client.name.ilike(f'%{query}%'),
            Client.email.ilike(f'%{query}%'),
            Client.contact_person.ilike(f'%{query}%') if hasattr(Client, 'contact_person') else False
        )
        
        clients = Client.query.filter(
            Client.firm_id == firm_id
        ).filter(client_filters).limit(limit).all()
        
        return clients

    @staticmethod
    def get_clients_for_firm(firm_id):
        """Get all clients for a firm"""
        clients = Client.query.filter_by(firm_id=firm_id).all()
        return [{
            'id': client.id,
            'name': client.name,
            'entity_type': client.entity_type,
            'email': client.email,
            'phone': client.phone,
            'is_active': client.is_active
        } for client in clients]
    
    @staticmethod
    def create_client(name, email=None, phone=None, entity_type=None, firm_id=None, user_id=None):
        """Create a new client"""
        try:
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
            db.session.commit()
            
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
            from events.schemas import ClientCreatedEvent
            from events.publisher import publish_event
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
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def get_client_by_id(client_id, firm_id):
        """Get client by ID with firm access check"""
        return Client.query.filter_by(id=client_id, firm_id=firm_id).first()
    
    @staticmethod
    def update_client(client_id, updates, firm_id, user_id):
        """Update client information"""
        try:
            client = ClientService.get_client_by_id(client_id, firm_id)
            if not client:
                return {'success': False, 'message': 'Client not found or access denied'}
            
            # Update fields
            for field, value in updates.items():
                if hasattr(client, field):
                    setattr(client, field, value)
            
            db.session.commit()
            
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
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def get_clients_by_firm(firm_id):
        """Get all clients for a firm (alias for get_clients_for_firm)"""
        return Client.query.filter_by(firm_id=firm_id).all()
