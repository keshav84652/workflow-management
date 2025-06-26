"""
Authentication service layer for business logic
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from flask import session, request
import importlib.util
import os

# Import db from root core.py file
spec = importlib.util.spec_from_file_location("core", os.path.join(os.path.dirname(os.path.dirname(__file__)), "core.py"))
core_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core_module)
db = core_module.db
from models import Firm, User, DemoAccessRequest


class AuthService:
    """Service class for authentication-related business operations"""
    
    @staticmethod
    def authenticate_firm(access_code: str, email: str) -> Dict[str, Any]:
        """
        Authenticate a firm using access code and optional email
        
        Args:
            access_code: The firm's access code
            email: User's email for tracking purposes
            
        Returns:
            Dict containing success status, firm data, and any error messages
        """
        try:
            # Clean input
            access_code = access_code.strip()
            email = email.strip()
            
            # Find active firm with matching access code
            firm = Firm.query.filter_by(access_code=access_code, is_active=True).first()
            
            if not firm:
                return {
                    'success': False,
                    'message': 'Invalid access code',
                    'firm': None
                }
            
            # Handle demo access tracking
            if access_code == 'DEMO2024':
                AuthService._track_demo_access(email)
            
            return {
                'success': True,
                'message': 'Authentication successful',
                'firm': {
                    'id': firm.id,
                    'name': firm.name,
                    'access_code': firm.access_code
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Authentication error: {str(e)}',
                'firm': None
            }
    
    @staticmethod
    def _track_demo_access(email: str) -> None:
        """
        Track demo access requests for analytics
        
        Args:
            email: User's email address
        """
        try:
            # Check if email already exists for demo access
            existing_request = db.session.execute(
                db.text("SELECT * FROM demo_access_request WHERE email = :email AND firm_access_code = 'DEMO2024'"),
                {'email': email}
            ).first()
            
            if not existing_request:
                # Create new demo access record
                db.session.execute(
                    db.text("""
                        INSERT INTO demo_access_request 
                        (email, firm_access_code, ip_address, user_agent, granted, granted_at, created_at) 
                        VALUES (:email, 'DEMO2024', :ip_address, :user_agent, 1, :granted_at, :created_at)
                    """),
                    {
                        'email': email,
                        'ip_address': request.remote_addr,
                        'user_agent': request.headers.get('User-Agent', ''),
                        'granted_at': datetime.utcnow(),
                        'created_at': datetime.utcnow()
                    }
                )
                db.session.commit()
                
        except Exception as e:
            # Don't block access if demo tracking fails
            print(f"Demo tracking error: {e}")
    
    @staticmethod
    def get_firm_users(firm_id: int) -> List[User]:
        """
        Get all users for a specific firm
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            List of User objects for the firm
        """
        return User.query.filter_by(firm_id=firm_id).all()
    
    @staticmethod
    def get_user_by_id(user_id: int, firm_id: int) -> Optional[User]:
        """
        Get a user by ID, ensuring they belong to the specified firm
        
        Args:
            user_id: The user's ID
            firm_id: The firm's ID for security check
            
        Returns:
            User object if found and belongs to firm, None otherwise
        """
        return User.query.filter_by(id=user_id, firm_id=firm_id).first()
    
    @staticmethod
    def create_session(firm_data: Dict[str, Any], email: str) -> None:
        """
        Create a persistent session for authenticated firm
        
        Args:
            firm_data: Dictionary containing firm information
            email: User's email for tracking
        """
        # Make session permanent for better persistence
        session.permanent = True
        
        # Store firm and user data in session
        session['user_email'] = email
        session['firm_id'] = firm_data['id']
        session['firm_name'] = firm_data['name']
    
    @staticmethod
    def set_user_in_session(user_id: int, firm_id: int) -> Dict[str, Any]:
        """
        Set the selected user in the session
        
        Args:
            user_id: The selected user's ID
            firm_id: The firm's ID for security check
            
        Returns:
            Dict containing success status and user data
        """
        try:
            user = AuthService.get_user_by_id(user_id, firm_id)
            
            if not user:
                return {
                    'success': False,
                    'message': 'User not found or does not belong to your firm'
                }
            
            # Set user data in session
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['user_role'] = user.role
            
            return {
                'success': True,
                'message': 'User selected successfully',
                'user': {
                    'id': user.id,
                    'name': user.name,
                    'role': user.role
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error setting user: {str(e)}'
            }
    
    @staticmethod
    def is_authenticated() -> bool:
        """
        Check if the current session is authenticated
        
        Returns:
            True if both firm_id and user_id are in session, False otherwise
        """
        return 'firm_id' in session and 'user_id' in session
    
    @staticmethod
    def is_firm_authenticated() -> bool:
        """
        Check if a firm is authenticated (but user may not be selected)
        
        Returns:
            True if firm_id is in session, False otherwise
        """
        return 'firm_id' in session
    
    @staticmethod
    def logout() -> None:
        """
        Clear the session and log out the user
        """
        session.clear()
    
    @staticmethod
    def get_current_user_info() -> Dict[str, Any]:
        """
        Get current user information from session
        
        Returns:
            Dictionary containing current user and firm information
        """
        return {
            'user_id': session.get('user_id'),
            'user_name': session.get('user_name'),
            'user_role': session.get('user_role'),
            'user_email': session.get('user_email'),
            'firm_id': session.get('firm_id'),
            'firm_name': session.get('firm_name')
        }
    
    @staticmethod
    def require_authentication() -> Optional[str]:
        """
        Check if user is authenticated, return redirect URL if not
        
        Returns:
            None if authenticated, redirect URL string if not authenticated
        """
        if not AuthService.is_authenticated():
            if AuthService.is_firm_authenticated():
                return 'auth.select_user'
            else:
                return 'auth.login'
        return None