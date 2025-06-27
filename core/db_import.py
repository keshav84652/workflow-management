"""
Centralized database import module for CPA WorkflowPilot

This module provides a clean way to import the database instance
without running into circular import issues.

USAGE:
    from core.db_import import db
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

__all__ = ['db']