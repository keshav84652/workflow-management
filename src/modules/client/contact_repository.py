"""
ContactRepository: Data access layer for contact operations
"""

from typing import List, Optional
from src.shared.database.db_import import db
from .models import Contact, ClientContact, Client
from src.shared.repositories.base import BaseRepository


class ContactRepository(BaseRepository):
    """Repository for contact data access"""
    
    def __init__(self):
        super().__init__(Contact)
    
    def get_contacts_for_firm(self, firm_id: int) -> List[Contact]:
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
    
    def get_association_by_contact_and_client(self, contact_id: int, client_id: int) -> Optional[ClientContact]:
        """Get association between contact and client"""
        return ClientContact.query.filter_by(
            contact_id=contact_id, 
            client_id=client_id
        ).first()
    
    def get_primary_contact_for_client(self, client_id: int) -> Optional[ClientContact]:
        """Get primary contact for a client"""
        return ClientContact.query.filter_by(
            client_id=client_id, 
            is_primary=True
        ).first()
    
    def update_primary_contacts_for_client(self, client_id: int) -> None:
        """Remove primary flag from all contacts for a client"""
        ClientContact.query.filter_by(
            client_id=client_id, 
            is_primary=True
        ).update({'is_primary': False})
    
    def create_client_contact_association(self, contact_id: int, client_id: int, 
                                        relationship_type: str = 'contact', 
                                        is_primary: bool = False) -> ClientContact:
        """Create association between contact and client"""
        association = ClientContact(
            contact_id=contact_id,
            client_id=client_id,
            relationship_type=relationship_type,
            is_primary=is_primary
        )
        db.session.add(association)
        return association
    
    def delete_client_contact_association(self, contact_id: int, client_id: int) -> bool:
        """Delete association between contact and client"""
        association = self.get_association_by_contact_and_client(contact_id, client_id)
        if association:
            db.session.delete(association)
            return True
        return False
    
    def get_contacts_by_client_and_firm(self, client_id: int, firm_id: int) -> List[Contact]:
        """Get all contacts for a specific client with firm access check"""
        return db.session.query(Contact).join(ClientContact).join(Client).filter(
            ClientContact.client_id == client_id,
            Client.firm_id == firm_id
        ).all()
    
    def get_clients_for_contact_and_firm(self, contact_id: int, firm_id: int) -> List:
        """Get all clients associated with a contact for a specific firm"""
        from src.models import Client
        return db.session.query(Client).join(ClientContact).filter(
            ClientContact.contact_id == contact_id,
            Client.firm_id == firm_id
        ).all()