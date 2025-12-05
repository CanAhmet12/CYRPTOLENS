"""
Cache service for Market Data Service.
Uses Redis for high-frequency data caching.
"""
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from shared.redis_client import get_redis


class MarketCacheService:
    """Service for caching market data in Redis."""
    
    # Cache TTLs (in seconds)
    MARKET_OVERVIEW_TTL = 60  # 1 minute
    HEATMAP_TTL = 60  # 1 minute
    DOMINANCE_TTL = 300  # 5 minutes
    FEAR_GREED_TTL = 3600  # 1 hour
    VOLATILITY_TTL = 300  # 5 minutes
    
    def __init__(self):
        self.redis = get_redis()
    
    def _serialize(self, data: Any) -> str:
        """Serialize data to JSON string."""
        # Handle Decimal and datetime serialization
        if isinstance(data, dict):
            return json.dumps(data, default=str)
        return json.dumps(data, default=str)
    
    def _deserialize(self, data: str) -> Any:
        """Deserialize JSON string to Python object."""
        return json.loads(data)
    
    def get_market_overview(self) -> Optional[Dict]:
        """Get cached market overview."""
        if not self.redis:
            return None
        key = "market:overview"
        try:
            data = self.redis.get(key)
            if data:
                return self._deserialize(data)
        except Exception:
            pass
        return None
    
    def set_market_overview(self, data: Dict, ttl: int = None):
        """Cache market overview."""
        if not self.redis:
            return
        key = "market:overview"
        ttl = ttl or self.MARKET_OVERVIEW_TTL
        try:
            self.redis.setex(key, ttl, self._serialize(data))
        except Exception:
            pass  # Cache failures should not break the app
    
    def get_heatmap(self) -> Optional[Dict]:
        """Get cached heatmap data."""
        key = "market:heatmap"
        data = self.redis.get(key)
        if data:
            return self._deserialize(data)
        return None
    
    def set_heatmap(self, data: Dict, ttl: int = None):
        """Cache heatmap data."""
        key = "market:heatmap"
        ttl = ttl or self.HEATMAP_TTL
        self.redis.setex(key, ttl, self._serialize(data))
    
    def get_dominance(self) -> Optional[Dict]:
        """Get cached dominance data."""
        key = "market:dominance"
        data = self.redis.get(key)
        if data:
            return self._deserialize(data)
        return None
    
    def set_dominance(self, data: Dict, ttl: int = None):
        """Cache dominance data."""
        key = "market:dominance"
        ttl = ttl or self.DOMINANCE_TTL
        self.redis.setex(key, ttl, self._serialize(data))
    
    def get_fear_greed(self) -> Optional[Dict]:
        """Get cached Fear & Greed Index."""
        key = "market:feargreed"
        data = self.redis.get(key)
        if data:
            return self._deserialize(data)
        return None
    
    def set_fear_greed(self, data: Dict, ttl: int = None):
        """Cache Fear & Greed Index."""
        key = "market:feargreed"
        ttl = ttl or self.FEAR_GREED_TTL
        self.redis.setex(key, ttl, self._serialize(data))
    
    def get_volatility(self) -> Optional[Dict]:
        """Get cached volatility data."""
        key = "market:volatility"
        data = self.redis.get(key)
        if data:
            return self._deserialize(data)
        return None
    
    def set_volatility(self, data: Dict, ttl: int = None):
        """Cache volatility data."""
        key = "market:volatility"
        ttl = ttl or self.VOLATILITY_TTL
        self.redis.setex(key, ttl, self._serialize(data))
    
    def get(self, key: str) -> Optional[Dict]:
        """Generic get method for any cache key."""
        if not self.redis:
            return None
        try:
            data = self.redis.get(key)
            if data:
                return self._deserialize(data)
        except Exception:
            pass
        return None
    
    def set(self, key: str, data: Dict, ttl: int = 300):
        """Generic set method for any cache key."""
        if not self.redis:
            return
        try:
            self.redis.setex(key, ttl, self._serialize(data))
        except Exception:
            pass  # Cache failures should not break the app
    
    # ORTA: Cache invalidation methods
    def invalidate(self, key: str):
        """Invalidate a specific cache key."""
        if not self.redis:
            return
        try:
            self.redis.delete(key)
        except Exception:
            pass
    
    def invalidate_pattern(self, pattern: str):
        """Invalidate all cache keys matching a pattern (e.g., 'market:*')."""
        if not self.redis:
            return
        try:
            # Redis SCAN for pattern matching
            cursor = 0
            while True:
                cursor, keys = self.redis.scan(cursor, match=pattern, count=100)
                if keys:
                    self.redis.delete(*keys)
                if cursor == 0:
                    break
        except Exception:
            pass
    
    def invalidate_market_data(self):
        """Invalidate all market data cache."""
        if not self.redis:
            return
        self.invalidate_pattern("market:*")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self.redis:
            return {"error": "Redis not available"}
        try:
            info = self.redis.info("memory")
            keyspace = self.redis.info("keyspace")
            return {
                "redis_connected": True,
                "memory_used": info.get("used_memory_human", "N/A"),
                "keyspace": keyspace,
            }
        except Exception as e:
            return {"error": str(e)}

