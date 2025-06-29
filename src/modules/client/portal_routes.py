"""
Client portal blueprint
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify

from .portal_service import PortalService

client_portal_bp = Blueprint('client_portal', __name__)


@client_portal_bp.route('/client-portal')
@client_portal_bp.route('/client-login')
def client_login():
    """Client portal login page"""
    return render_template('clients/client_login.html')


@client_portal_bp.route('/client-authenticate', methods=['POST'])
def client_authenticate():
    """Authenticate client user"""
    access_code = request.form.get('access_code', '').strip()
    
    result = PortalService.authenticate_client(access_code)
    
    if result['success']:
        session['client_user_id'] = result['client_user_id']
        session['client_id'] = result['client_id']
        session['client_email'] = result['client_email']
        return redirect(url_for('client_portal.client_dashboard'))
    else:
        flash(result['message'], 'error')
        return redirect(url_for('client_portal.client_login'))


@client_portal_bp.route('/client-dashboard')
def client_dashboard():
    """Client portal dashboard"""
    if 'client_user_id' not in session:
        return redirect(url_for('client_portal.client_login'))
    
    client_id = session['client_id']
    
    # Get dashboard data using service
    dashboard_data = PortalService.get_client_dashboard_data(client_id)
    
    if not dashboard_data['success']:
        flash(dashboard_data['message'], 'error')
        return redirect(url_for('client_portal.client_login'))
    
    return render_template(
        'clients/client_dashboard_modern.html',
        client=dashboard_data['client'],
        checklists=dashboard_data['checklists']
    )


@client_portal_bp.route('/client-logout')
def client_logout():
    """Client logout"""
    session.pop('client_user_id', None)
    session.pop('client_id', None)
    session.pop('client_email', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('client_portal.client_login'))


@client_portal_bp.route('/client-upload/<int:item_id>', methods=['POST'])
def client_upload_document(item_id):
    """Handle client document upload"""
    if 'client_user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    client_id = session['client_id']
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400
    
    # Use service to handle upload
    result = PortalService.upload_client_document(file, item_id, client_id)
    
    if result['success']:
        return jsonify({
            'success': True,
            'message': result['message'],
            'filename': result['filename']
        })
    else:
        status_code = 404 if 'Invalid document item' in result['message'] else 500
        return jsonify({
            'success': False,
            'message': result['message']
        }), status_code


@client_portal_bp.route('/client-update-status/<int:item_id>', methods=['POST'])
def client_update_status(item_id):
    """Update document item status (already provided, not applicable)"""
    if 'client_user_id' not in session:
        flash('Not authenticated', 'error')
        return redirect(url_for('client_portal.client_login'))
    
    client_id = session['client_id']
    new_status = request.form.get('status')
    
    # Use service to handle status update
    result = PortalService.update_item_status(item_id, client_id, new_status)
    
    if result['success']:
        flash(result['message'], 'success')
    else:
        flash(result['message'], 'error')
    
    return redirect(url_for('client_portal.client_dashboard'))