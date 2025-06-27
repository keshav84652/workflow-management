"""
DEPRECATED: Session helper functions moved to consolidated.py
This file is kept for backwards compatibility only.

MIGRATION: Import from utils.consolidated directly instead:
    from utils.consolidated import get_session_firm_id, get_session_user_id
"""

# Backwards compatibility imports
from .consolidated import get_session_firm_id, get_session_user_id

__all__ = ['get_session_firm_id', 'get_session_user_id']