"""
Centralized database import module for CPA WorkflowPilot

This module provides a clean way to import the database instance
without running into circular import issues.

USAGE:
    from src.shared.database.db_import import db
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

__all__ = ['db']