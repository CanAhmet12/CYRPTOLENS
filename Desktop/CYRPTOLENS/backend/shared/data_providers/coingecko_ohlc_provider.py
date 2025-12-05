"""
CoinGecko OHLC Data Provider.
Implements OhlcDataProvider interface as fallback when Binance is blocked.
Following CryptoLens Data Architecture Specification.
"""
import httpx
from typing import List
from decimal import Decimal
from datetime import datetime
from .interfaces import OhlcDataProvider, Timeframe, Candle
from .symbol_resolver import SymbolResolver
from shared.config import settings


class CoinGeckoOhlcDataProvider(OhlcDataProvider):
    """CoinGecko implementation of OhlcDataProvider (fallback for Binance)."""
    
    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.client = httpx.AsyncClient(timeout=30.0)
        self.api_key = getattr(settings, 'COINGECKO_API_KEY', '') or ''
        self.symbol_resolver = SymbolResolver()
    
    def _map_timeframe_to_days(self, timeframe: Timeframe, limit: int) -> int:
        """Map timeframe to number of days for CoinGecko API."""
        # CoinGecko OHLC endpoint uses days parameter
        # We need to calculate days based on timeframe and limit
        days_per_candle = {
            Timeframe.MINUTE_1: 1 / (24 * 60),  # 1 minute
            Timeframe.MINUTE_15: 15 / (24 * 60),  # 15 minutes
            Timeframe.HOUR_1: 1 / 24,  # 1 hour
            Timeframe.HOUR_4: 4 / 24,  # 4 hours
            Timeframe.DAY_1: 1,  # 1 day
        }
        
        days_per = days_per_candle.get(timeframe, 1)
        total_days = int(days_per * limit)
        
        # CoinGecko limits: min 1 day, max 365 days
        return max(1, min(total_days, 365))
    
    def _get_interval_from_timeframe(self, timeframe: Timeframe) -> str:
        """Get CoinGecko interval from timeframe."""
        # CoinGecko OHLC returns daily data, we'll aggregate if needed
        return "daily"  # CoinGecko only supports daily OHLC
    
    async def get_ohlc_for_symbol(
        self,
        symbol: str,
        timeframe: Timeframe,
        limit: int = 500
    ) -> List[Candle]:
        """Get OHLC candles for a symbol and timeframe from CoinGecko."""
        try:
            # Get CoinGecko ID for symbol
            gecko_id = self.symbol_resolver.get_gecko_id(symbol)
            if not gecko_id:
                return []
            
            # Calculate days parameter
            days = self._map_timeframe_to_days(timeframe, limit)
            
            url = f"{self.base_url}/coins/{gecko_id}/ohlc"
            params = {
                "vs_currency": "usd",
                "days": days,
            }
            
            if self.api_key:
                params["x_cg_demo_api_key"] = self.api_key
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            candles = []
            for item in data:
                # CoinGecko OHLC format: [timestamp_ms, open, high, low, close]
                if len(item) >= 5:
                    timestamp_ms = item[0]
                    open_price = Decimal(str(item[1]))
                    high_price = Decimal(str(item[2]))
                    low_price = Decimal(str(item[3]))
                    close_price = Decimal(str(item[4]))
                    
                    candles.append(Candle(
                        timestamp=datetime.fromtimestamp(timestamp_ms / 1000),
                        open=open_price,
                        high=high_price,
                        low=low_price,
                        close=close_price,
                        volume=Decimal(0)  # CoinGecko OHLC doesn't include volume
                    ))
            
            # If we need more granular data (hourly, 4h, etc.), we'll need to aggregate
            # For now, return daily candles
            return candles
            
        except Exception as e:
            # Return empty list on error
            return []
    
    async def is_symbol_supported(self, symbol: str) -> bool:
        """Check if symbol is supported by CoinGecko."""
        try:
            gecko_id = self.symbol_resolver.get_gecko_id(symbol)
            if not gecko_id:
                return False
            
            # Try to get price to verify symbol exists
            url = f"{self.base_url}/simple/price"
            params = {
                "ids": gecko_id,
                "vs_currencies": "usd",
            }
            
            if self.api_key:
                params["x_cg_demo_api_key"] = self.api_key
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return gecko_id in data
        except Exception:
            # On error, assume not supported
            return False
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

