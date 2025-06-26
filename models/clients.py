"""
Client and contact management models
"""

from datetime import datetime
import importlib.util
import os

# Import db from root core.py file
spec = importlib.util.spec_from_file_location("core", os.path.join(os.path.dirname(os.path.dirname(__file__)), "core.py"))
core_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core_module)
db = core_module.db


class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    contact_person = db.Column(db.String(100))
    entity_type = db.Column(db.String(50))  # Individual, Corp, LLC, Partnership, etc.
    tax_id = db.Column(db.String(20))  # EIN or SSN
    notes = db.Column(db.Text)
    firm_id = db.Column(db.Integer, db.ForeignKey('firm.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    projects = db.relationship('Project', backref='client', lazy=True)
    
    @property
    def contacts(self):
        """Get all contacts associated with this client"""
        return db.session.query(Contact).join(ClientContact).filter(
            ClientContact.client_id == self.id
        ).all()
    
    @property
    def primary_contact(self):
        """Get the primary contact for this client"""
        return db.session.query(Contact).join(ClientContact).filter(
            ClientContact.client_id == self.id,
            ClientContact.is_primary == True
        ).first()


class Contact(db.Model):
    """Individual contacts that can be associated with multiple clients"""
    __tablename__ = 'contact'
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    title = db.Column(db.String(100))  # Job title/role
    company = db.Column(db.String(200))  # Company name
    address = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships (many-to-many with clients)
    client_contacts = db.relationship('ClientContact', backref='contact', lazy=True)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class ClientContact(db.Model):
    """Many-to-many relationship between clients and contacts"""
    __tablename__ = 'client_contact'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    contact_id = db.Column(db.Integer, db.ForeignKey('contact.id'), nullable=False)
    is_primary = db.Column(db.Boolean, default=False, nullable=False)
    relationship_type = db.Column(db.String(50))  # 'Owner', 'Accountant', 'Bookkeeper', etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    client = db.relationship('Client', backref='client_contacts')
    
    # Ensure unique client-contact pairs
    __table_args__ = (db.UniqueConstraint('client_id', 'contact_id', name='unique_client_contact'),)