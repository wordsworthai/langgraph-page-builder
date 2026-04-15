# core/langgraph_redis_cache.py
"""
LangGraph Redis Cache Backend.

Implements LangGraph's BaseCache interface using Redis for persistent caching.
Matches the exact interface expected by LangGraph.
"""

from __future__ import annotations

import time
import datetime
from collections.abc import Mapping, Sequence
from typing import TypeVar

from langgraph.cache.base import BaseCache, FullKey, Namespace
from langgraph.checkpoint.serde.base import SerializerProtocol
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from wwai_agent_orchestration.core.database.redis.redis_cache import redis_cache
from wwai_agent_orchestration.core.observability.logger import get_logger, get_request_context, is_perf_logging_enabled

logger = get_logger(__name__)

ValueT = TypeVar("ValueT")


class LangGraphRedisCache(BaseCache[ValueT]):
    """
    Redis-backed cache for LangGraph workflows.
    
    Implements LangGraph's BaseCache interface with Redis persistence.
    
    Key Structure:
        FullKey = (Namespace, str)
        Namespace = tuple[str, ...]
        
        Example: (("smb_workflow", "v1"), "business_data_abc123")
        
    Redis Storage:
        Key: "prefix:namespace_joined:key_hash"
        Value: JSON with {type, data, expiry}
        
    Usage:
        cache = LangGraphRedisCache(prefix="smb_workflow")
        graph = builder.compile(cache=cache)
    """
    
    def __init__(
        self,
        prefix: str = "langgraph_cache",
        default_ttl: int = 5184000,
        *,
        serde: SerializerProtocol | None = None
    ):
        """
        Initialize LangGraph Redis cache.
        
        Args:
            prefix: Cache key prefix (e.g., "smb_workflow")
            default_ttl: Default time-to-live in seconds (default: 60 days)
            serde: Serializer protocol (uses JsonPlusSerializer by default)
        """
        super().__init__(serde=serde)
        self.redis = redis_cache.redis_client
        self.prefix = prefix
        self.default_ttl = default_ttl
        
        logger.info(
            f"✅ LangGraphRedisCache initialized with prefix={prefix}, default_ttl={default_ttl}s"
        )
    
    def get(self, keys: Sequence[FullKey]) -> dict[FullKey, ValueT]:
        """
        Get cached values for multiple keys (batch operation).
        
        Args:
            keys: Sequence of (namespace, key) tuples
            
        Returns:
            Dict mapping FullKey to cached value (only non-expired entries)
        """
        if not keys:
            return {}
        
        try:
            start = time.perf_counter()
            start_time_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            now = datetime.datetime.now(datetime.timezone.utc).timestamp()
            values: dict[FullKey, ValueT] = {}

            # Use Redis pipeline for batch get
            pipe = self.redis.pipeline()
            for full_key in keys:
                redis_key = self._build_redis_key(full_key)
                pipe.get(redis_key)

            results = pipe.execute()
            duration_ms = (time.perf_counter() - start) * 1000
            end_time_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            if is_perf_logging_enabled():
                ctx = get_request_context()
                logger.info(
                    "Redis cache get",
                    metric_type="perf_redis",
                    operation="get",
                    start_time=start_time_iso,
                    end_time=end_time_iso,
                    duration_ms=round(duration_ms, 2),
                    keys_count=len(keys),
                    **{k: v for k, v in ctx.items() if k in ("request_id", "workflow_id")},
                )
            
            # Process results
            for full_key, cached_str in zip(keys, results):
                if cached_str:
                    try:
                        cached_data = self._deserialize_cache_entry(cached_str)
                        
                        # Check expiry
                        expiry = cached_data.get("expiry")
                        if expiry is None or now < expiry:
                            # Deserialize value using LangGraph's serde
                            type_str = cached_data["type"]
                            data_bytes = cached_data["data"].encode("latin1")  # Reverse the encoding
                            value = self.serde.loads_typed((type_str, data_bytes))
                            values[full_key] = value
                            logger.debug(f"✅ Cache HIT: {self._build_redis_key(full_key)}")
                        else:
                            # Expired - delete it
                            redis_key = self._build_redis_key(full_key)
                            self.redis.delete(redis_key)
                            logger.debug(f"⏰ Cache EXPIRED: {redis_key}")
                    except Exception as e:
                        logger.error(f"Error deserializing cache entry: {e}")
                        continue
            
            if not values:
                logger.debug(f"❌ Cache MISS: All {len(keys)} keys missed")
            
            return values
            
        except Exception as e:
            logger.error(f"Redis batch GET error: {e}")
            return {}
    
    async def aget(self, keys: Sequence[FullKey]) -> dict[FullKey, ValueT]:
        """Async version of get (uses sync implementation)."""
        return self.get(keys)
    
    def set(self, pairs: Mapping[FullKey, tuple[ValueT, int | None]]) -> None:
        """
        Set cached values for multiple keys with TTLs (batch operation).
        
        Args:
            pairs: Mapping of FullKey to (value, ttl_seconds)
        """
        if not pairs:
            return
        
        try:
            start = time.perf_counter()
            start_time_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            now = datetime.datetime.now(datetime.timezone.utc)

            # Use Redis pipeline for batch set
            pipe = self.redis.pipeline()

            for full_key, (value, ttl) in pairs.items():
                # Calculate expiry timestamp
                if ttl is not None:
                    delta = datetime.timedelta(seconds=ttl)
                    expiry: float | None = (now + delta).timestamp()
                else:
                    expiry = None
                    ttl = self.default_ttl  # Use default TTL for Redis SETEX
                
                # Serialize value using LangGraph's serde
                type_str, data_bytes = self.serde.dumps_typed(value)
                
                # Build cache entry
                cache_entry = {
                    "type": type_str,
                    "data": data_bytes.decode("latin1"),  # Store as string
                    "expiry": expiry
                }
                
                # Serialize cache entry to JSON
                cache_entry_str = self._serialize_cache_entry(cache_entry)
                
                # Store in Redis with TTL
                redis_key = self._build_redis_key(full_key)
                pipe.setex(redis_key, ttl or self.default_ttl, cache_entry_str)
            
            pipe.execute()
            duration_ms = (time.perf_counter() - start) * 1000
            end_time_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            if is_perf_logging_enabled():
                ctx = get_request_context()
                logger.info(
                    "Redis cache set",
                    metric_type="perf_redis",
                    operation="set",
                    start_time=start_time_iso,
                    end_time=end_time_iso,
                    duration_ms=round(duration_ms, 2),
                    pairs_count=len(pairs),
                    **{k: v for k, v in ctx.items() if k in ("request_id", "workflow_id")},
                )

            logger.debug(f"✅ Cache SET: {len(pairs)} entries")
            
        except Exception as e:
            logger.error(f"Redis batch SET error: {e}")
    
    async def aset(self, pairs: Mapping[FullKey, tuple[ValueT, int | None]]) -> None:
        """Async version of set (uses sync implementation)."""
        self.set(pairs)
    
    def clear(self, namespaces: Sequence[Namespace] | None = None) -> None:
        """
        Delete cached values for given namespaces.
        
        Args:
            namespaces: Namespaces to clear (None = clear all)
        """
        try:
            if namespaces is None:
                # Clear all keys with this prefix
                pattern = f"{self.prefix}:*"
                keys = self.redis.keys(pattern)
                if keys:
                    deleted = self.redis.delete(*keys)
                    logger.info(f"✅ Cleared ALL cache: {deleted} keys deleted")
                else:
                    logger.info("✅ Cache already empty")
            else:
                # Clear specific namespaces
                total_deleted = 0
                for namespace in namespaces:
                    namespace_str = ":".join(namespace)
                    pattern = f"{self.prefix}:{namespace_str}:*"
                    keys = self.redis.keys(pattern)
                    if keys:
                        deleted = self.redis.delete(*keys)
                        total_deleted += deleted
                        logger.info(f"✅ Cleared namespace {namespace}: {deleted} keys")
                
                logger.info(f"✅ Total cleared: {total_deleted} keys")
                
        except Exception as e:
            logger.error(f"Redis CLEAR error: {e}")
    
    async def aclear(self, namespaces: Sequence[Namespace] | None = None) -> None:
        """Async version of clear (uses sync implementation)."""
        self.clear(namespaces)
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _build_redis_key(self, full_key: FullKey) -> str:
        """
        Build Redis key from FullKey.
        
        Args:
            full_key: (namespace_tuple, key) tuple
            
        Returns:
            Redis key: "prefix:namespace:key"
            
        Example:
            (("smb_workflow", "v1"), "abc123") 
            → "langgraph_cache:smb_workflow:v1:abc123"
        """
        namespace, key = full_key
        namespace_str = ":".join(namespace)
        return f"{self.prefix}:{namespace_str}:{key}"
    
    def _serialize_cache_entry(self, cache_entry: dict) -> str:
        """
        Serialize cache entry to JSON string.
        
        Args:
            cache_entry: Dict with {type, data, expiry}
            
        Returns:
            JSON string
        """
        import json
        return json.dumps(cache_entry, default=str)
    
    def _deserialize_cache_entry(self, cached_str: str) -> dict:
        """
        Deserialize cache entry from JSON string.
        
        Args:
            cached_str: JSON string from Redis
            
        Returns:
            Dict with {type, data, expiry}
        """
        import json
        return json.loads(cached_str)


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

# Create global instance for SMB workflow
smb_workflow_cache = LangGraphRedisCache(
    prefix="smb_workflow",
    default_ttl=5184000  # 60 days
)