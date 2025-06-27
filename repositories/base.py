"""
Base Repository Interface for CPA WorkflowPilot
Provides abstraction layer for data access operations.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Generic, TypeVar
from datetime import datetime
import importlib.util
import os

from core.db_import import db

T = TypeVar('T')


class BaseRepository(ABC, Generic[T]):
    """
    Base repository interface for common CRUD operations
    """
    
    def __init__(self, model_class: type):
        self.model_class = model_class
    
    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[T]:
        """Get entity by ID"""
        pass
    
    @abstractmethod
    def get_all(self, firm_id: Optional[int] = None, **filters) -> List[T]:
        """Get all entities with optional filters"""
        pass
    
    @abstractmethod
    def create(self, data: Dict[str, Any]) -> T:
        """Create new entity"""
        pass
    
    @abstractmethod
    def update(self, entity_id: int, data: Dict[str, Any]) -> Optional[T]:
        """Update existing entity"""
        pass
    
    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """Delete entity by ID"""
        pass
    
    @abstractmethod
    def exists(self, entity_id: int) -> bool:
        """Check if entity exists"""
        pass
    
    @abstractmethod
    def count(self, firm_id: Optional[int] = None, **filters) -> int:
        """Count entities with optional filters"""
        pass


class SqlAlchemyRepository(BaseRepository[T]):
    """
    SQLAlchemy-based repository implementation
    """
    
    def __init__(self, model_class: type):
        super().__init__(model_class)
    
    def get_by_id(self, entity_id: int) -> Optional[T]:
        """Get entity by ID"""
        return self.model_class.query.get(entity_id)
    
    def get_all(self, firm_id: Optional[int] = None, **filters) -> List[T]:
        """Get all entities with optional filters"""
        query = self.model_class.query
        
        # Apply firm filter if applicable and provided
        if firm_id is not None and hasattr(self.model_class, 'firm_id'):
            query = query.filter(self.model_class.firm_id == firm_id)
        
        # Apply additional filters
        for field, value in filters.items():
            if hasattr(self.model_class, field):
                query = query.filter(getattr(self.model_class, field) == value)
        
        return query.all()
    
    def create(self, data: Dict[str, Any]) -> T:
        """Create new entity"""
        # Filter data to only include valid model fields
        valid_data = self._filter_valid_fields(data)
        
        entity = self.model_class(**valid_data)
        db.session.add(entity)
        db.session.commit()
        return entity
    
    def update(self, entity_id: int, data: Dict[str, Any]) -> Optional[T]:
        """Update existing entity"""
        entity = self.get_by_id(entity_id)
        if not entity:
            return None
        
        # Filter data to only include valid model fields
        valid_data = self._filter_valid_fields(data)
        
        for field, value in valid_data.items():
            if hasattr(entity, field):
                setattr(entity, field, value)
        
        db.session.commit()
        return entity
    
    def delete(self, entity_id: int) -> bool:
        """Delete entity by ID"""
        entity = self.get_by_id(entity_id)
        if not entity:
            return False
        
        db.session.delete(entity)
        db.session.commit()
        return True
    
    def exists(self, entity_id: int) -> bool:
        """Check if entity exists"""
        return self.model_class.query.filter(self.model_class.id == entity_id).first() is not None
    
    def count(self, firm_id: Optional[int] = None, **filters) -> int:
        """Count entities with optional filters"""
        query = self.model_class.query
        
        # Apply firm filter if applicable and provided
        if firm_id is not None and hasattr(self.model_class, 'firm_id'):
            query = query.filter(self.model_class.firm_id == firm_id)
        
        # Apply additional filters
        for field, value in filters.items():
            if hasattr(self.model_class, field):
                query = query.filter(getattr(self.model_class, field) == value)
        
        return query.count()
    
    def _filter_valid_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Filter data to only include valid model fields"""
        if not data:
            return {}
        
        valid_fields = {}
        for field, value in data.items():
            if hasattr(self.model_class, field):
                # Skip special fields that shouldn't be mass-assigned
                if field not in ['id', 'created_at', 'updated_at']:
                    valid_fields[field] = value
        
        return valid_fields


class CachedRepository(SqlAlchemyRepository[T]):
    """
    Repository with Redis caching support
    """
    
    def __init__(self, model_class: type, cache_ttl: int = 300):
        super().__init__(model_class)
        self.cache_ttl = cache_ttl
        self.cache_prefix = f"repo:{model_class.__name__.lower()}"
    
    def get_by_id(self, entity_id: int) -> Optional[T]:
        """Get entity by ID with caching"""
        from core.redis_client import redis_client
        
        # Try cache first
        if redis_client and redis_client.is_available():
            cache_key = f"{self.cache_prefix}:id:{entity_id}"
            cached_data = redis_client.get_json(cache_key)
            if cached_data:
                return self._deserialize_entity(cached_data)
        
        # Fallback to database
        entity = super().get_by_id(entity_id)
        
        # Cache the result
        if entity and redis_client and redis_client.is_available():
            cache_key = f"{self.cache_prefix}:id:{entity_id}"
            redis_client.set_json(cache_key, self._serialize_entity(entity), ex=self.cache_ttl)
        
        return entity
    
    def create(self, data: Dict[str, Any]) -> T:
        """Create new entity and invalidate cache"""
        entity = super().create(data)
        self._invalidate_cache(entity.id if hasattr(entity, 'id') else None)
        return entity
    
    def update(self, entity_id: int, data: Dict[str, Any]) -> Optional[T]:
        """Update existing entity and invalidate cache"""
        entity = super().update(entity_id, data)
        self._invalidate_cache(entity_id)
        return entity
    
    def delete(self, entity_id: int) -> bool:
        """Delete entity and invalidate cache"""
        result = super().delete(entity_id)
        if result:
            self._invalidate_cache(entity_id)
        return result
    
    def _serialize_entity(self, entity: T) -> Dict[str, Any]:
        """Serialize entity for caching"""
        if hasattr(entity, 'to_dict'):
            return entity.to_dict()
        
        # Basic serialization for SQLAlchemy models
        data = {}
        for column in entity.__table__.columns:
            value = getattr(entity, column.name)
            if isinstance(value, datetime):
                data[column.name] = value.isoformat()
            else:
                data[column.name] = value
        return data
    
    def _deserialize_entity(self, data: Dict[str, Any]) -> T:
        """Deserialize entity from cache"""
        # This is a simplified approach - in production, you'd want more robust deserialization
        # For now, we'll just return None to fall back to database
        return None
    
    def _invalidate_cache(self, entity_id: Optional[int] = None):
        """Invalidate cache entries"""
        from core.redis_client import redis_client
        
        if not redis_client or not redis_client.is_available():
            return
        
        # Invalidate specific entity cache
        if entity_id:
            cache_key = f"{self.cache_prefix}:id:{entity_id}"
            redis_client.delete(cache_key)
        
        # Invalidate list caches (simple approach - delete all list caches for this model)
        pattern = f"{self.cache_prefix}:list:*"
        client = redis_client.get_client()
        if client:
            for key in client.scan_iter(match=pattern):
                client.delete(key)
