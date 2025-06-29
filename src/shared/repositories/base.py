"""
Base Repository Classes for CPA WorkflowPilot
"""

from typing import List, Dict, Any, Optional, Generic, TypeVar, Type
from sqlalchemy import func
from src.shared.database.db_import import db

T = TypeVar('T')


class PaginationResult:
    """Result container for paginated queries"""
    
    def __init__(self, items: List[Any], total: int, page: int, per_page: int):
        self.items = items
        self.total = total
        self.page = page
        self.per_page = per_page
        self.pages = (total - 1) // per_page + 1 if total > 0 else 0
        self.has_prev = page > 1
        self.has_next = page < self.pages


class BaseRepository(Generic[T]):
    """Base repository with common CRUD operations"""
    
    def __init__(self, model: Type[T]):
        self.model = model
    
    def get_by_id(self, id: int) -> Optional[T]:
        """Get entity by ID"""
        return self.model.query.get(id)
    
    def get_all(self) -> List[T]:
        """Get all entities"""
        return self.model.query.all()
    
    def create(self, **kwargs) -> T:
        """Create new entity"""
        entity = self.model(**kwargs)
        db.session.add(entity)
        return entity
    
    def update(self, entity: T, **kwargs) -> T:
        """Update entity"""
        for key, value in kwargs.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        return entity
    
    def delete(self, entity: T) -> bool:
        """Delete entity"""
        db.session.delete(entity)
        return True
    
    def count(self, **filters) -> int:
        """Count entities with optional filters"""
        query = self.model.query
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)
        return query.count()


class CachedRepository(BaseRepository[T]):
    """Repository with simple caching capabilities"""
    
    def __init__(self, model: Type[T], cache_ttl: int = 300):
        super().__init__(model)
        self.cache_ttl = cache_ttl
        self._cache = {}
        self._cache_timestamps = {}
    
    def _get_cache_key(self, key: str) -> str:
        """Generate cache key"""
        return f"{self.model.__name__}:{key}"
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache entry is still valid"""
        import time
        cache_key = self._get_cache_key(key)
        if cache_key not in self._cache_timestamps:
            return False
        return time.time() - self._cache_timestamps[cache_key] < self.cache_ttl
    
    def _cache_set(self, key: str, value: Any):
        """Set cache value"""
        import time
        cache_key = self._get_cache_key(key)
        self._cache[cache_key] = value
        self._cache_timestamps[cache_key] = time.time()
    
    def _cache_get(self, key: str) -> Any:
        """Get cache value"""
        cache_key = self._get_cache_key(key)
        if self._is_cache_valid(key):
            return self._cache.get(cache_key)
        return None
    
    def get_by_id(self, id: int) -> Optional[T]:
        """Get entity by ID with caching"""
        cache_key = f"id:{id}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        
        entity = super().get_by_id(id)
        if entity:
            self._cache_set(cache_key, entity)
        return entity