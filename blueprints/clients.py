"""
Client management blueprint
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime
from core import db
from models import Client, Project, Task, User, ActivityLog, Contact, ClientContact
from utils import create_activity_log

clients_bp = Blueprint('clients', __name__, url_prefix='/clients')


@clients_bp.route('/')
def list_clients():
    firm_id = session['firm_id']
    clients = Client.query.filter_by(firm_id=firm_id).order_by(Client.name.asc()).all()
    return render_template('clients/clients.html', clients=clients)


@clients_bp.route('/create', methods=['GET', 'POST'])
def create_client():
    if request.method == 'POST':
        firm_id = session['firm_id']
        
        client = Client(
            name=request.form.get('name'),
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            address=request.form.get('address'),
            contact_person=request.form.get('contact_person'),
            entity_type=request.form.get('entity_type', 'Individual'),
            tax_id=request.form.get('tax_id'),
            notes=request.form.get('notes'),
            firm_id=firm_id
        )
        db.session.add(client)
        db.session.commit()
        
        # Activity log
        create_activity_log(f'Client "{client.name}" created', session['user_id'])
        
        flash('Client created successfully!', 'success')
        return redirect(url_for('clients.list_clients'))
    
    return render_template('clients/create_client.html')


@clients_bp.route('/<int:id>')
def view_client(id):
    client = Client.query.get_or_404(id)
    if client.firm_id != session['firm_id']:
        flash('Access denied', 'error')
        return redirect(url_for('clients.list_clients'))
    
    projects = Project.query.filter_by(client_id=id).order_by(Project.created_at.desc()).all()
    
    # Get available contacts (not already associated with this client)
    associated_contact_ids = db.session.query(ClientContact.contact_id).filter_by(client_id=id).subquery()
    available_contacts = Contact.query.filter(~Contact.id.in_(associated_contact_ids)).all()
    
    return render_template('clients/view_client.html', client=client, projects=projects, available_contacts=available_contacts)