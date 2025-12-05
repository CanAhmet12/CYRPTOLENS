"""
CoinGecko Market Data Provider.
Implements MarketDataProvider interface.
Following CryptoLens Data Architecture Specification.
"""
import httpx
from typing import List, Dict
from decimal import Decimal
from datetime import datetime
from .interfaces import MarketDataProvider, CoinMeta, PriceData, MarketOverview
from shared.config import settings


class CoinGeckoMarketDataProvider(MarketDataProvider):
    """CoinGecko implementation of MarketDataProvider."""
    
    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.client = httpx.AsyncClient(timeout=30.0)
        self.api_key = getattr(settings, 'COINGECKO_API_KEY', '') or ''
    
    async def get_coin_list(self, limit: int = 250) -> List[CoinMeta]:
        """Get list of coins with metadata."""
        try:
            url = f"{self.base_url}/coins/markets"
            params = {
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": min(limit, 250),
                "page": 1,
                "sparkline": False,
            }
            
            if self.api_key:
                params["x_cg_demo_api_key"] = self.api_key
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            coins = []
            for item in data:
                coins.append(CoinMeta(
                    symbol=item.get("symbol", "").upper(),
                    name=item.get("name", ""),
                    gecko_id=item.get("id", ""),
                    binance_pair=None  # Will be resolved by SymbolResolver
                ))
            
            return coins
        except Exception as e:
            # Return empty list on error
            return []
    
    async def get_market_overview(self) -> MarketOverview:
        """Get global market overview."""
        try:
            url = f"{self.base_url}/global"
            params = {}
            
            if self.api_key:
                params["x_cg_demo_api_key"] = self.api_key
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            global_data = data.get("data", {})
            market_cap = Decimal(str(global_data.get("total_market_cap", {}).get("usd", 0)))
            volume = Decimal(str(global_data.get("total_volume", {}).get("usd", 0)))
            btc_dominance = Decimal(str(global_data.get("market_cap_percentage", {}).get("btc", 0)))
            eth_dominance = Decimal(str(global_data.get("market_cap_percentage", {}).get("eth", 0)))
            
            # Market cap change 24h (approximate from active_cryptocurrencies change)
            market_cap_change_24h = Decimal(0)  # CoinGecko global doesn't provide this directly
            
            return MarketOverview(
                total_market_cap=market_cap,
                total_volume_24h=volume,
                btc_dominance=btc_dominance,
                eth_dominance=eth_dominance,
                market_cap_change_24h=market_cap_change_24h
            )
        except Exception as e:
            # Return default values on error
            return MarketOverview(
                total_market_cap=Decimal(0),
                total_volume_24h=Decimal(0),
                btc_dominance=Decimal(0),
                eth_dominance=Decimal(0),
                market_cap_change_24h=Decimal(0)
            )
    
    async def get_prices_for_symbols(self, symbols: List[str]) -> Dict[str, PriceData]:
        """Get prices for a list of coin symbols."""
        try:
            # Get gecko IDs for symbols (simplified - in production, use SymbolResolver)
            gecko_ids = [s.lower() for s in symbols]
            
            url = f"{self.base_url}/simple/price"
            params = {
                "ids": ",".join(gecko_ids),
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_market_cap": "true",
                "include_24hr_vol": "true",
            }
            
            if self.api_key:
                params["x_cg_demo_api_key"] = self.api_key
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            prices = {}
            for symbol in symbols:
                gecko_id = symbol.lower()
                if gecko_id in data:
                    coin_data = data[gecko_id]
                    prices[symbol.upper()] = PriceData(
                        symbol=symbol.upper(),
                        price=Decimal(str(coin_data.get("usd", 0))),
                        change_24h=Decimal(str(coin_data.get("usd_24h_change", 0) or 0)),
                        market_cap=Decimal(str(coin_data.get("usd_market_cap", 0) or 0)),
                        volume_24h=Decimal(str(coin_data.get("usd_24h_vol", 0) or 0))
                    )
            
            return prices
        except Exception as e:
            return {}
    
    async def get_trending_coins(self) -> List[CoinMeta]:
        """Get trending coins."""
        try:
            url = f"{self.base_url}/search/trending"
            params = {}
            
            if self.api_key:
                params["x_cg_demo_api_key"] = self.api_key
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            coins = []
            for item in data.get("coins", [])[:10]:  # Top 10 trending
                coin_data = item.get("item", {})
                coins.append(CoinMeta(
                    symbol=coin_data.get("symbol", "").upper(),
                    name=coin_data.get("name", ""),
                    gecko_id=coin_data.get("id", ""),
                    binance_pair=None
                ))
            
            return coins
        except Exception as e:
            return []
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

