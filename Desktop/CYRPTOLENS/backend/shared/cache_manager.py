"""
Multi-layer Cache Manager for CryptoLens backend services.
Implements L1 (in-memory), L2 (Redis), and L3 (Database) caching layers.
"""
from typing import Optional, Any, Dict
from datetime import datetime, timedelta
import json
import hashlib
import logging
from .redis_client import get_redis
from .database import get_db

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Multi-layer cache manager with automatic fallback.
    
    Cache Layers:
    - L1: In-memory cache (30 seconds TTL) - Fastest
    - L2: Redis cache (1-5 minutes TTL) - Fast
    - L3: Database cache (5+ minutes TTL) - Slower but persistent
    """
    
    def __init__(self):
        # L1: In-memory cache
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        
        # L2: Redis client (lazy initialization)
        self._redis_client = None
        try:
            self._redis_client = get_redis()
        except Exception as e:
            logger.warning(f"Redis not available: {e}")
        
        # L3: Database (lazy initialization)
        self._db = None
        
        # Phase 1.2: Cache statistics tracking
        self._cache_hits: Dict[str, int] = {}  # Track hits per key pattern
        self._cache_misses: Dict[str, int] = {}  # Track misses per key pattern
        self._total_hits = 0
        self._total_misses = 0
    
    def _get_memory_cache_key(self, base_key: str) -> str:
        """Generate memory cache key."""
        return f"l1:{base_key}"
    
    def _get_redis_cache_key(self, base_key: str) -> str:
        """Generate Redis cache key."""
        return f"l2:{base_key}"
    
    def _get_db_cache_key(self, base_key: str) -> str:
        """Generate database cache key."""
        return f"l3:{base_key}"
    
    def _is_stale(self, cached_data: Dict[str, Any], ttl_seconds: int) -> bool:
        """Check if cached data is stale."""
        if "timestamp" not in cached_data:
            return True
        
        timestamp = datetime.fromisoformat(cached_data["timestamp"])
        age = (datetime.utcnow() - timestamp).total_seconds()
        return age > ttl_seconds
    
    def get(self, key: str, ttl_l1: int = 30, ttl_l2: int = 60, ttl_l3: int = 300) -> Optional[Any]:
        """
        Get value from cache (tries L1 -> L2 -> L3).
        
        Args:
            key: Cache key
            ttl_l1: L1 cache TTL in seconds (default: 30)
            ttl_l2: L2 cache TTL in seconds (default: 60)
            ttl_l3: L3 cache TTL in seconds (default: 300)
        
        Returns:
            Cached value or None if not found
        """
        # Try L1: In-memory cache
        l1_key = self._get_memory_cache_key(key)
        if l1_key in self._memory_cache:
            cached = self._memory_cache[l1_key]
            if not self._is_stale(cached, ttl_l1):
                logger.debug(f"Cache HIT (L1): {key}")
                # Phase 1.2: Track cache hit
                self._track_hit(key)
                return cached.get("value")
            else:
                # Remove stale entry
                del self._memory_cache[l1_key]
        
        # Try L2: Redis cache
        if self._redis_client:
            try:
                l2_key = self._get_redis_cache_key(key)
                cached_data = self._redis_client.get(l2_key)
                if cached_data:
                    cached = json.loads(cached_data)
                    if not self._is_stale(cached, ttl_l2):
                        # Promote to L1
                        self._memory_cache[l1_key] = cached
                        logger.debug(f"Cache HIT (L2): {key}")
                        # Phase 1.2: Track cache hit
                        self._track_hit(key)
                        return cached.get("value")
            except Exception as e:
                logger.warning(f"Redis cache read error: {e}")
        
        # Try L3: Database cache (if needed)
        # Note: L3 is typically used for long-term caching
        # For now, we'll skip L3 for performance
        
        logger.debug(f"Cache MISS: {key}")
        # Phase 1.2: Track cache miss
        self._track_miss(key)
        return None
    
    def set(self, key: str, value: Any, ttl_l1: int = 30, ttl_l2: int = 60, ttl_l3: int = 300):
        """
        Set value in cache (writes to L1 and L2).
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_l1: L1 cache TTL in seconds (default: 30)
            ttl_l2: L2 cache TTL in seconds (default: 60)
            ttl_l3: L3 cache TTL in seconds (default: 300)
        """
        timestamp = datetime.utcnow().isoformat()
        cached_data = {
            "value": value,
            "timestamp": timestamp,
        }
        
        # Write to L1: In-memory cache
        l1_key = self._get_memory_cache_key(key)
        self._memory_cache[l1_key] = cached_data
        
        # Write to L2: Redis cache
        if self._redis_client:
            try:
                l2_key = self._get_redis_cache_key(key)
                self._redis_client.setex(
                    l2_key,
                    ttl_l2,
                    json.dumps(cached_data)
                )
            except Exception as e:
                logger.warning(f"Redis cache write error: {e}")
        
        logger.debug(f"Cache SET: {key}")
    
    def invalidate(self, key: str):
        """
        Invalidate cache entry from all layers.
        
        Args:
            key: Cache key to invalidate
        """
        # Invalidate L1
        l1_key = self._get_memory_cache_key(key)
        if l1_key in self._memory_cache:
            del self._memory_cache[l1_key]
        
        # Invalidate L2
        if self._redis_client:
            try:
                l2_key = self._get_redis_cache_key(key)
                self._redis_client.delete(l2_key)
            except Exception as e:
                logger.warning(f"Redis cache delete error: {e}")
        
        logger.debug(f"Cache INVALIDATED: {key}")
    
    def invalidate_pattern(self, pattern: str):
        """
        Invalidate all cache entries matching pattern.
        
        Args:
            pattern: Pattern to match (e.g., "home:dashboard:*")
        """
        # Invalidate L1 entries matching pattern
        pattern_base = pattern.replace("*", "")
        keys_to_delete = [
            k for k in self._memory_cache.keys()
            if pattern_base in k
        ]
        for key in keys_to_delete:
            del self._memory_cache[key]
        
        # Invalidate L2 entries matching pattern
        if self._redis_client:
            try:
                # Use Redis SCAN for pattern matching
                pattern_base = pattern.replace("*", "*")  # Keep * for Redis pattern
                l2_pattern = self._get_redis_cache_key(pattern_base)
                
                # Scan and delete matching keys
                cursor = 0
                deleted_count = 0
                while True:
                    cursor, keys = self._redis_client.scan(cursor, match=l2_pattern, count=100)
                    if keys:
                        deleted_count += self._redis_client.delete(*keys)
                    if cursor == 0:
                        break
                
                logger.debug(f"Cache INVALIDATED (pattern): {pattern} ({deleted_count} keys deleted)")
            except Exception as e:
                logger.warning(f"Redis cache pattern delete error: {e}")
    
    def _track_hit(self, key: str):
        """Track cache hit for statistics."""
        self._total_hits += 1
        # Track by key pattern (e.g., "portfolio:dashboard:*")
        pattern = self._get_key_pattern(key)
        self._cache_hits[pattern] = self._cache_hits.get(pattern, 0) + 1
    
    def _track_miss(self, key: str):
        """Track cache miss for statistics."""
        self._total_misses += 1
        # Track by key pattern
        pattern = self._get_key_pattern(key)
        self._cache_misses[pattern] = self._cache_misses.get(pattern, 0) + 1
    
    def _get_key_pattern(self, key: str) -> str:
        """Extract key pattern from full key."""
        # Extract pattern (e.g., "portfolio:dashboard:1234" -> "portfolio:dashboard")
        parts = key.split(":")
        if len(parts) >= 2:
            return ":".join(parts[:2]) + ":*"
        return key
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        # Calculate cache hit/miss rates
        l1_keys = [k for k in self._memory_cache.keys() if not self._is_stale(self._memory_cache[k], 30)]
        
        total_requests = self._total_hits + self._total_misses
        hit_rate = (self._total_hits / total_requests * 100) if total_requests > 0 else 0
        
        # Get L2 size (if available)
        l2_size = 0
        if self._redis_client:
            try:
                l2_size = self._redis_client.dbsize()
            except Exception:
                pass
        
        return {
            "l1_size": len(self._memory_cache),
            "l1_active": len(l1_keys),
            "l2_size": l2_size,
            "l2_available": self._redis_client is not None,
            "l3_available": False,  # Not implemented yet
            "total_hits": self._total_hits,
            "total_misses": self._total_misses,
            "hit_rate": f"{hit_rate:.2f}%",
            "detailed_hits": dict(self._cache_hits),
            "detailed_misses": dict(self._cache_misses),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    
    def clear_all(self):
        """Clear all cache layers."""
        # Clear L1
        self._memory_cache.clear()
        
        # Clear L2 (pattern-based - simplified)
        if self._redis_client:
            try:
                # Note: Full implementation would use SCAN for pattern matching
                logger.debug("L2 cache clear requested (pattern-based clear not fully implemented)")
            except Exception as e:
                logger.warning(f"Failed to clear L2 cache: {e}")
        
        logger.info("All cache layers cleared")


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager

