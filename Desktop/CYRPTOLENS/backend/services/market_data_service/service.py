"""
Main business logic service for Market Data Service.
Orchestrates API calls, caching, and database operations.
Following CryptoLens Data Architecture Specification.
"""
from typing import Dict, List
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
import random
from shared.data_providers.coingecko_provider import CoinGeckoMarketDataProvider
from shared.data_providers.binance_provider import BinanceOhlcDataProvider
from shared.repositories.crypto_data_repository import CryptoDataRepository
from .api_client import FearGreedClient  # Keep FearGreed as it's not in spec
from .cache_service import MarketCacheService
from .database_service import MarketDatabaseService
from .models import (
    MarketOverviewResponse,
    HeatmapResponse,
    DominanceResponse,
    FearGreedResponse,
    VolatilityResponse,
    VolatileCoin,
    CoinData
)


class MarketDataService:
    """Main service for market data operations."""
    
    def __init__(self):
        # Initialize data providers following architecture spec
        market_provider = CoinGeckoMarketDataProvider()
        ohlc_provider = BinanceOhlcDataProvider()
        self.repository = CryptoDataRepository(market_provider, ohlc_provider)
        
        # Keep FearGreed client (not in architecture spec, but used)
        self.fear_greed = FearGreedClient()
        self.cache = MarketCacheService()
        self.db_service = MarketDatabaseService()
    
    async def get_market_overview(self, db: Session) -> MarketOverviewResponse:
        """Get market overview with caching."""
        # Check cache first
        cached = self.cache.get_market_overview()
        if cached:
            return MarketOverviewResponse(**cached)
        
        # Fetch from repository (uses CoinGecko via MarketDataProvider)
        market_overview = await self.repository.get_market_overview()
        
        response_data = {
            "total_market_cap": market_overview.total_market_cap,
            "total_volume_24h": market_overview.total_volume_24h,
            "btc_dominance": market_overview.btc_dominance,
            "eth_dominance": market_overview.eth_dominance,
            "market_cap_change_24h": market_overview.market_cap_change_24h,
            "active_cryptocurrencies": 0,  # Not provided by MarketOverview, keep 0
            "updated_at": datetime.utcnow()
        }
        
        # Cache the response
        self.cache.set_market_overview(response_data)
        
        return MarketOverviewResponse(**response_data)
    
    async def get_heatmap(self, db: Session, limit: int = 100) -> HeatmapResponse:
        """Get market heatmap data with caching."""
        # Check cache first
        cached = self.cache.get_heatmap()
        if cached:
            return HeatmapResponse(**cached)
        
        # Fetch from CoinGecko directly using markets endpoint (already includes all data)
        import httpx
        from shared.config import settings
        
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": min(limit, 250),
            "page": 1,
            "sparkline": False,
            "price_change_percentage": "24h"
        }
        
        if hasattr(settings, 'COINGECKO_API_KEY') and settings.COINGECKO_API_KEY:
            params["x_cg_demo_api_key"] = settings.COINGECKO_API_KEY
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=30.0)
                response.raise_for_status()
                data = response.json()
            
            coins = []
            for item in data:
                coin_data = CoinData(
                    symbol=item.get("symbol", "").upper(),
                    name=item.get("name", ""),
                    price=Decimal(str(item.get("current_price", 0))),
                    market_cap=Decimal(str(item.get("market_cap", 0) or 0)),
                    volume_24h=Decimal(str(item.get("total_volume", 0) or 0)),
                    price_change_24h=Decimal(str(item.get("price_change_24h", 0) or 0)),
                    price_change_percentage_24h=Decimal(str(item.get("price_change_percentage_24h", 0) or 0))
                )
                coins.append(coin_data)
                
                # Update database cache
                self.db_service.upsert_market_data(
                    db=db,
                    symbol=coin_data.symbol,
                    price=coin_data.price,
                    volume24=coin_data.volume_24h,
                    market_cap=coin_data.market_cap,
                    price_change_24h=coin_data.price_change_24h
                )
            
            response_data = {
                "coins": [coin.dict() for coin in coins],
                "updated_at": datetime.utcnow()
            }
            
            # Cache the response
            self.cache.set_heatmap(response_data)
            
            return HeatmapResponse(**response_data)
        except Exception as e:
            # On error, return empty response
            import logging
            logging.error(f"Error fetching heatmap data: {e}")
            return HeatmapResponse(
                coins=[],
                updated_at=datetime.utcnow()
            )
    
    async def get_dominance(self, db: Session) -> DominanceResponse:
        """Get BTC and ETH dominance with caching."""
        # Check cache first
        cached = self.cache.get_dominance()
        if cached:
            return DominanceResponse(**cached)
        
        # Fetch from repository (uses CoinGecko via MarketDataProvider)
        market_overview = await self.repository.get_market_overview()
        
        other_dominance = Decimal("100") - market_overview.btc_dominance - market_overview.eth_dominance
        
        response_data = {
            "btc_dominance": market_overview.btc_dominance,
            "eth_dominance": market_overview.eth_dominance,
            "other_dominance": other_dominance,
            "updated_at": datetime.utcnow()
        }
        
        # Cache the response
        self.cache.set_dominance(response_data)
        
        return DominanceResponse(**response_data)
    
    async def get_fear_greed(self) -> FearGreedResponse:
        """Get Fear & Greed Index with caching."""
        # Check cache first
        cached = self.cache.get_fear_greed()
        if cached:
            return FearGreedResponse(**cached)
        
        # Fetch from API (FearGreed not in architecture spec, but keep for now)
        fng_data = await self.fear_greed.get_fear_greed_index()
        
        value = int(fng_data.get("value", 50))
        value_classification = fng_data.get("value_classification", "Neutral")
        timestamp = datetime.fromtimestamp(int(fng_data.get("timestamp", 0)))
        
        response_data = {
            "value": value,
            "classification": value_classification,
            "timestamp": timestamp
        }
        
        # Cache the response
        self.cache.set_fear_greed(response_data)
        
        return FearGreedResponse(**response_data)
    
    async def get_volatility(self, db: Session) -> VolatilityResponse:
        """Calculate market volatility index with caching."""
        # Check cache first - but skip if old format detected
        cached = self.cache.get_volatility()
        if cached:
            # Check if cached data has old format (dict with symbol as key instead of VolatileCoin)
            try:
                # Try to validate cached data structure
                if cached.get("top_volatile_coins") and len(cached["top_volatile_coins"]) > 0:
                    first_item = cached["top_volatile_coins"][0]
                    # If first item is a dict with "symbol" key, it's the new format
                    # If it's a string or doesn't have "symbol", it's old format - skip cache
                    if not isinstance(first_item, dict) or "symbol" not in first_item:
                        cached = None  # Skip old format cache
            except:
                cached = None  # Skip cache on any error
                
        if cached:
            try:
                # Convert cached data to proper format
                top_volatile_list = []
                if cached.get("top_volatile_coins"):
                    for v in cached["top_volatile_coins"]:
                        if isinstance(v, dict) and "symbol" in v:
                            top_volatile_list.append(
                                VolatileCoin(symbol=v["symbol"], volatility=Decimal(str(v["volatility"])))
                            )
                
                cached["top_volatile_coins"] = top_volatile_list
                cached["volatility_index"] = Decimal(str(cached["volatility_index"]))
                cached["btc_volatility"] = Decimal(str(cached["btc_volatility"]))
                cached["eth_volatility"] = Decimal(str(cached["eth_volatility"]))
                if isinstance(cached["updated_at"], str):
                    cached["updated_at"] = datetime.fromisoformat(cached["updated_at"].replace("Z", "+00:00"))
                return VolatilityResponse(**cached)
            except Exception as e:
                # If cache parsing fails, skip cache and fetch fresh data
                import logging
                logging.warning(f"Failed to parse cached volatility data: {e}. Fetching fresh data.")
                cached = None  # Skip cache
        
        # Fetch top coins for volatility calculation (uses CoinGecko via repository)
        coins_meta = await self.repository.get_market_list(limit=50)
        symbols = [coin.symbol for coin in coins_meta]
        prices = await self.repository.get_portfolio_data(symbols)
        
        volatilities = []
        for symbol, price_data in prices.items():
            price_change = abs(float(price_data.change_24h))
            volatilities.append({
                "symbol": symbol,
                "volatility": Decimal(str(price_change))
            })
        
        # Sort by volatility
        volatilities.sort(key=lambda x: x["volatility"], reverse=True)
        top_volatile = volatilities[:10]
        
        # Convert to VolatileCoin objects
        top_volatile_coins = [
            VolatileCoin(symbol=v["symbol"], volatility=v["volatility"])
            for v in top_volatile
        ]
        
        # Calculate average volatility
        avg_volatility = sum([float(v["volatility"]) for v in volatilities]) / len(volatilities) if volatilities else 0
        
        # Calculate volatility index (0-100 scale)
        volatility_index = min(Decimal("100"), max(Decimal("0"), Decimal(str(avg_volatility * 2))))
        
        # Determine market volatility level
        if volatility_index < 20:
            market_volatility = "Low"
        elif volatility_index < 40:
            market_volatility = "Medium"
        elif volatility_index < 70:
            market_volatility = "High"
        else:
            market_volatility = "Extreme"
        
        # Get BTC and ETH specific volatility
        btc_vol = Decimal("0")
        eth_vol = Decimal("0")
        if "BTC" in prices:
            btc_vol = Decimal(str(abs(float(prices["BTC"].change_24h))))
        if "ETH" in prices:
            eth_vol = Decimal(str(abs(float(prices["ETH"].change_24h))))
        
        response_data = {
            "volatility_index": volatility_index,
            "market_volatility": market_volatility,
            "btc_volatility": btc_vol,
            "eth_volatility": eth_vol,
            "top_volatile_coins": top_volatile_coins,
            "updated_at": datetime.utcnow()
        }
        
        # Cache the response (convert to dict for caching)
        cache_data = {
            "volatility_index": str(volatility_index),
            "market_volatility": market_volatility,
            "btc_volatility": str(btc_vol),
            "eth_volatility": str(eth_vol),
            "top_volatile_coins": [{"symbol": v.symbol, "volatility": str(v.volatility)} for v in top_volatile_coins],
            "updated_at": datetime.utcnow().isoformat()
        }
        self.cache.set_volatility(cache_data)
        
        return VolatilityResponse(**response_data)
    
    async def get_market_trend(self, db: Session, days: int = 7) -> Dict:
        """Get market trend data for specified number of days."""
        try:
            # Get current market overview
            market_overview = await self.repository.get_market_overview()
            current_change = float(market_overview.market_cap_change_24h)
            
            # Generate trend data based on current change
            # In production, this would fetch historical data from database or API
            trend_data = []
            
            # Simulate trend around current change
            # For now, generate data that varies around the current change
            base_change = current_change
            
            for i in range(days):
                # Create variation around base change
                # Earlier days have more variation, recent days closer to current
                variation_factor = (days - i) / days  # Closer to 1 for recent days
                variation = random.uniform(-2, 2) * (1 - variation_factor)
                trend_value = base_change + variation
                # Clamp to reasonable range
                trend_value = max(-10.0, min(10.0, trend_value))
                trend_data.append(round(trend_value, 2))
            
            return {"trend": trend_data}
        except Exception as e:
            import logging
            logging.error(f"Error fetching trend data: {e}")
            # Return empty list on error
            return {"trend": []}
    
    async def close(self):
        """Close API clients."""
        await self.repository.market_provider.close()
        await self.repository.ohlc_provider.close()
        await self.fear_greed.close()
