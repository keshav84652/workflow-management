"""
Authentication service layer for business logic

SERVICE PATTERN:
- Instance methods for all business operations requiring repositories
- Session management delegated to dedicated SessionService
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from flask import session, request
from src.shared.database.db_import import db
from src.models.auth import Firm, User
from .models import DemoAccessRequest
from .firm_repository import FirmRepository
from .repository import UserRepository


class AuthService:
    """Service class for authentication-related business operations"""

    def __init__(self):
        self.firm_repository = FirmRepository()
        self.user_repository = UserRepository()
    

    def authenticate_firm(self, access_code: str, email: str) -> Dict[str, Any]:
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
            firm = self.firm_repository.get_by_access_code(access_code, active_only=True)
            
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
    

    def create_session(self, firm_data: Dict[str, Any], email: str) -> None:
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
    

    # Session management methods moved to SessionService for better separation of concerns
    # Use SessionService.is_authenticated(), SessionService.logout(), etc.