"""
Authentication service layer for business logic
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from flask import session, request
from flask_bcrypt import Bcrypt
from core.db_import import db
from models import Firm, User, DemoAccessRequest
from repositories.firm_repository import FirmRepository
from repositories.user_repository import UserRepository


class AuthService:
    """Service class for authentication-related business operations"""

    def __init__(self):
        self.firm_repository = FirmRepository()
        self.user_repository = UserRepository()
        self.bcrypt = Bcrypt()
    

    def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate a user using email and password
        
        Args:
            email: User's email address
            password: User's password
            
        Returns:
            Dict containing success status, user data, firm data, and any error messages
        """
        try:
            # Clean input
            email = email.strip().lower()
            
            # Find user by email
            user = self.user_repository.get_by_email(email)
            
            if not user:
                return {
                    'success': False,
                    'message': 'Invalid email or password',
                    'user': None,
                    'firm': None
                }
            
            # Verify password
            if not self.bcrypt.check_password_hash(user.password_hash, password):
                return {
                    'success': False,
                    'message': 'Invalid email or password',
                    'user': None,
                    'firm': None
                }
            
            # Get firm data
            firm = self.firm_repository.get_by_id(user.firm_id)
            
            if not firm or not firm.is_active:
                return {
                    'success': False,
                    'message': 'Your firm account is not active',
                    'user': None,
                    'firm': None
                }
            
            return {
                'success': True,
                'message': 'Authentication successful',
                'user': {
                    'id': user.id,
                    'name': user.name,
                    'email': user.email,
                    'role': user.role
                },
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
                'user': None,
                'firm': None
            }
    

    def authenticate_firm_by_code(self, access_code: str) -> Optional[Firm]:
        """
        Authenticate a firm using access code only
        
        Args:
            access_code: The firm's access code
            
        Returns:
            Firm object if found and active, None otherwise
        """
        return self.firm_repository.get_by_access_code(access_code, active_only=True)
    
    def get_users_for_firm(self, firm_id: int) -> List[User]:
        """
        Get all users for a specific firm (static method for blueprint usage)
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            List of User objects for the firm
        """
        return self.user_repository.get_by_firm(firm_id)
    
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
    

    def get_firm_users(self, firm_id: int) -> List[User]:
        """
        Get all users for a specific firm
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            List of User objects for the firm
        """
        return self.user_repository.get_by_firm(firm_id)
    

    def get_user_by_id(self, user_id: int, firm_id: int) -> Optional[User]:
        """
        Get a user by ID, ensuring they belong to the specified firm
        
        Args:
            user_id: The user's ID
            firm_id: The firm's ID for security check
            
        Returns:
            User object if found and belongs to firm, None otherwise
        """
        return self.user_repository.get_by_id_and_firm(user_id, firm_id)
    

    def create_session(self, user_data: Dict[str, Any], firm_data: Dict[str, Any]) -> None:
        """
        Create a persistent session for authenticated user
        
        Args:
            user_data: Dictionary containing user information
            firm_data: Dictionary containing firm information
        """
        # Make session permanent for better persistence
        session.permanent = True
        
        # Store user and firm data in session
        session['user_id'] = user_data['id']
        session['user_name'] = user_data['name']
        session['user_email'] = user_data['email']
        session['user_role'] = user_data['role']
        session['firm_id'] = firm_data['id']
        session['firm_name'] = firm_data['name']
    

    def set_user_in_session(self, user_id: int, firm_id: int) -> Dict[str, Any]:
        """
        Set the selected user in the session
        
        Args:
            user_id: The selected user's ID
            firm_id: The firm's ID for security check
            
        Returns:
            Dict containing success status and user data
        """
        try:
            user = self.get_user_by_id(user_id, firm_id)
            
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
    
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        return self.bcrypt.generate_password_hash(password).decode('utf-8')
    
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verify a password against its hash
        
        Args:
            password: Plain text password
            password_hash: Hashed password
            
        Returns:
            True if password matches, False otherwise
        """
        return self.bcrypt.check_password_hash(password_hash, password)