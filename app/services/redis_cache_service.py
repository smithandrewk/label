"""
Redis Cache Service
Provides caching for database queries to improve remote performance
"""

import redis
import json
import os
import hashlib
import pickle
from typing import Any, Optional, Union
from functools import wraps
import time
from app.logging_config import get_logger

logger = get_logger(__name__)

class RedisCacheService:
    """Redis-based caching service for database queries and API responses"""
    
    def __init__(self):
        self.redis_client = None
        self.enabled = False
        self.default_ttl = 300  # 5 minutes default TTL
        self.key_prefix = "label_app:"
        
        # Performance tracking
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'errors': 0
        }
        
        self._initialize_redis()
    
    def _initialize_redis(self):
        """Initialize Redis connection"""
        try:
            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(os.getenv('REDIS_PORT', 6379))
            redis_db = int(os.getenv('REDIS_DB', 0))
            redis_password = os.getenv('REDIS_PASSWORD', None)
            
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=False,  # We'll handle encoding ourselves
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            self.redis_client.ping()
            self.enabled = True
            
            logger.info(f"✅ Redis cache service initialized (host: {redis_host}:{redis_port})")
            
        except redis.ConnectionError as e:
            logger.warning(f"⚠️ Redis connection failed: {e}. Caching disabled.")
            self.enabled = False
        except Exception as e:
            logger.warning(f"⚠️ Redis initialization error: {e}. Caching disabled.")
            self.enabled = False
    
    def _generate_key(self, key: str, prefix: str = None) -> str:
        """Generate a properly prefixed cache key"""
        full_prefix = prefix or self.key_prefix
        return f"{full_prefix}{key}"
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize a value for storage"""
        try:
            # Use pickle for complex objects, JSON for simple ones
            if isinstance(value, (dict, list, str, int, float, bool)) or value is None:
                return json.dumps(value).encode('utf-8')
            else:
                return pickle.dumps(value)
        except Exception as e:
            logger.error(f"Serialization error: {e}")
            raise
    
    def _deserialize_value(self, value: bytes) -> Any:
        """Deserialize a value from storage"""
        try:
            # Try JSON first (for simple types)
            try:
                return json.loads(value.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Fall back to pickle for complex objects
                return pickle.loads(value)
        except Exception as e:
            logger.error(f"Deserialization error: {e}")
            raise
    
    def get(self, key: str, prefix: str = None) -> Optional[Any]:
        """Get a value from cache"""
        if not self.enabled:
            return None
        
        try:
            cache_key = self._generate_key(key, prefix)
            value = self.redis_client.get(cache_key)
            
            if value is None:
                self.stats['misses'] += 1
                return None
            
            self.stats['hits'] += 1
            result = self._deserialize_value(value)
            
            logger.debug(f"Cache hit for key: {key}")
            return result
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = None, prefix: str = None) -> bool:
        """Set a value in cache"""
        if not self.enabled:
            return False
        
        try:
            cache_key = self._generate_key(key, prefix)
            serialized_value = self._serialize_value(value)
            ttl = ttl or self.default_ttl
            
            success = self.redis_client.setex(cache_key, ttl, serialized_value)
            
            if success:
                self.stats['sets'] += 1
                logger.debug(f"Cache set for key: {key} (TTL: {ttl}s)")
            
            return success
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    def delete(self, key: str, prefix: str = None) -> bool:
        """Delete a value from cache"""
        if not self.enabled:
            return False
        
        try:
            cache_key = self._generate_key(key, prefix)
            result = self.redis_client.delete(cache_key)
            
            if result:
                logger.debug(f"Cache delete for key: {key}")
            
            return bool(result)
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    def exists(self, key: str, prefix: str = None) -> bool:
        """Check if a key exists in cache"""
        if not self.enabled:
            return False
        
        try:
            cache_key = self._generate_key(key, prefix)
            return bool(self.redis_client.exists(cache_key))
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    def invalidate_pattern(self, pattern: str, prefix: str = None) -> int:
        """Invalidate all keys matching a pattern"""
        if not self.enabled:
            return 0
        
        try:
            full_pattern = self._generate_key(pattern, prefix)
            keys = self.redis_client.keys(full_pattern)
            
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.debug(f"Invalidated {deleted} keys matching pattern: {pattern}")
                return deleted
            
            return 0
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Cache pattern invalidation error for {pattern}: {e}")
            return 0
    
    def clear_all(self) -> bool:
        """Clear all cache entries (use with caution!)"""
        if not self.enabled:
            return False
        
        try:
            # Only clear keys with our prefix
            keys = self.redis_client.keys(f"{self.key_prefix}*")
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"Cleared {deleted} cache entries")
                return True
            return True
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Cache clear error: {e}")
            return False
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        stats = {
            **self.stats,
            'hit_rate': f"{hit_rate:.1f}%",
            'enabled': self.enabled,
            'total_requests': total_requests
        }
        
        if self.enabled:
            try:
                info = self.redis_client.info('memory')
                stats['redis_memory'] = f"{info.get('used_memory_human', 'N/A')}"
                stats['redis_keys'] = self.redis_client.dbsize()
            except Exception as e:
                logger.error(f"Error getting Redis info: {e}")
        
        return stats
    
    def health_check(self) -> dict:
        """Check Redis health"""
        if not self.enabled:
            return {'status': 'disabled', 'message': 'Redis caching is disabled'}
        
        try:
            start_time = time.time()
            self.redis_client.ping()
            response_time = (time.time() - start_time) * 1000  # ms
            
            return {
                'status': 'healthy',
                'response_time_ms': f"{response_time:.2f}",
                'memory_usage': self.redis_client.info('memory').get('used_memory_human', 'N/A')
            }
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}


def cache_result(key_template: str, ttl: int = 300, prefix: str = None):
    """
    Decorator to cache function results
    
    Args:
        key_template: Template for cache key (can use function args)
        ttl: Time to live in seconds
        prefix: Optional key prefix
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from template and arguments
            try:
                if hasattr(args[0], '__dict__'):  # Skip 'self' for methods
                    format_args = args[1:]
                else:
                    format_args = args
                
                cache_key = key_template.format(*format_args, **kwargs)
            except (IndexError, KeyError):
                # Fallback to function name + hash of args
                args_hash = hashlib.md5(str(args + tuple(kwargs.items())).encode()).hexdigest()[:8]
                cache_key = f"{func.__name__}:{args_hash}"
            
            # Try to get from cache first
            cached_result = redis_cache.get(cache_key, prefix)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            redis_cache.set(cache_key, result, ttl, prefix)
            
            return result
        return wrapper
    return decorator


# Global instance
redis_cache = RedisCacheService()