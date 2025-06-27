"""
Template Repository for CPA WorkflowPilot
Provides data access layer for template-related operations.
"""

from typing import List, Optional
from core.db_import import db
from models import Template
from .base import CachedRepository


class TemplateRepository(CachedRepository[Template]):
    """Repository for Template entity with caching support"""

    def __init__(self):
        super().__init__(Template, cache_ttl=300)  # 5 minute cache

    def get_by_firm(self, firm_id: int) -> List[Template]:
        """Get all templates for a firm"""
        return Template.query.filter(Template.firm_id == firm_id).order_by(Template.created_at.desc()).all()

    def get_active_templates(self, firm_id: int) -> List[Template]:
        """Get all active templates for a firm"""
        return Template.query.filter(
            Template.firm_id == firm_id,
            Template.is_active.is_(True)
        ).order_by(Template.created_at.desc()).all()

    def create(self, **kwargs) -> Template:
        """Create a new template"""
        template = Template(**kwargs)
        db.session.add(template)
        # Note: Transaction commit is handled by service layer
        return template

    def update(self, template_id: int, **kwargs) -> Optional[Template]:
        """Update an existing template"""
        template = Template.query.get(template_id)
        if not template:
            return None
        for key, value in kwargs.items():
            if hasattr(template, key):
                setattr(template, key, value)
        # Note: Transaction commit is handled by service layer
        return template
