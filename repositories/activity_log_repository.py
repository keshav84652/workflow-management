"""
ActivityLog Repository for CPA WorkflowPilot
Provides data access layer for activity log-related operations.
"""

from typing import List, Optional
from datetime import datetime
from core.db_import import db
from models import ActivityLog
from .base import CachedRepository


class ActivityLogRepository(CachedRepository[ActivityLog]):
    """Repository for ActivityLog entity with caching support"""

    def __init__(self):
        super().__init__(ActivityLog, cache_ttl=300)  # 5 minute cache

    def get_by_firm(self, firm_id: int) -> List[ActivityLog]:
        """Get all activity logs for a firm"""
        return ActivityLog.query.filter(ActivityLog.firm_id == firm_id).order_by(ActivityLog.timestamp.desc()).all()

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
        db.session.commit()
        self._invalidate_cache(log.id)
        return log