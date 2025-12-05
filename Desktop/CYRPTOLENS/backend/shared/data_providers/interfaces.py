"""
Data Provider Interfaces.
Following CryptoLens Data Architecture Specification.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from decimal import Decimal
from datetime import datetime
from enum import Enum


class Timeframe(str, Enum):
    """OHLC Timeframe enumeration."""
    MINUTE_1 = "1m"
    MINUTE_15 = "15m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAY_1 = "1d"


class CoinMeta:
    """Coin metadata."""
    def __init__(
        self,
        symbol: str,
        name: str,
        gecko_id: str,
        binance_pair: Optional[str] = None
    ):
        self.symbol = symbol
        self.name = name
        self.gecko_id = gecko_id
        self.binance_pair = binance_pair


class PriceData:
    """Price data for a coin."""
    def __init__(
        self,
        symbol: str,
        price: Decimal,
        change_24h: Decimal,
        market_cap: Optional[Decimal] = None,
        volume_24h: Optional[Decimal] = None
    ):
        self.symbol = symbol
        self.price = price
        self.change_24h = change_24h
        self.market_cap = market_cap
        self.volume_24h = volume_24h


class MarketOverview:
    """Market overview data."""
    def __init__(
        self,
        total_market_cap: Decimal,
        total_volume_24h: Decimal,
        btc_dominance: Decimal,
        eth_dominance: Decimal,
        market_cap_change_24h: Decimal
    ):
        self.total_market_cap = total_market_cap
        self.total_volume_24h = total_volume_24h
        self.btc_dominance = btc_dominance
        self.eth_dominance = eth_dominance
        self.market_cap_change_24h = market_cap_change_24h


class Candle:
    """OHLC Candle data."""
    def __init__(
        self,
        timestamp: datetime,
        open: Decimal,
        high: Decimal,
        low: Decimal,
        close: Decimal,
        volume: Decimal
    ):
        self.timestamp = timestamp
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume


class MarketDataProvider(ABC):
    """Interface for market data providers (CoinGecko)."""
    
    @abstractmethod
    async def get_coin_list(self, limit: int = 250) -> List[CoinMeta]:
        """Get list of coins with metadata."""
        pass
    
    @abstractmethod
    async def get_market_overview(self) -> MarketOverview:
        """Get global market overview."""
        pass
    
    @abstractmethod
    async def get_prices_for_symbols(self, symbols: List[str]) -> Dict[str, PriceData]:
        """Get prices for a list of coin symbols."""
        pass
    
    @abstractmethod
    async def get_trending_coins(self) -> List[CoinMeta]:
        """Get trending coins."""
        pass


class OhlcDataProvider(ABC):
    """Interface for OHLC data providers (Binance)."""
    
    @abstractmethod
    async def get_ohlc_for_symbol(
        self,
        symbol: str,
        timeframe: Timeframe,
        limit: int = 500
    ) -> List[Candle]:
        """Get OHLC candles for a symbol and timeframe."""
        pass
    
    @abstractmethod
    async def is_symbol_supported(self, symbol: str) -> bool:
        """Check if symbol is supported by this provider."""
        pass

