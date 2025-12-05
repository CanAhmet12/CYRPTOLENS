"""
Background Tasks and Scheduled Jobs for CryptoLens backend.
Handles scheduled refresh, precomputed aggregations, and data prefetching.
"""
import asyncio
import logging
from typing import Dict, Optional, Callable, Any
from datetime import datetime, timedelta
from .cache_manager import get_cache_manager
from .redis_client import get_redis
import json
import httpx
from .config import settings

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """
    Manages background tasks and scheduled jobs.
    
    Features:
    - Scheduled refresh (market data every 30s, portfolio every 1m, AI insights every 5m)
    - Precomputed aggregations (top gainers/losers, market trends)
    - Data prefetching (next page data, related data)
    """
    
    def __init__(self):
        self._tasks: Dict[str, asyncio.Task] = {}
        self._is_running = False
        self._cache_manager = get_cache_manager()
        self._redis_client = get_redis()
    
    async def start(self):
        """Start all background tasks."""
        if self._is_running:
            logger.warning("Background tasks already running")
            return
        
        self._is_running = True
        logger.info("Starting background tasks...")
        
        # Start scheduled refresh tasks
        self._tasks["market_refresh"] = asyncio.create_task(self._market_refresh_loop())
        self._tasks["portfolio_refresh"] = asyncio.create_task(self._portfolio_refresh_loop())
        self._tasks["ai_insight_refresh"] = asyncio.create_task(self._ai_insight_refresh_loop())
        self._tasks["precompute_aggregations"] = asyncio.create_task(self._precompute_aggregations_loop())
        # Phase 1.3: Portfolio-specific background jobs
        self._tasks["transaction_history_refresh"] = asyncio.create_task(self._transaction_history_refresh_loop())
        self._tasks["performance_metrics_precompute"] = asyncio.create_task(self._performance_metrics_precompute_loop())
        
        logger.info("Background tasks started")
    
    async def stop(self):
        """Stop all background tasks."""
        self._is_running = False
        
        # Cancel all tasks
        for task_name, task in self._tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self._tasks.clear()
        logger.info("Background tasks stopped")
    
    async def _market_refresh_loop(self):
        """Refresh market data every 30 seconds."""
        while self._is_running:
            try:
                await self._refresh_market_data()
            except Exception as e:
                logger.error(f"Error in market refresh: {e}")
            
            await asyncio.sleep(30)  # 30 seconds
    
    async def _refresh_market_data(self):
        """Refresh market data and invalidate cache."""
        try:
            # Phase 1.2: Smart cache invalidation for market dashboard
            # Invalidate market dashboard cache patterns
            self._cache_manager.invalidate_pattern("market:dashboard:*")
            self._cache_manager.invalidate_pattern("market:overview")
            self._cache_manager.invalidate_pattern("market:heatmap")
            self._cache_manager.invalidate_pattern("market:dominance")
            self._cache_manager.invalidate_pattern("market:feargreed")
            self._cache_manager.invalidate_pattern("market:volatility")
            self._cache_manager.invalidate_pattern("market:trend")
            
            logger.debug("Market data cache invalidated")
        except Exception as e:
            logger.warning(f"Error invalidating market cache: {e}")
    
    async def _portfolio_refresh_loop(self):
        """Refresh portfolio data every 1 minute."""
        while self._is_running:
            try:
                await self._refresh_portfolio_data()
            except Exception as e:
                logger.error(f"Error in portfolio refresh: {e}")
            
            await asyncio.sleep(60)  # 1 minute
    
    async def _transaction_history_refresh_loop(self):
        """Refresh transaction history every 2 minutes."""
        while self._is_running:
            try:
                await self._refresh_transaction_history()
            except Exception as e:
                logger.error(f"Error in transaction history refresh: {e}")
            
            await asyncio.sleep(120)  # 2 minutes
    
    async def _performance_metrics_precompute_loop(self):
        """Precompute performance metrics every 5 minutes."""
        while self._is_running:
            try:
                await self._precompute_performance_metrics()
            except Exception as e:
                logger.error(f"Error in performance metrics precomputation: {e}")
            
            await asyncio.sleep(300)  # 5 minutes
    
    async def _ai_insight_refresh_loop(self):
        """Refresh AI insights every 5 minutes."""
        while self._is_running:
            try:
                await self._refresh_ai_insights()
            except Exception as e:
                logger.error(f"Error in AI insight refresh: {e}")
            
            await asyncio.sleep(300)  # 5 minutes
    
    async def _precompute_aggregations_loop(self):
        """Precompute aggregations every 1 minute."""
        while self._is_running:
            try:
                await self._precompute_aggregations()
            except Exception as e:
                logger.error(f"Error in precompute aggregations: {e}")
            
            await asyncio.sleep(60)  # 1 minute
    
    async def _refresh_market_data(self):
        """Refresh market data and update cache."""
        try:
            # Phase 1.2: Smart cache invalidation for market dashboard
            # Invalidate market dashboard cache patterns first
            self._cache_manager.invalidate_pattern("market:dashboard:*")
            self._cache_manager.invalidate_pattern("market:overview")
            self._cache_manager.invalidate_pattern("market:heatmap")
            self._cache_manager.invalidate_pattern("market:dominance")
            self._cache_manager.invalidate_pattern("market:feargreed")
            self._cache_manager.invalidate_pattern("market:volatility")
            self._cache_manager.invalidate_pattern("market:trend")
            
            market_service_url = settings.MARKET_SERVICE_URL
            
            # Fetch market overview
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                overview_response = await client.get(f"{market_service_url}/market/overview")
                if overview_response.status_code == 200:
                    overview_data = overview_response.json()
                    cache_key = "market:overview"
                    self._cache_manager.set(cache_key, overview_data, ttl_l1=30, ttl_l2=60)
                    logger.debug("Market overview refreshed")
                
                # Fetch heatmap
                heatmap_response = await client.get(f"{market_service_url}/market/heatmap?limit=250")
                if heatmap_response.status_code == 200:
                    heatmap_data = heatmap_response.json()
                    cache_key = "market:heatmap"
                    self._cache_manager.set(cache_key, heatmap_data, ttl_l1=30, ttl_l2=60)
                    logger.debug("Market heatmap refreshed")
        except Exception as e:
            logger.warning(f"Failed to refresh market data: {e}")
    
    async def _refresh_portfolio_data(self):
        """Refresh portfolio data for active users (prefetch)."""
        try:
            # Phase 1.3: Enhanced portfolio refresh
            # Invalidate portfolio dashboard cache to force refresh on next request
            self._cache_manager.invalidate_pattern("portfolio:dashboard:*")
            
            # Also invalidate portfolio-specific caches
            self._cache_manager.invalidate_pattern("portfolio:*")
            
            logger.debug("Portfolio data cache invalidated (will refresh on next request)")
        except Exception as e:
            logger.warning(f"Failed to refresh portfolio data: {e}")
    
    async def _refresh_transaction_history(self):
        """Refresh transaction history cache."""
        try:
            # Phase 1.3: Transaction history refresh
            # Invalidate transaction history cache
            self._cache_manager.invalidate_pattern("portfolio:transactions:*")
            
            logger.debug("Transaction history cache invalidated")
        except Exception as e:
            logger.warning(f"Failed to refresh transaction history: {e}")
    
    async def _precompute_performance_metrics(self):
        """Precompute performance metrics (Sharpe Ratio, Alpha/Beta, etc.)."""
        try:
            # Phase 1.3: Performance metrics precomputation
            # Invalidate performance metrics cache to force recalculation
            self._cache_manager.invalidate_pattern("portfolio:analytics:*")
            self._cache_manager.invalidate_pattern("portfolio:performance:*")
            
            logger.debug("Performance metrics cache invalidated (will recalculate on next request)")
        except Exception as e:
            logger.warning(f"Failed to precompute performance metrics: {e}")
    
    async def _refresh_ai_insights(self):
        """Refresh AI insights for market (global)."""
        try:
            # Get market data
            market_data = self._cache_manager.get("market:overview")
            if not market_data:
                return
            
            # Prepare market data for AI
            market_data_for_ai = {
                "market": {
                    "total_market_cap": market_data.get("total_market_cap", 0),
                    "total_volume_24h": market_data.get("total_volume_24h", 0),
                    "market_cap_change_24h": market_data.get("market_cap_change_24h", 0),
                    "btc_dominance": market_data.get("btc_dominance", 0),
                    "fear_greed": 50,  # Default
                    "volatility_index": 0.5,  # Default
                    "trend_score": 50,  # Default
                }
            }
            
            # Generate AI insight
            ai_service_url = settings.AI_SERVICE_URL
            async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
                ai_response = await client.post(
                    f"{ai_service_url}/ai/market",
                    json=market_data_for_ai
                )
                if ai_response.status_code == 200:
                    ai_insight = ai_response.json()
                    ai_insight["timestamp"] = datetime.utcnow().isoformat() + "Z"
                    
                    # Cache AI insight (global, not user-specific)
                    cache_key = "ai_insights:market:global"
                    self._cache_manager.set(cache_key, ai_insight, ttl_l1=300, ttl_l2=300)
                    logger.info("AI insight refreshed")
        except Exception as e:
            logger.warning(f"Failed to refresh AI insights: {e}")
    
    async def _precompute_aggregations(self):
        """Precompute aggregations (top gainers/losers, market trends)."""
        try:
            # Get heatmap data
            heatmap_data = self._cache_manager.get("market:heatmap")
            if not heatmap_data:
                return
            
            coins = heatmap_data.get("coins", []) if isinstance(heatmap_data, dict) else []
            
            # Precompute top gainers
            top_gainers = sorted(
                [c for c in coins if c.get("price_change_percentage_24h", 0) > 0],
                key=lambda x: x.get("price_change_percentage_24h", 0),
                reverse=True
            )[:10]
            
            # Precompute top losers
            top_losers = sorted(
                [c for c in coins if c.get("price_change_percentage_24h", 0) < 0],
                key=lambda x: x.get("price_change_percentage_24h", 0)
            )[:10]
            
            # Cache precomputed aggregations
            aggregations = {
                "topGainers": top_gainers,
                "topLosers": top_losers,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            
            cache_key = "market:aggregations"
            self._cache_manager.set(cache_key, aggregations, ttl_l1=30, ttl_l2=60)
            logger.debug("Aggregations precomputed")
        except Exception as e:
            logger.warning(f"Failed to precompute aggregations: {e}")
    
    def _get_active_users(self) -> list:
        """Get list of active users (simplified - tracks recent cache access)."""
        # This is a simplified version
        # In production, you'd track user activity in Redis or database
        return []
    
    async def prefetch_data(self, key: str, fetch_func: Callable[[], Any], ttl: int = 60):
        """
        Prefetch data and cache it.
        
        Args:
            key: Cache key
            fetch_func: Async function to fetch data
            ttl: Cache TTL in seconds
        """
        try:
            data = await fetch_func()
            self._cache_manager.set(key, data, ttl_l1=ttl, ttl_l2=ttl * 2)
            logger.debug(f"Data prefetched: {key}")
        except Exception as e:
            logger.warning(f"Failed to prefetch data {key}: {e}")


# Global background task manager instance
_background_task_manager: Optional[BackgroundTaskManager] = None


def get_background_task_manager() -> BackgroundTaskManager:
    """Get global background task manager instance."""
    global _background_task_manager
    if _background_task_manager is None:
        _background_task_manager = BackgroundTaskManager()
    return _background_task_manager

