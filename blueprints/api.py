"""
API endpoints blueprint

UPDATED: Modernized with standardized session management and clean imports.
"""

from flask import Blueprint, jsonify, request, session
from core.db_import import db
from models import Client, Project, Task, User
from services.base import SessionService
from services.auth_service import AuthService
from services.task_service import TaskService
from services.project_service import ProjectService
from services.dashboard_aggregator_service import DashboardAggregatorService

api_bp = Blueprint('api', __name__, url_prefix='/api')

# Authentication endpoints
@api_bp.route('/auth/login', methods=['POST'])
def api_login():
    """API endpoint for user authentication"""
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if not username or not password:
        return jsonify({
            'success': False,
            'message': 'Username and password are required'
        }), 400
    
    # First authenticate with demo firm (DEMO2024)
    auth_service = AuthService()
    firm_result = auth_service.authenticate_firm('DEMO2024', '')
    
    if not firm_result['success']:
        return jsonify({
            'success': False,
            'message': 'Authentication failed'
        }), 401
    
    # Create firm session
    auth_service.create_session(firm_result['firm'], '')
    
    # Map simple usernames to actual user names in the database
    user_mapping = {
        'admin': 'Sarah Johnson',  # Admin user
        'manager': 'Michael Chen',  # Admin user (can act as manager)
        'senior': 'Emily Rodriguez',  # Member user (can act as senior)
        'staff': 'David Park'  # Member user (can act as staff)
    }
    
    actual_name = user_mapping.get(username.lower())
    if not actual_name:
        return jsonify({
            'success': False,
            'message': 'Invalid credentials'
        }), 401
    
    # Find user by actual name
    firm_id = session['firm_id']
    user = User.query.filter_by(name=actual_name, firm_id=firm_id).first()
    
    if not user:
        return jsonify({
            'success': False,
            'message': 'Invalid credentials'
        }), 401
    
    # Simple password check (in production, use proper hashing)
    valid_passwords = {
        'admin': 'admin123',
        'manager': 'manager123',
        'senior': 'senior123',
        'staff': 'staff123'
    }
    
    if valid_passwords.get(username.lower()) != password:
        return jsonify({
            'success': False,
            'message': 'Invalid credentials'
        }), 401
    
    # Set user in session
    user_result = auth_service.set_user_in_session(user.id, firm_id)
    
    if user_result['success']:
        return jsonify({
            'success': True,
            'data': {
                'user': {
                    'id': user.id,
                    'username': username,  # Use the simple username
                    'email': f'{username}@demo.com',  # Mock email with simple username
                    'role': user.role,
                    'firm_id': user.firm_id,
                    'firm_name': session.get('firm_name', 'Demo Firm')
                },
                'token': 'demo-token'  # In production, use JWT
            }
        })
    else:
        return jsonify({
            'success': False,
            'message': user_result['message']
        }), 401

@api_bp.route('/auth/me', methods=['GET'])
def api_current_user():
    """Get current authenticated user"""
    if not AuthService.is_authenticated():
        return jsonify({
            'success': False,
            'message': 'Not authenticated'
        }), 401
    
    user_id = session.get('user_id')
    firm_id = session.get('firm_id')
    
    user = User.query.filter_by(id=user_id, firm_id=firm_id).first()
    
    if not user:
        return jsonify({
            'success': False,
            'message': 'User not found'
        }), 404
    
    return jsonify({
        'success': True,
        'data': {
            'id': user.id,
            'username': user.name,
            'email': f'{user.name}@demo.com',  # Mock email
            'role': user.role,
            'firm_id': user.firm_id,
            'firm_name': session.get('firm_name', 'Demo Firm')
        }
    })

@api_bp.route('/auth/logout', methods=['POST'])
def api_logout():
    """Logout current user"""
    session.clear()
    return jsonify({
        'success': True,
        'message': 'Logged out successfully'
    })

