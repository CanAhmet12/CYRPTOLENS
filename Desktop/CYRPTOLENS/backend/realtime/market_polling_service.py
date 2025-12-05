"""
Market Polling Service
Polls CoinGecko for market data at regular intervals.
"""
import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
import httpx
from shared.data_providers.coingecko_provider import CoinGeckoMarketDataProvider

logger = logging.getLogger(__name__)


class MarketPollingService:
    """
    Polls CoinGecko for market data and caches results.
    PERFORMANCE FIX: Optimized polling interval and error handling.
    """
    
    # PERFORMANCE FIX: Increased interval to 60s to reduce rate limit risk
    POLL_INTERVAL = 60  # seconds (was 30, increased for rate limit protection)
    STALE_THRESHOLD = 300  # 5 minutes in seconds
    
    def __init__(self):
        self.coingecko_provider = CoinGeckoMarketDataProvider()
        self.market_cache: Dict = {}
        self.last_successful_fetch: Optional[datetime] = None
        self.is_running = False
        self._poll_task: Optional[asyncio.Task] = None
        # PERFORMANCE FIX: Error tracking for exponential backoff
        self._error_count = 0
        self._consecutive_errors = 0
    
    async def start(self):
        """Start the polling service."""
        if self.is_running:
            logger.warning("Market polling service already running")
            return
        
        self.is_running = True
        self._poll_task = asyncio.create_task(self._poll_loop())
        logger.info("Market polling service started")
    
    async def stop(self):
        """Stop the polling service."""
        self.is_running = False
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        logger.info("Market polling service stopped")
    
    async def _poll_loop(self):
        """
        Main polling loop.
        PERFORMANCE FIX: Added exponential backoff for error recovery.
        """
        while self.is_running:
            try:
                await self._fetch_market_data()
                # PERFORMANCE FIX: Reset error count on success
                self._error_count = 0
                self._consecutive_errors = 0
                await asyncio.sleep(self.POLL_INTERVAL)
            except Exception as e:
                self._error_count += 1
                self._consecutive_errors += 1
                logger.error(f"Error in market polling (attempt {self._consecutive_errors}): {e}")
                # Don't clear cache on error - keep last known values
                
                # PERFORMANCE FIX: Exponential backoff on consecutive errors
                # 60s, 120s, 240s, 300s (max)
                if self._consecutive_errors > 1:
                    backoff_delay = min(
                        self.POLL_INTERVAL * (2 ** (self._consecutive_errors - 1)),
                        300  # Max 5 minutes
                    )
                    logger.warning(f"Using exponential backoff: {backoff_delay}s")
                    await asyncio.sleep(backoff_delay)
                else:
                    await asyncio.sleep(self.POLL_INTERVAL)
    
    async def _fetch_market_data(self):
        """Fetch market data from CoinGecko."""
        try:
            # Fetch top coins
            top_coins = await self.coingecko_provider.get_top_coins(limit=100)
            
            # Fetch global market data
            global_data = await self.coingecko_provider.get_global_market_data()
            
            # Update cache with timestamp
            self.market_cache = {
                'coins': top_coins,
                'global': global_data,
                'lastUpdated': datetime.utcnow().isoformat(),
                'isStale': False
            }
            
            self.last_successful_fetch = datetime.utcnow()
            logger.debug(f"Market data updated at {self.last_successful_fetch}")
            
        except Exception as e:
            logger.error(f"Failed to fetch market data: {e}")
            # Mark as stale but keep last known values
            if self.market_cache:
                self.market_cache['isStale'] = True
    
    def get_market_overview(self) -> Dict:
        """
        Get market overview from cache.
        Always returns last known values, never None.
        
        Returns:
            Dict with coins, global metrics, lastUpdated, isStale
        """
        if not self.market_cache:
            # Return empty structure if no data yet
            return {
                'coins': [],
                'global': {},
                'lastUpdated': None,
                'isStale': True
            }
        
        # Check if data is stale
        if self.last_successful_fetch:
            age_seconds = (datetime.utcnow() - self.last_successful_fetch).total_seconds()
            is_stale = age_seconds > self.STALE_THRESHOLD
            self.market_cache['isStale'] = is_stale
        
        return self.market_cache.copy()
    
    def is_data_stale(self) -> bool:
        """Check if cached data is stale."""
        if not self.last_successful_fetch:
            return True
        
        age_seconds = (datetime.utcnow() - self.last_successful_fetch).total_seconds()
        return age_seconds > self.STALE_THRESHOLD

