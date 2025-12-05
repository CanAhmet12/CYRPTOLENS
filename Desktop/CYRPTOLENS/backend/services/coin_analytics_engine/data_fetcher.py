"""
Data fetcher for coin analytics.
Fetches OHLC data from Binance for technical analysis.
Following CryptoLens Data Architecture Specification.
"""
from typing import List
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select
from shared.models import MarketCache
from shared.data_providers.binance_provider import BinanceOhlcDataProvider
from shared.data_providers.interfaces import Timeframe
from shared.data_providers.symbol_resolver import SymbolResolver
from shared.config import settings


class CoinDataFetcher:
    """Fetches OHLC data from Binance for technical analysis."""
    
    def __init__(self):
        self.ohlc_provider = BinanceOhlcDataProvider()
        self.symbol_resolver = SymbolResolver()
    
    async def get_historical_prices(
        self, coin_symbol: str, days: int = 200
    ) -> List[Decimal]:
        """
        Fetch historical prices for a coin from Binance OHLC with CoinGecko fallback.
        Returns list of close prices (most recent last).
        Following CryptoLens Data Architecture Specification.
        """
        try:
            # Map days to timeframe (approximate)
            # For 200 days, use 1d timeframe
            timeframe = Timeframe.DAY_1
            limit = min(days, 500)
            
            # Try Binance first
            candles = []
            if self.symbol_resolver.is_binance_supported(coin_symbol):
                try:
                    candles = await self.ohlc_provider.get_ohlc_for_symbol(
                        coin_symbol,
                        timeframe,
                        limit=limit
                    )
                except Exception:
                    # Binance failed, try CoinGecko
                    pass
            
            # If Binance failed, try CoinGecko fallback
            if not candles:
                try:
                    from shared.data_providers.coingecko_ohlc_provider import CoinGeckoOhlcDataProvider
                    coingecko_ohlc = CoinGeckoOhlcDataProvider()
                    candles = await coingecko_ohlc.get_ohlc_for_symbol(
                        coin_symbol,
                        timeframe,
                        limit=limit
                    )
                except Exception:
                    pass
            
            # Extract close prices
            prices = [candle.close for candle in candles]
            
            return prices
        except Exception as e:
            # Fallback: return empty list
            return []
    
    async def get_chart_data(
        self, coin_symbol: str, timeframe: str = "1D"
    ) -> List[dict]:
        """
        Fetch chart data for a specific timeframe from Binance OHLC with CoinGecko fallback.
        Returns list of OHLC dictionaries with full candlestick data.
        
        Timeframes: 1H, 1D, 1W, 1M, 1Y
        Following CryptoLens Data Architecture Specification.
        """
        try:
            # Map timeframe string to Timeframe enum
            timeframe_map = {
                "1H": Timeframe.HOUR_1,
                "4H": Timeframe.HOUR_4,
                "1D": Timeframe.DAY_1,
                "1W": Timeframe.DAY_1,  # Use 1d for weekly
                "1M": Timeframe.DAY_1,  # Use 1d for monthly
                "1Y": Timeframe.DAY_1,  # Use 1d for yearly
            }
            
            # Map timeframe to limit
            limit_map = {
                "1H": 168,  # 7 days of hourly data
                "4H": 168,  # 28 days of 4h data
                "1D": 365,  # 1 year of daily data
                "1W": 104,  # 2 years of weekly data (using daily candles)
                "1M": 365,  # 1 year of monthly data (using daily candles)
                "1Y": 365,  # 1 year of yearly data (using daily candles)
            }
            
            binance_timeframe = timeframe_map.get(timeframe, Timeframe.DAY_1)
            limit = limit_map.get(timeframe, 365)
            
            # Try Binance first
            candles = []
            if self.symbol_resolver.is_binance_supported(coin_symbol):
                try:
                    candles = await self.ohlc_provider.get_ohlc_for_symbol(
                        coin_symbol,
                        binance_timeframe,
                        limit=min(limit, 1000)  # Binance max is 1000
                    )
                except Exception:
                    # Binance failed, try CoinGecko
                    pass
            
            # If Binance failed, try CoinGecko fallback
            if not candles:
                try:
                    from shared.data_providers.coingecko_ohlc_provider import CoinGeckoOhlcDataProvider
                    coingecko_ohlc = CoinGeckoOhlcDataProvider()
                    candles = await coingecko_ohlc.get_ohlc_for_symbol(
                        coin_symbol,
                        binance_timeframe,
                        limit=limit
                    )
                except Exception:
                    pass
            
            # Convert to OHLC chart data format (TradingView compatible)
            chart_data = []
            for candle in candles:
                chart_data.append({
                    "timestamp": int(candle.timestamp.timestamp() * 1000),  # Unix timestamp in ms
                    "open": float(candle.open),
                    "high": float(candle.high),
                    "low": float(candle.low),
                    "close": float(candle.close),
                    "volume": float(candle.volume) if hasattr(candle, 'volume') else 0.0,
                    "price": float(candle.close)  # Keep for backward compatibility
                })
            
            return chart_data
        except Exception as e:
            # Fallback: return empty list
            return []
    
    def get_current_price_from_db(
        self, db: Session, coin_symbol: str
    ) -> Decimal:
        """Get current price from market_cache table."""
        stmt = select(MarketCache).where(
            MarketCache.symbol == coin_symbol.upper()
        )
        result = db.execute(stmt)
        market_data = result.scalar_one_or_none()
        if market_data:
            return market_data.price
        return Decimal(0)
    
    async def close(self):
        """Close OHLC provider."""
        await self.ohlc_provider.close()

