"""
ClientService: Handles all business logic for clients, including search and retrieval.
"""

from models import Client

class ClientService:
    @staticmethod
    def search_clients(firm_id, query):
        if not query:
            return []
        clients = Client.query.filter(
            Client.firm_id == firm_id,
            Client.name.contains(query)
        ).limit(10).all()
        return [{
            'id': client.id,
            'name': client.name,
            'entity_type': client.entity_type
        } for client in clients]

    @staticmethod
    def get_clients_for_firm(firm_id):
        clients = Client.query.filter_by(firm_id=firm_id).all()
        return [{
            'id': client.id,
            'name': client.name,
            'entity_type': client.entity_type,
            'email': client.email,
            'phone': client.phone,
            'is_active': client.is_active
        } for client in clients]