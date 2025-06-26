"""
Centralized database import module for CPA WorkflowPilot

This module provides a clean way to import the database instance
without the verbose importlib pattern repeated across 37+ files.

USAGE:
    from core.db_import import db
    
Instead of:
    import importlib.util
    import os
    spec = importlib.util.spec_from_file_location("core", ...)
    core_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core_module)
    db = core_module.db
"""

import importlib.util
import os

# Single point of truth for core.py database import
_spec = importlib.util.spec_from_file_location(
    "core", 
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "core.py")
)
_core_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_core_module)

# Export the database instance
db = _core_module.db

# Also export other commonly used core utilities if needed
migrate = getattr(_core_module, 'migrate', None)
create_directories = getattr(_core_module, 'create_directories', None)

__all__ = ['db', 'migrate', 'create_directories']