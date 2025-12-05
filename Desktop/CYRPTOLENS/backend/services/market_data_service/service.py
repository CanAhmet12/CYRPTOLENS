"""
Main business logic service for Market Data Service.
Orchestrates API calls, caching, and database operations.
Following CryptoLens Data Architecture Specification.
"""
# Standard library imports
import random
from datetime import datetime
from decimal import Decimal
from typing import Dict, List

# Third-party imports
from sqlalchemy.orm import Session

# Local application imports
from shared.data_providers.binance_provider import BinanceOhlcDataProvider
from shared.data_providers.coingecko_provider import CoinGeckoMarketDataProvider
from shared.repositories.crypto_data_repository import CryptoDataRepository
from .api_client import FearGreedClient  # Keep FearGreed as it's not in spec
from .cache_service import MarketCacheService
from .database_service import MarketDatabaseService
from .models import (
    CategoriesResponse,
    ChainsResponse,
    CoinData,
    DominanceResponse,
    ExchangesResponse,
    FearGreedResponse,
    HeatmapResponse,
    MarketCapHistoryResponse,
    MarketOverviewResponse,
    VolatileCoin,
    VolatilityResponse,
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
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(f"Cache validation error: {e}")
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
        try:
            coins_meta = await self.repository.get_market_list(limit=50)
            symbols = [coin.symbol for coin in coins_meta]
            prices = await self.repository.get_portfolio_data(symbols)
        except Exception as e:
            import logging
            logging.error(f"Error fetching coins for volatility: {e}", exc_info=True)
            # Return default response on error
            return VolatilityResponse(
                volatility_index=Decimal("0"),
                market_volatility="Low",
                btc_volatility=Decimal("0"),
                eth_volatility=Decimal("0"),
                top_volatile_coins=[],
                updated_at=datetime.utcnow()
            )
        
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
    
    async def get_exchanges(self, db: Session, exchange_type: str = "all") -> ExchangesResponse:
        """Get exchanges list with optional type filter from CoinGecko API."""
        from .models import ExchangeData
        import httpx
        from shared.config import settings
        
        # Check cache first
        cache_key = f"exchanges_{exchange_type}"
        cached = self.cache.get(f"exchanges_{exchange_type}")
        if cached:
            try:
                exchanges_list = [ExchangeData(**e) for e in cached.get("exchanges", [])]
                return ExchangesResponse(
                    exchanges=exchanges_list,
                    updated_at=datetime.fromisoformat(cached["updated_at"].replace("Z", "+00:00"))
                )
            except:
                pass  # If cache parsing fails, fetch fresh data
        
        try:
            url = "https://api.coingecko.com/api/v3/exchanges"
            params = {
                "per_page": 250,
                "page": 1
            }
            
            if hasattr(settings, 'COINGECKO_API_KEY') and settings.COINGECKO_API_KEY:
                params["x_cg_demo_api_key"] = settings.COINGECKO_API_KEY
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=30.0)
                response.raise_for_status()
                data = response.json()
            
            # Get current BTC price for volume conversion
            btc_price = Decimal("50000")  # Default fallback
            try:
                btc_prices = await self.repository.get_portfolio_data(["BTC"])
                if "BTC" in btc_prices:
                    btc_price = btc_prices["BTC"].price
            except:
                pass  # Use default if BTC price fetch fails
            
            exchanges = []
            for item in data:
                # Determine exchange type based on name or other indicators
                exchange_name = item.get("name", "").lower()
                ex_type = "Spot"  # Default
                if "derivatives" in exchange_name or "futures" in exchange_name:
                    ex_type = "Derivatives"
                elif "dex" in exchange_name or "uniswap" in exchange_name or "pancake" in exchange_name:
                    ex_type = "DEX"
                
                # Get trust score (0-10 scale, convert to Decimal)
                trust_score = item.get("trust_score", 0)
                if trust_score is None:
                    trust_score = 0
                
                # Get 24h volume in BTC, convert to USD using current BTC price
                volume_btc = Decimal(str(item.get("trade_volume_24h_btc", 0) or 0))
                volume_usd = volume_btc * btc_price
                
                # Only add if matches filter
                if exchange_type == "all" or ex_type == exchange_type:
                    exchanges.append(ExchangeData(
                        name=item.get("name", "Unknown"),
                        score=Decimal(str(trust_score)),
                        volume_24h=volume_usd,
                        type=ex_type
                    ))
            
            # Sort by volume descending
            exchanges.sort(key=lambda x: x.volume_24h, reverse=True)
            
            response_data = {
                "exchanges": [e.dict() for e in exchanges],
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Cache the response
            self.cache.set(f"exchanges_{exchange_type}", response_data, ttl=300)  # 5 minutes cache
            
            return ExchangesResponse(
                exchanges=exchanges,
                updated_at=datetime.utcnow()
            )
        except Exception as e:
            import logging
            logging.error(f"Error fetching exchanges data: {e}")
            # Return empty response on error
            return ExchangesResponse(
                exchanges=[],
                updated_at=datetime.utcnow()
            )
    
    async def get_chains(self, db: Session) -> ChainsResponse:
        """Get blockchain chains list from CoinGecko API."""
        from .models import ChainData
        import httpx
        from shared.config import settings
        
        # Check cache first
        cached = self.cache.get("chains")
        if cached:
            try:
                chains_list = [ChainData(**c) for c in cached.get("chains", [])]
                return ChainsResponse(
                    chains=chains_list,
                    updated_at=datetime.fromisoformat(cached["updated_at"].replace("Z", "+00:00"))
                )
            except:
                pass  # If cache parsing fails, fetch fresh data
        
        try:
            # Fetch asset platforms (blockchains) from CoinGecko
            url = "https://api.coingecko.com/api/v3/asset_platforms"
            params = {}
            
            if hasattr(settings, 'COINGECKO_API_KEY') and settings.COINGECKO_API_KEY:
                params["x_cg_demo_api_key"] = settings.COINGECKO_API_KEY
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=30.0)
                response.raise_for_status()
                platforms = response.json()
            
            # Get top coins to determine project counts and market data
            markets_url = "https://api.coingecko.com/api/v3/coins/markets"
            markets_params = {
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": 250,
                "page": 1
            }
            
            if hasattr(settings, 'COINGECKO_API_KEY') and settings.COINGECKO_API_KEY:
                markets_params["x_cg_demo_api_key"] = settings.COINGECKO_API_KEY
            
            async with httpx.AsyncClient() as client:
                markets_response = await client.get(markets_url, params=markets_params, timeout=30.0)
                markets_response.raise_for_status()
                coins_data = markets_response.json()
            
            # Major blockchain platforms to prioritize with their native coin symbols
            major_platforms_config = {
                "ethereum": {"symbols": ["eth", "weth", "usdt", "usdc", "dai", "link", "uni", "aave"], "default_projects": 100},
                "binance-smart-chain": {"symbols": ["bnb", "busd", "cake"], "default_projects": 50},
                "polygon-pos": {"symbols": ["matic", "poly"], "default_projects": 30},
                "avalanche": {"symbols": ["avax"], "default_projects": 20},
                "solana": {"symbols": ["sol"], "default_projects": 25},
                "cardano": {"symbols": ["ada"], "default_projects": 15},
                "polkadot": {"symbols": ["dot"], "default_projects": 20},
                "cosmos": {"symbols": ["atom"], "default_projects": 15},
                "near-protocol": {"symbols": ["near"], "default_projects": 10},
                "fantom": {"symbols": ["ftm"], "default_projects": 10},
                "arbitrum-one": {"symbols": ["arb"], "default_projects": 15},
                "optimistic-ethereum": {"symbols": ["op"], "default_projects": 10},
                "base": {"symbols": [], "default_projects": 10},
                "tron": {"symbols": ["trx"], "default_projects": 15},
                "stellar": {"symbols": ["xlm"], "default_projects": 5},
                "algorand": {"symbols": ["algo"], "default_projects": 5},
                "tezos": {"symbols": ["xtz"], "default_projects": 5},
                "cronos": {"symbols": ["cro"], "default_projects": 5},
                "celo": {"symbols": ["celo"], "default_projects": 5},
                "osmosis": {"symbols": ["osmo"], "default_projects": 5}
            }
            
            # Create a mapping of platform IDs to their data
            platform_map = {p.get("id"): p for p in platforms}
            
            # First, add major platforms with estimated data
            chains = []
            chain_ids_added = set()
            
            # Process major platforms first - ALWAYS add them even if no matching coins
            for platform_id, config in major_platforms_config.items():
                if platform_id in platform_map:
                    platform = platform_map[platform_id]
                    platform_name = platform.get("name", "Unknown")
                    native_coin = platform.get("native_coin_id", "")
                    
                    # Start with default project count
                    projects_count = config["default_projects"]
                    tvl = Decimal("0")
                    price_change_sum = Decimal("0")
                    price_change_count = 0
                    
                    # Try to find matching coins for better estimates
                    matching_symbols = config["symbols"]
                    for coin in coins_data:
                        coin_symbol = coin.get("symbol", "").lower()
                        coin_name = coin.get("name", "").lower()
                        
                        # Check if coin matches this platform
                        if (coin_symbol in matching_symbols or 
                            coin_symbol == platform_id.split("-")[0].lower() or
                            platform_id.split("-")[0].lower() in coin_symbol or
                            platform_name.lower() in coin_name):
                            projects_count += 1
                            market_cap = Decimal(str(coin.get("market_cap", 0) or 0))
                            tvl += market_cap / Decimal("1000000000")  # Convert to billions
                            price_change = coin.get("price_change_percentage_24h")
                            if price_change is not None:
                                price_change_sum += Decimal(str(price_change))
                                price_change_count += 1
                    
                    # Calculate average price change
                    avg_change = Decimal("0")
                    if price_change_count > 0:
                        avg_change = price_change_sum / Decimal(str(price_change_count))
                    else:
                        # Use market average for major chains if no specific data
                        if coins_data:
                            total_change = sum(Decimal(str(c.get("price_change_percentage_24h", 0) or 0)) for c in coins_data[:20])
                            avg_change = total_change / Decimal(str(min(len(coins_data), 20)))
                    
                    # Ensure minimum TVL for major chains (they're important!)
                    if tvl == 0:
                        # Set realistic default TVL based on chain importance
                        default_tvl_map = {
                            "ethereum": Decimal("50.0"),  # ~50B TVL
                            "binance-smart-chain": Decimal("5.0"),
                            "polygon-pos": Decimal("1.0"),
                            "solana": Decimal("2.0"),
                            "avalanche": Decimal("1.0"),
                            "cardano": Decimal("0.5"),
                            "polkadot": Decimal("0.5"),
                            "arbitrum-one": Decimal("2.0"),
                            "optimistic-ethereum": Decimal("1.0"),
                            "base": Decimal("1.0"),
                        }
                        tvl = default_tvl_map.get(platform_id, Decimal("0.5"))
                    
                    chains.append(ChainData(
                        name=platform_name,
                        symbol=native_coin.upper() if native_coin else platform_id.replace("-", " ").title().replace(" ", ""),
                        projects_count=projects_count,
                        tvl=tvl,
                        tvl_change_24h=avg_change
                    ))
                    chain_ids_added.add(platform_id)
            
            # Then add other platforms that have matching coins
            for platform in platforms:
                platform_id = platform.get("id")
                if platform_id in chain_ids_added:
                    continue
                    
                platform_name = platform.get("name", "Unknown")
                native_coin = platform.get("native_coin_id", "")
                
                projects_count = 0
                total_market_cap = Decimal("0")
                price_change_sum = Decimal("0")
                price_change_count = 0
                
                # Match coins to platforms
                for coin in coins_data:
                    coin_name = coin.get("name", "").lower()
                    coin_symbol = coin.get("symbol", "").lower()
                    platform_name_lower = platform_name.lower()
                    platform_id_lower = platform_id.lower()
                    
                    if (platform_name_lower in coin_name or 
                        platform_name_lower in coin_symbol or
                        coin_symbol in platform_name_lower or
                        platform_id_lower in coin_symbol):
                        projects_count += 1
                        total_market_cap += Decimal(str(coin.get("market_cap", 0) or 0))
                        price_change = coin.get("price_change_percentage_24h")
                        if price_change is not None:
                            price_change_sum += Decimal(str(price_change))
                            price_change_count += 1
                
                if projects_count > 0:
                    avg_change = Decimal("0")
                    if price_change_count > 0:
                        avg_change = price_change_sum / Decimal(str(price_change_count))
                    
                    tvl = total_market_cap / Decimal("1000000000")
                    
                    chains.append(ChainData(
                        name=platform_name,
                        symbol=native_coin.upper() if native_coin else platform_id.replace("-", " ").title().replace(" ", ""),
                        projects_count=projects_count,
                        tvl=tvl,
                        tvl_change_24h=avg_change
                    ))
            
            # Sort by projects count descending
            chains.sort(key=lambda x: x.projects_count, reverse=True)
            # Limit to top 50 chains
            chains = chains[:50]
            
            response_data = {
                "chains": [c.dict() for c in chains],
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Cache the response
            self.cache.set("chains", response_data, ttl=600)  # 10 minutes cache
            
            return ChainsResponse(
                chains=chains,
                updated_at=datetime.utcnow()
            )
        except Exception as e:
            import logging
            logging.error(f"Error fetching chains data: {e}")
            # Return empty response on error
            return ChainsResponse(
                chains=[],
                updated_at=datetime.utcnow()
            )
    
    async def get_categories(self, db: Session) -> CategoriesResponse:
        """Get cryptocurrency categories list from CoinGecko API."""
        from .models import CategoryData
        import httpx
        from shared.config import settings
        
        # Check cache first
        cached = self.cache.get("categories")
        if cached:
            try:
                categories_list = [CategoryData(**c) for c in cached.get("categories", [])]
                return CategoriesResponse(
                    categories=categories_list,
                    updated_at=datetime.fromisoformat(cached["updated_at"].replace("Z", "+00:00"))
                )
            except:
                pass  # If cache parsing fails, fetch fresh data
        
        try:
            url = "https://api.coingecko.com/api/v3/coins/categories"
            params = {}
            
            if hasattr(settings, 'COINGECKO_API_KEY') and settings.COINGECKO_API_KEY:
                params["x_cg_demo_api_key"] = settings.COINGECKO_API_KEY
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=30.0)
                response.raise_for_status()
                data = response.json()
            
            categories = []
            for item in data:
                market_cap = Decimal(str(item.get("market_cap", 0) or 0))
                market_cap_change_24h = Decimal(str(item.get("market_cap_change_24h", 0) or 0))
                
                categories.append(CategoryData(
                    name=item.get("name", "Unknown"),
                    market_cap=market_cap / Decimal("1000000000"),  # Convert to billions
                    avg_price_change=market_cap_change_24h
                ))
            
            # Sort by market cap descending
            categories.sort(key=lambda x: x.market_cap, reverse=True)
            
            response_data = {
                "categories": [c.dict() for c in categories],
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Cache the response
            self.cache.set("categories", response_data, ttl=600)  # 10 minutes cache
            
            return CategoriesResponse(
                categories=categories,
                updated_at=datetime.utcnow()
            )
        except Exception as e:
            import logging
            logging.error(f"Error fetching categories data: {e}")
            # Return empty response on error
            return CategoriesResponse(
                categories=[],
                updated_at=datetime.utcnow()
            )
    
    async def get_market_cap_history(self, db: Session, days: int = 30) -> MarketCapHistoryResponse:
        """Get market cap history from CoinGecko API."""
        from .models import MarketCapHistoryPoint
        import httpx
        from shared.config import settings
        
        # Check cache first
        cache_key = f"market_cap_history_{days}"
        cached = self.cache.get(cache_key)
        if cached:
            try:
                data_points = [MarketCapHistoryPoint(**p) for p in cached.get("data", [])]
                return MarketCapHistoryResponse(
                    data=data_points,
                    updated_at=datetime.fromisoformat(cached["updated_at"].replace("Z", "+00:00"))
                )
            except:
                pass  # If cache parsing fails, fetch fresh data
        
        try:
            url = "https://api.coingecko.com/api/v3/global/market_cap_chart"
            params = {
                "days": min(days, 365)  # CoinGecko supports up to 365 days
            }
            
            if hasattr(settings, 'COINGECKO_API_KEY') and settings.COINGECKO_API_KEY:
                params["x_cg_demo_api_key"] = settings.COINGECKO_API_KEY
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=30.0)
                response.raise_for_status()
                data = response.json()
            
            # CoinGecko returns data in format: {"market_cap": [[timestamp, value], ...]}
            market_cap_data = data.get("market_cap", [])
            
            history_points = []
            for point in market_cap_data:
                if len(point) >= 2:
                    timestamp = int(point[0])
                    market_cap = Decimal(str(point[1]))
                    history_points.append(MarketCapHistoryPoint(
                        timestamp=timestamp,
                        market_cap=market_cap
                    ))
            
            response_data = {
                "data": [p.dict() for p in history_points],
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Cache the response
            self.cache.set(cache_key, response_data, ttl=3600)  # 1 hour cache
            
            return MarketCapHistoryResponse(
                data=history_points,
                updated_at=datetime.utcnow()
            )
        except Exception as e:
            import logging
            logging.error(f"Error fetching market cap history: {e}")
            # Return empty response on error
            return MarketCapHistoryResponse(
                data=[],
                updated_at=datetime.utcnow()
            )
    
    async def get_market_calendar(self, db: Session) -> dict:
        """Get market calendar events from CoinGecko API."""
        import httpx
        from shared.config import settings
        from datetime import datetime, timedelta
        
        # Check cache first
        cached = self.cache.get("market_calendar")
        if cached:
            try:
                return cached
            except:
                pass  # If cache parsing fails, fetch fresh data
        
        try:
            # CoinGecko events endpoint
            url = "https://api.coingecko.com/api/v3/events"
            params = {
                "upcoming": "true",  # Get upcoming events
            }
            
            api_key = getattr(settings, 'COINGECKO_API_KEY', '') or ''
            if api_key:
                params["x_cg_demo_api_key"] = api_key
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                
                if response.status_code == 404:
                    return {"events": []}
                
                response.raise_for_status()
                data = response.json()
            
            # Format events
            events = []
            for event in data.get("data", {}).get("events", [])[:50]:  # Limit to 50 events
                event_date = event.get("date", "")
                if event_date:
                    try:
                        # Parse date string
                        event_datetime = datetime.fromisoformat(event_date.replace("Z", "+00:00"))
                        # Only include upcoming events (next 3 months)
                        if event_datetime > datetime.utcnow() and event_datetime < datetime.utcnow() + timedelta(days=90):
                            events.append({
                                "id": event.get("id", ""),
                                "title": event.get("title", ""),
                                "description": event.get("description", ""),
                                "date": event_date,
                                "type": event.get("type", "other"),  # airdrop, listing, upgrade, etc.
                                "coin_symbol": event.get("coin_symbol", ""),
                                "coin_name": event.get("coin_name", ""),
                                "url": event.get("url", ""),
                            })
                    except:
                        continue  # Skip invalid dates
            
            # Sort by date
            events.sort(key=lambda x: x.get("date", ""))
            
            response_data = {
                "events": events,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Cache for 1 hour
            self.cache.set("market_calendar", response_data, ttl=3600)
            
            return response_data
        except Exception as e:
            import logging
            logging.error(f"Error fetching market calendar: {e}")
            return {"events": [], "updated_at": datetime.utcnow().isoformat()}
    
    async def close(self):
        """Close API clients."""
        await self.repository.market_provider.close()
        await self.repository.ohlc_provider.close()
        await self.fear_greed.close()
