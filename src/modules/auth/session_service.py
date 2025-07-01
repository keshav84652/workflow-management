"""
Session management service for authentication state

This service handles session-related operations independently from the main
AuthService to maintain clean separation of concerns.
"""

from typing import Optional, Dict, Any
from flask import session, request, redirect, url_for


class SessionService:
    """Static service for session management operations"""
    
    @staticmethod
    def is_authenticated() -> bool:
        """Check if user is fully authenticated (both firm and user selected)"""
        return (
            'firm_id' in session and 
            'firm_name' in session and 
            'user_id' in session and
            session.get('firm_id') is not None and
            session.get('user_id') is not None
        )
    
    @staticmethod
    def is_firm_authenticated() -> bool:
        """Check if firm is authenticated (but user may not be selected yet)"""
        return (
            'firm_id' in session and 
            'firm_name' in session and 
            session.get('firm_id') is not None
        )
    
    @staticmethod
    def logout() -> None:
        """Clear all session data"""
        session.clear()
    
    @staticmethod
    def get_current_user_info() -> Dict[str, Any]:
        """Get current user information from session"""
        return {
            'firm_id': session.get('firm_id'),
            'firm_name': session.get('firm_name'),
            'user_id': session.get('user_id'),
            'user_name': session.get('user_name'),
            'user_email': session.get('user_email'),
            'access_level': session.get('access_level', 'user'),
            'is_authenticated': SessionService.is_authenticated(),
            'is_firm_authenticated': SessionService.is_firm_authenticated()
        }
    
    @staticmethod
    def require_authentication() -> Optional[str]:
        """Require authentication for protected routes"""
        if not SessionService.is_firm_authenticated():
            # Return redirect URL for unauthenticated users
            return url_for('main.login')
        return None
    
    @staticmethod
    def create_session(firm_data: Dict[str, Any], email: str) -> None:
        """Create a new authenticated session"""
        session['firm_id'] = firm_data['id']
        session['firm_name'] = firm_data['name']
        session['user_email'] = email
        session['access_level'] = 'firm_admin'
        session['login_time'] = firm_data.get('login_time')
        session['firm_status'] = firm_data.get('status', 'active')
        session.permanent = True
    
    @staticmethod
    def set_user_in_session(user_id: int, firm_id: int, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Set user context in existing firm session"""
        if not SessionService.is_firm_authenticated():
            return {
                'success': False,
                'message': 'No authenticated firm session found'
            }
        
        if session.get('firm_id') != firm_id:
            return {
                'success': False,
                'message': 'User does not belong to authenticated firm'
            }
        
        # Update session with user context
        session['user_id'] = user_id
        session['user_name'] = user_data.get('name', 'Unknown User')
        session['user_email'] = user_data.get('email', session.get('user_email'))
        session['access_level'] = user_data.get('access_level', 'user')
        
        return {
            'success': True,
            'message': 'User context set successfully',
            'user': {
                'id': user_id,
                'name': user_data.get('name'),
                'email': user_data.get('email'),
                'access_level': user_data.get('access_level', 'user')
            }
        }