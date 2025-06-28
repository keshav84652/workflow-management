"""
ActivityLog Repository for CPA WorkflowPilot
Provides data access layer for activity log-related operations.
"""

from typing import List, Optional
from datetime import datetime
from core.db_import import db
from models import ActivityLog
from .base import CachedRepository, PaginationResult


class ActivityLogRepository(CachedRepository[ActivityLog]):
    """Repository for ActivityLog entity with caching support"""

    def __init__(self):
        super().__init__(ActivityLog, cache_ttl=300)  # 5 minute cache

    def get_by_firm(self, firm_id: int, limit: Optional[int] = 100) -> List[ActivityLog]:
        """Get activity logs for a firm with default limit (WARNING: Use paginated version for large datasets)"""
        query = ActivityLog.query.filter(ActivityLog.firm_id == firm_id).order_by(ActivityLog.timestamp.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def get_by_firm_paginated(self, firm_id: int, page: int = 1, per_page: int = 50) -> PaginationResult:
        """Get activity logs for a firm with pagination"""
        query = ActivityLog.query.filter(ActivityLog.firm_id == firm_id).order_by(ActivityLog.timestamp.desc())
        
        total = query.count()
        pages = (total + per_page - 1) // per_page
        
        offset = (page - 1) * per_page
        items = query.offset(offset).limit(per_page).all()
        
        return PaginationResult(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
            has_prev=page > 1,
            has_next=page < pages
        )

    def get_recent_activities(self, firm_id: int, limit: int = 20) -> List[ActivityLog]:
        """Get recent activity logs for a firm"""
        return ActivityLog.query.filter(ActivityLog.firm_id == firm_id).order_by(ActivityLog.timestamp.desc()).limit(limit).all()

    def create(self, firm_id: int, user_id: int, action: str, details: str = "") -> ActivityLog:
        """Create a new activity log entry"""
        log = ActivityLog(
            firm_id=firm_id,
            user_id=user_id,
            action=action,
            details=details,
            timestamp=datetime.utcnow()
        )
        db.session.add(log)
        # Note: Transaction commit is handled by service layer
        return log