# Dashboard endpoints
@api_bp.route('/dashboard/stats', methods=['GET'])
def api_dashboard_stats():
    """Get dashboard statistics"""
    if not AuthService.is_authenticated():
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    # Return mock dashboard stats for demo
    stats = {
        'total_tasks': 25,
        'pending_tasks': 8,
        'completed_tasks': 15,
        'overdue_tasks': 2,
        'total_projects': 5,
        'active_projects': 3,
        'total_clients': 12,
        'recent_activities': [
            {
                'id': 1,
                'message': 'Task "Review Q4 Financial Statements" was completed',
                'user': 'Sarah Johnson',
                'timestamp': '2024-01-15T10:30:00Z'
            },
            {
                'id': 2,
                'message': 'New project "Tax Season 2024" was created',
                'user': 'Michael Chen',
                'timestamp': '2024-01-14T15:45:00Z'
            }
        ]
    }
    
    return jsonify({
        'success': True,
        'data': stats
    })

@api_bp.route('/dashboard/activity', methods=['GET'])
def api_recent_activity():
    """Get recent activity"""
    if not AuthService.is_authenticated():
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    limit = request.args.get('limit', 10, type=int)
    # For now, return mock data
    activities = [
        {
            'id': 1,
            'message': 'Task "Review Q4 Financial Statements" was completed',
            'user': 'John Doe',
            'timestamp': '2024-01-15T10:30:00Z'
        },
        {
            'id': 2,
            'message': 'New project "Tax Season 2024" was created',
            'user': 'Jane Smith',
            'timestamp': '2024-01-14T15:45:00Z'
        }
    ]
    
    return jsonify({
        'success': True,
        'data': activities[:limit]
    })

# Task endpoints
@api_bp.route('/tasks', methods=['GET'])
def api_get_tasks():
    """Get tasks for the current user/firm"""
    if not AuthService.is_authenticated():
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    firm_id = SessionService.get_current_firm_id()
    task_service = TaskService()
    
    # Get query parameters
    status = request.args.get('status')
    project_id = request.args.get('project_id', type=int)
    assigned_to = request.args.get('assigned_to', type=int)
    
    # Build filters
    filters = {}
    if status:
        filters['status'] = status
    if project_id:
        filters['project_id'] = project_id
    if assigned_to:
        filters['assigned_to'] = assigned_to
    
    result = task_service.get_filtered_tasks(firm_id, filters)
    
    if result['success']:
        return jsonify({
            'success': True,
            'data': result['tasks']
        })
    else:
        return jsonify({
            'success': False,
            'message': result['message']
        }), 400

@api_bp.route('/tasks/<int:task_id>/status', methods=['PATCH'])
def api_update_task_status(task_id):
    """Update task status"""
    if not AuthService.is_authenticated():
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    data = request.get_json()
    status = data.get('status')
    
    if not status:
        return jsonify({
            'success': False,
            'message': 'Status is required'
        }), 400
    
    firm_id = SessionService.get_current_firm_id()
    user_id = SessionService.get_current_user_id()
    
    task_service = TaskService()
    result = task_service.update_task_status(task_id, status, firm_id, user_id)
    
    if result['success']:
        return jsonify({
            'success': True,
            'data': result['task']
        })
    else:
        return jsonify({
            'success': False,
            'message': result['message']
        }), 400


from services.client_service import ClientService

@api_bp.route('/clients/search')
def search_clients():
    firm_id = SessionService.get_current_firm_id()
    query = request.args.get('q', '').strip()
    client_service = ClientService()
    results = client_service.search_clients(firm_id, query)
    return jsonify(results)


from services.project_service import ProjectService

@api_bp.route('/project/<int:project_id>/progress', methods=['GET'])
def get_project_progress(project_id):
    firm_id = SessionService.get_current_firm_id()
    project_service = ProjectService()
    result = project_service.get_project_progress(project_id, firm_id)
    if isinstance(result, tuple):
        # Error with status code
        return jsonify(result[0]), result[1]
    return jsonify(result)


