"""
Binance OHLC Data Provider.
Implements OhlcDataProvider interface.
Following CryptoLens Data Architecture Specification.
"""
import httpx
from typing import List
from decimal import Decimal
from datetime import datetime
from .interfaces import OhlcDataProvider, Timeframe, Candle
from shared.config import settings


class BinanceOhlcDataProvider(OhlcDataProvider):
    """Binance implementation of OhlcDataProvider."""
    
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3"
        self.client = httpx.AsyncClient(timeout=30.0)
        self.api_key = getattr(settings, 'BINANCE_API_KEY', '') or ''
        self.api_secret = getattr(settings, 'BINANCE_API_SECRET', '') or ''
    
    def _map_timeframe(self, timeframe: Timeframe) -> str:
        """Map internal timeframe to Binance interval."""
        mapping = {
            Timeframe.MINUTE_1: "1m",
            Timeframe.MINUTE_15: "15m",
            Timeframe.HOUR_1: "1h",
            Timeframe.HOUR_4: "4h",
            Timeframe.DAY_1: "1d",
        }
        return mapping.get(timeframe, "1d")
    
    def _symbol_to_pair(self, symbol: str) -> str:
        """Convert symbol to Binance trading pair."""
        # Assume USDT pairs
        return f"{symbol.upper()}USDT"
    
    async def get_ohlc_for_symbol(
        self,
        symbol: str,
        timeframe: Timeframe,
        limit: int = 500
    ) -> List[Candle]:
        """Get OHLC candles for a symbol and timeframe."""
        try:
            pair = self._symbol_to_pair(symbol)
            interval = self._map_timeframe(timeframe)
            
            url = f"{self.base_url}/klines"
            params = {
                "symbol": pair,
                "interval": interval,
                "limit": min(limit, 1000),  # Binance max is 1000
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            candles = []
            for kline in data:
                # Binance kline format: [timestamp, open, high, low, close, volume, ...]
                candles.append(Candle(
                    timestamp=datetime.fromtimestamp(kline[0] / 1000),
                    open=Decimal(str(kline[1])),
                    high=Decimal(str(kline[2])),
                    low=Decimal(str(kline[3])),
                    close=Decimal(str(kline[4])),
                    volume=Decimal(str(kline[5]))
                ))
            
            return candles
        except Exception as e:
            # Return empty list on error
            return []
    
    async def get_ticker_price(self, symbol: str) -> Decimal:
        """Get current ticker price for a symbol."""
        try:
            pair = self._symbol_to_pair(symbol)
            url = f"{self.base_url}/ticker/price"
            params = {"symbol": pair}
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return Decimal(str(data.get("price", 0)))
        except Exception:
            return Decimal(0)
    
    async def is_symbol_supported(self, symbol: str) -> bool:
        """Check if symbol is supported by Binance."""
        try:
            pair = self._symbol_to_pair(symbol)
            url = f"{self.base_url}/exchangeInfo"
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
            
            symbols = [s["symbol"] for s in data.get("symbols", [])]
            return pair in symbols
        except Exception:
            # On error, assume not supported
            return False
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

