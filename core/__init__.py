"""
Core infrastructure module for CPA WorkflowPilot
"""

from .redis_client import RedisClient, init_redis, redis_client

__all__ = ['RedisClient', 'init_redis', 'redis_client']