# Projects endpoints
@api_bp.route('/projects', methods=['GET'])
def api_get_projects():
    """Get projects for the current firm"""
    if not AuthService.is_authenticated():
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    firm_id = SessionService.get_current_firm_id()
    project_service = ProjectService()
    
    # Get query parameters
    status = request.args.get('status')
    client_id = request.args.get('client_id', type=int)
    
    # Build filters
    filters = {}
    if status:
        filters['status'] = status
    if client_id:
        filters['client_id'] = client_id
    
    result = project_service.get_filtered_projects(firm_id, filters)
    
    if result.get('success', True):
        return jsonify({
            'success': True,
            'data': result.get('projects', result)
        })
    else:
        return jsonify({
            'success': False,
            'message': result.get('message', 'Failed to fetch projects')
        }), 400

@api_bp.route('/projects/<int:project_id>', methods=['GET'])
def api_get_project(project_id):
    """Get a specific project"""
    if not AuthService.is_authenticated():
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    firm_id = SessionService.get_current_firm_id()
    project_service = ProjectService()
    
    result = project_service.get_project_by_id(project_id, firm_id)
    
    if result.get('success', True):
        return jsonify({
            'success': True,
            'data': result.get('project', result)
        })
    else:
        return jsonify({
            'success': False,
            'message': result.get('message', 'Project not found')
        }), 404

@api_bp.route('/projects/<int:project_id>/tasks', methods=['GET'])
def api_get_project_tasks(project_id):
    """Get tasks for a specific project"""
    if not AuthService.is_authenticated():
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    firm_id = SessionService.get_current_firm_id()
    task_service = TaskService()
    
    result = task_service.get_filtered_tasks(firm_id, {'project_id': project_id})
    
    if result.get('success', True):
        return jsonify({
            'success': True,
            'data': result.get('tasks', result)
        })
    else:
        return jsonify({
            'success': False,
            'message': result.get('message', 'Failed to fetch project tasks')
        }), 400

# Clients endpoints
@api_bp.route('/clients', methods=['GET'])
def api_get_clients():
    """Get clients for the current firm"""
    if not AuthService.is_authenticated():
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    firm_id = SessionService.get_current_firm_id()
    client_service = ClientService()
    
    # Get query parameters
    search = request.args.get('search')
    
    if search:
        results = client_service.search_clients(firm_id, search)
    else:
        results = client_service.get_clients_for_firm(firm_id)
    
    # Ensure consistent response format
    if isinstance(results, dict) and 'success' in results:
        return jsonify(results)
    else:
        return jsonify({
            'success': True,
            'data': results if isinstance(results, list) else []
        })

@api_bp.route('/clients/<int:client_id>', methods=['GET'])
def api_get_client(client_id):
    """Get a specific client"""
    if not AuthService.is_authenticated():
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    firm_id = SessionService.get_current_firm_id()
    client_service = ClientService()
    
    result = client_service.get_client_by_id(client_id, firm_id)
    
    if result.get('success', True):
        return jsonify({
            'success': True,
            'data': result.get('client', result)
        })
    else:
        return jsonify({
            'success': False,
            'message': result.get('message', 'Client not found')
        }), 404

@api_bp.route('/clients/<int:client_id>/projects', methods=['GET'])
def api_get_client_projects(client_id):
    """Get projects for a specific client"""
    if not AuthService.is_authenticated():
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    firm_id = SessionService.get_current_firm_id()
    project_service = ProjectService()
    
    result = project_service.get_filtered_projects(firm_id, {'client_id': client_id})
    
    if result.get('success', True):
        return jsonify({
            'success': True,
            'data': result.get('projects', result)
        })
    else:
        return jsonify({
            'success': False,
            'message': result.get('message', 'Failed to fetch client projects')
        }), 400
