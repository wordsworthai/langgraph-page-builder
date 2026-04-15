# core/redis_cache.py
"""
Redis cache client for LangGraph caching.
Adapted from existing redis_client.py with LangGraph integration.
"""

import redis
from typing import Optional, Dict, Any
import json
import hashlib
from datetime import datetime
from decimal import Decimal
import logging
import os

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis cache client for LangGraph workflow caching"""
    
    def __init__(self):
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6380"))
        redis_db = int(os.getenv("REDIS_DB", "0"))
        redis_password = os.getenv("REDIS_PASSWORD", "") or None
        
        logger.info(
            f"Connecting to Redis: {redis_host}:{redis_port}/{redis_db} "
            f"(has_password={redis_password is not None})"
        )
        
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            # Connection pool settings to prevent blocking
            max_connections=50,
            socket_keepalive=True,
            socket_keepalive_options={}
        )
        
        # Test connection
        try:
            self.redis_client.ping()
            logger.info("✅ Redis connection established successfully")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            raise
    
    def generate_cache_key(self, prefix: str, **params) -> str:
        """
        Generate deterministic cache key from parameters.
        
        Args:
            prefix: Key prefix (e.g., "smb_workflow:business_data_extractor")
            **params: Parameters to hash
            
        Returns:
            Cache key string
        """
        # Sort params for consistent hashing
        sorted_params = dict(sorted(params.items()))
        param_string = json.dumps(sorted_params, sort_keys=True, default=str)
        hash_key = hashlib.md5(param_string.encode()).hexdigest()
        return f"{prefix}:{hash_key}"
    
    def _serialize_for_cache(self, value: Dict[str, Any]) -> str:
        """Serialize data with custom datetime handling"""
        return json.dumps(value, default=self._json_serializer, sort_keys=True)
    
    def _json_serializer(self, obj):
        """Custom JSON serializer for non-serializable objects"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)
    
    def _deserialize_from_cache(self, cached_str: str) -> Dict[str, Any]:
        """Deserialize data and convert datetime strings back"""
        data = json.loads(cached_str)
        return self._restore_datetimes(data)
    
    def _restore_datetimes(self, data):
        """Recursively restore datetime objects from ISO strings"""
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str) and self._is_datetime_string(value):
                    try:
                        data[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    except:
                        pass
                elif isinstance(value, (dict, list)):
                    data[key] = self._restore_datetimes(value)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                data[i] = self._restore_datetimes(item)
        return data
    
    def _is_datetime_string(self, value: str) -> bool:
        """Check if string looks like an ISO datetime"""
        if len(value) < 19:
            return False
        return 'T' in value and ':' in value and value.count('-') >= 2
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached result.
        
        Args:
            key: Cache key
            
        Returns:
            Cached dict or None if not found
        """
        try:
            cached = self.redis_client.get(key)
            if cached:
                logger.debug(f"✅ Redis Cache HIT: {key}")
                return self._deserialize_from_cache(cached)
            logger.debug(f"❌ Redis Cache MISS: {key}")
            return None
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None
    
    def set(self, key: str, value: Dict[str, Any], ttl: int = 5184000) -> bool:
        """
        Cache result with TTL.
        
        Args:
            key: Cache key
            value: Data to cache
            ttl: Time to live in seconds (default: 60 days)
            
        Returns:
            True if successful
        """
        try:
            serialized_data = self._serialize_for_cache(value)
            result = self.redis_client.setex(key, ttl, serialized_data)
            logger.debug(f"✅ Redis Cache SET: {key} (TTL: {ttl}s)")
            return result
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete cached entry.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted
        """
        try:
            result = self.redis_client.delete(key)
            logger.debug(f"✅ Redis Cache DELETE: {key}")
            return result > 0
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching pattern.
        
        Args:
            pattern: Key pattern (e.g., "smb_workflow:*")
            
        Returns:
            Number of keys deleted
        """
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"✅ Cleared {deleted} Redis keys matching pattern: {pattern}")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Redis CLEAR error for pattern {pattern}: {e}")
            return 0


# Global instance
redis_cache = RedisCache()