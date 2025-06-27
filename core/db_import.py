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

from core import db, migrate, create_directories

__all__ = ['db', 'migrate', 'create_directories']