"""
Cached Repository Base Class
Extends BaseRepository with Redis caching capabilities for improved remote performance
"""

from .base_repository import BaseRepository
from app.services.redis_cache_service import redis_cache, cache_result
from app.logging_config import get_logger
import hashlib
import json

logger = get_logger(__name__)

class CachedRepository(BaseRepository):
    """Base repository with Redis caching for frequently accessed data"""
    
    def __init__(self, get_db_connection=None, cache_prefix=None):
        super().__init__(get_db_connection)
        self.cache_prefix = cache_prefix or f"{self.__class__.__name__.lower()}:"
        
    def _generate_cache_key(self, query, params=None):
        """Generate a consistent cache key for a query"""
        # Create a hash of query + params for consistent cache keys
        key_data = f"{query}:{params or ()}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()[:12]
        return f"query:{key_hash}"
    
    def _cached_execute_query(self, query, params=None, fetch_one=False, fetch_all=False, 
                            commit=False, ttl=300, use_cache=True):
        """
        Execute query with caching for read operations
        
        Args:
            query: SQL query string
            params: Query parameters
            fetch_one/fetch_all: Fetch options
            commit: Whether to commit (no caching for write operations)
            ttl: Cache time-to-live in seconds
            use_cache: Whether to use cache for this query
        """
        # Don't cache write operations
        if commit or not use_cache:
            return self._execute_query(query, params, fetch_one, fetch_all, commit)
        
        # Only cache SELECT queries
        if not query.strip().upper().startswith('SELECT'):
            return self._execute_query(query, params, fetch_one, fetch_all, commit)
        
        # Generate cache key
        cache_key = self._generate_cache_key(query, params)
        
        # Try cache first
        cached_result = redis_cache.get(cache_key, self.cache_prefix)
        if cached_result is not None:
            logger.debug(f"Cache hit for query: {query[:50]}...")
            return cached_result
        
        # Execute query and cache result
        result = self._execute_query(query, params, fetch_one, fetch_all, commit)
        
        # Cache the result
        if result is not None:
            redis_cache.set(cache_key, result, ttl, self.cache_prefix)
            logger.debug(f"Cached query result: {query[:50]}...")
        
        return result
    
    def invalidate_cache_pattern(self, pattern):
        """Invalidate cached queries matching a pattern"""
        full_pattern = f"{self.cache_prefix}{pattern}"
        count = redis_cache.invalidate_pattern(full_pattern)
        if count > 0:
            logger.info(f"Invalidated {count} cached queries matching: {pattern}")
        return count
    
    def invalidate_all_cache(self):
        """Invalidate all cached queries for this repository"""
        pattern = f"{self.cache_prefix}*"
        count = redis_cache.invalidate_pattern(pattern)
        if count > 0:
            logger.info(f"Invalidated all {count} cached queries for {self.__class__.__name__}")
        return count


class CachedSessionRepository(CachedRepository):
    """Session repository with caching for frequently accessed session data"""
    
    def __init__(self, get_db_connection=None):
        super().__init__(get_db_connection, "session:")
    
    @cache_result("session_details:{0}", ttl=600)  # Cache for 10 minutes
    def get_session_details_cached(self, session_id):
        """Get session details with caching"""
        query = """
            SELECT s.*, p.path as project_path, p.project_name, pt.participant_code
            FROM sessions s
            JOIN projects p ON s.project_id = p.project_id
            JOIN participants pt ON p.participant_id = pt.participant_id
            WHERE s.session_id = %s
        """
        return self._cached_execute_query(query, (session_id,), fetch_one=True, ttl=600)
    
    @cache_result("sessions_by_project:{0}", ttl=300)  # Cache for 5 minutes
    def get_sessions_by_project_cached(self, project_id):
        """Get sessions for a project with caching"""
        query = """
            SELECT s.*, p.project_name, pt.participant_code
            FROM sessions s
            JOIN projects p ON s.project_id = p.project_id
            JOIN participants pt ON p.participant_id = pt.participant_id
            WHERE s.project_id = %s
            ORDER BY s.session_name
        """
        return self._cached_execute_query(query, (project_id,), fetch_all=True, ttl=300)
    
    def update_session_invalidate_cache(self, session_id, **kwargs):
        """Update session and invalidate related caches"""
        # First update the session
        # ... (update logic here)
        
        # Then invalidate caches
        self.invalidate_cache_pattern(f"session_details:{session_id}")
        self.invalidate_cache_pattern("sessions_by_project:*")
        logger.info(f"Invalidated caches for session {session_id}")


class CachedProjectRepository(CachedRepository):
    """Project repository with caching for project and participant data"""
    
    def __init__(self, get_db_connection=None):
        super().__init__(get_db_connection, "project:")
    
    @cache_result("all_projects", ttl=300)  # Cache for 5 minutes
    def get_all_projects_cached(self):
        """Get all projects with caching"""
        query = """
            SELECT p.*, pt.participant_code, pt.first_name, pt.last_name
            FROM projects p
            JOIN participants pt ON p.participant_id = pt.participant_id
            ORDER BY p.created_at DESC
        """
        return self._cached_execute_query(query, fetch_all=True, ttl=300)
    
    @cache_result("participants_with_stats", ttl=600)  # Cache for 10 minutes
    def get_participants_with_stats_cached(self):
        """Get participants with project stats, cached"""
        query = """
            SELECT 
                pt.*,
                COUNT(p.project_id) as project_count,
                GROUP_CONCAT(p.project_id) as project_ids,
                GROUP_CONCAT(p.project_name) as project_names
            FROM participants pt
            LEFT JOIN projects p ON pt.participant_id = p.participant_id
            GROUP BY pt.participant_id
            ORDER BY pt.participant_code
        """
        return self._cached_execute_query(query, fetch_all=True, ttl=600)
    
    def create_project_invalidate_cache(self, **kwargs):
        """Create project and invalidate related caches"""
        # ... (creation logic)
        
        # Invalidate caches
        self.invalidate_cache_pattern("all_projects")
        self.invalidate_cache_pattern("participants_with_stats")
        logger.info("Invalidated project-related caches")


class CachedModelRepository(CachedRepository):
    """Model repository with caching for model metadata"""
    
    def __init__(self, get_db_connection=None):
        super().__init__(get_db_connection, "model:")
    
    @cache_result("all_models", ttl=900)  # Cache for 15 minutes (models don't change often)
    def get_all_models_cached(self):
        """Get all models with caching"""
        query = """
            SELECT * FROM models
            WHERE is_active = 1
            ORDER BY created_at DESC
        """
        return self._cached_execute_query(query, fetch_all=True, ttl=900)
    
    @cache_result("model_details:{0}", ttl=900)  # Cache for 15 minutes
    def get_model_by_id_cached(self, model_id):
        """Get model by ID with caching"""
        query = "SELECT * FROM models WHERE id = %s AND is_active = 1"
        return self._cached_execute_query(query, (model_id,), fetch_one=True, ttl=900)