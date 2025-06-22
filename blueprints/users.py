"""
User management blueprint
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from core import db
from models import User

users_bp = Blueprint('users', __name__, url_prefix='/users')


@users_bp.route('/')
def list_users():
    firm_id = session['firm_id']
    users = User.query.filter_by(firm_id=firm_id).all()
    return render_template('admin/users.html', users=users)


@users_bp.route('/create', methods=['GET', 'POST'])
def create_user():
    if request.method == 'POST':
        firm_id = session['firm_id']
        
        user = User(
            name=request.form.get('name'),
            role=request.form.get('role', 'Member'),
            firm_id=firm_id
        )
        db.session.add(user)
        db.session.commit()
        
        flash('User created successfully!', 'success')
        return redirect(url_for('users.list_users'))
    
    return render_template('admin/create_user.html')