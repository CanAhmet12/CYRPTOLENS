"""
Real-time Data Service
Main service providing stable, near real-time data with graceful fallbacks.
"""
import logging
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from .binance_realtime_client import BinanceRealtimeClient
from .market_polling_service import MarketPollingService
from shared.data_providers.binance_provider import BinanceOhlcDataProvider
from shared.data_providers.interfaces import Timeframe, Candle
from shared.analytics.indicators.rsi import calculate_rsi
from shared.analytics.indicators.macd import calculate_macd
from shared.analytics.indicators.ema import calculate_ema
from shared.analytics.indicators.volatility import calculate_volatility

logger = logging.getLogger(__name__)


class RealtimeDataService:
    """
    Main real-time data service.
    Provides clean API with last-known-value behavior.
    """

    STALE_THRESHOLD_SECONDS = 300  # 5 minutes

    def __init__(self):
        self.binance_client = BinanceRealtimeClient()
        self.market_polling = MarketPollingService()
        self.ohlc_provider = BinanceOhlcDataProvider()
        self._initialized = False
        self._ohlc_cache: Dict[str, Dict] = {}
        self._ohlc_fetch_times: Dict[str, datetime] = {}

    async def initialize(self, symbols: list = None):
        """
        Initialize the service and start background tasks.

        Args:
            symbols: List of symbols to subscribe to (default: top coins)
        """
        if self._initialized:
            return

        if symbols is None:
            symbols = ['BTC', 'ETH', 'SOL', 'BNB', 'ADA', 'XRP', 'DOGE', 'DOT', 'MATIC', 'AVAX']

        await self.market_polling.start()

        for symbol in symbols:
            await self.binance_client.subscribe_ticker(symbol)

        self._initialized = True
        logger.info("Real-time data service initialized")

    async def shutdown(self):
        """Shutdown the service and cleanup resources."""
        await self.binance_client.close_all()
        await self.market_polling.stop()
        try:
            await self.ohlc_provider.close()
        except Exception:
            pass
        self._initialized = False
        logger.info("Real-time data service shut down")

    def get_latest_ticker(self, symbol: str) -> Dict:
        """
        Get latest ticker data for a symbol.
        Returns last known value if available, never None.
        """
        ticker = self.binance_client.get_latest_ticker(symbol)

        if ticker:
            last_updated = datetime.fromisoformat(ticker['lastUpdated'])
            age_seconds = (datetime.utcnow() - last_updated).total_seconds()
            is_stale = age_seconds > self.STALE_THRESHOLD_SECONDS

            return {
                'price': ticker['price'],
                'change24h': ticker['change24h'],
                'volume24h': ticker.get('volume24h', 0),
                'high24h': ticker.get('high24h', 0),
                'low24h': ticker.get('low24h', 0),
                'lastUpdated': ticker['lastUpdated'],
                'isStale': is_stale
            }

        return {
            'price': 0.0,
            'change24h': 0.0,
            'volume24h': 0.0,
            'high24h': 0.0,
            'low24h': 0.0,
            'lastUpdated': None,
            'isStale': True
        }

    def get_market_overview(self) -> Dict:
        """Get market overview with last-known values."""
        return self.market_polling.get_market_overview()

    def get_all_tickers(self) -> Dict[str, Dict]:
        """Get all cached ticker data."""
        all_tickers = self.binance_client.get_all_tickers()
        result = {}

        for symbol, ticker in all_tickers.items():
            last_updated = datetime.fromisoformat(ticker['lastUpdated'])
            age_seconds = (datetime.utcnow() - last_updated).total_seconds()
            is_stale = age_seconds > self.STALE_THRESHOLD_SECONDS

            result[symbol] = {
                'price': ticker['price'],
                'change24h': ticker['change24h'],
                'volume24h': ticker.get('volume24h', 0),
                'high24h': ticker.get('high24h', 0),
                'low24h': ticker.get('low24h', 0),
                'lastUpdated': ticker['lastUpdated'],
                'isStale': is_stale
            }

        return result

    async def subscribe_ticker(self, symbol: str, callback=None):
        """Subscribe to ticker updates for a symbol."""
        await self.binance_client.subscribe_ticker(symbol, callback)
    
    def get_ticker_update_callback(self):
        """Get callback function for ticker updates to broadcast via WebSocket."""
        # This will be set by main.py when WebSocket manager is available
        return None

    async def get_coin_data(self, symbol: str, timeframe: str = "1h") -> Dict:
        """
        Get real-time data for a coin (ticker + OHLC + indicators).
        Always returns last known values.
        """
        ticker = self.get_latest_ticker(symbol)
        ohlc_payload, candles = await self._get_ohlc_with_cache(symbol, timeframe)
        indicators = self._calculate_indicators(candles) if candles else {}

        last_updated = ticker.get("lastUpdated") or ohlc_payload.get("lastUpdated")
        is_stale = ticker.get("isStale", True) if ticker else True
        if ohlc_payload.get("isStale"):
            is_stale = True

        return {
            "ticker": ticker,
            "ohlc": ohlc_payload.get("candles", []),
            "indicators": indicators,
            "lastUpdated": last_updated,
            "isStale": is_stale,
        }

    def _map_timeframe(self, timeframe: str) -> Timeframe:
        normalized = timeframe.lower()
        mapping = {
            "1m": Timeframe.MINUTE_1,
            "15m": Timeframe.MINUTE_15,
            "1h": Timeframe.HOUR_1,
            "4h": Timeframe.HOUR_4,
            "1d": Timeframe.DAY_1,
            "1w": Timeframe.HOUR_4,
            "1month": Timeframe.DAY_1,
            "1mo": Timeframe.DAY_1,
        }
        if normalized in mapping:
            return mapping[normalized]
        if normalized.endswith("h") and normalized[:-1].isdigit():
            hours = int(normalized[:-1])
            if hours <= 1:
                return Timeframe.HOUR_1
            if hours <= 4:
                return Timeframe.HOUR_4
            return Timeframe.DAY_1
        return Timeframe.HOUR_1

    def _get_refresh_interval(self, timeframe: str) -> int:
        normalized = timeframe.lower()
        if normalized == "1m":
            return 15
        if normalized in ("5m", "15m"):
            return 20
        if normalized in ("1h", "4h"):
            return 45
        return 90

    async def _get_ohlc_with_cache(self, symbol: str, timeframe: str) -> Tuple[Dict, List[Candle]]:
        key = f"{symbol.upper()}:{timeframe.upper()}"
        now = datetime.utcnow()

        cached = self._ohlc_cache.get(key)
        last_fetch = self._ohlc_fetch_times.get(key)
        refresh_interval = self._get_refresh_interval(timeframe)

        if cached and last_fetch:
            age = (now - last_fetch).total_seconds()
            if age < refresh_interval:
                cached["isStale"] = False if age < refresh_interval else True
                return cached, cached.get("raw_candles", [])

        try:
            timeframe_enum = self._map_timeframe(timeframe)
            candles = await self.ohlc_provider.get_ohlc_for_symbol(
                symbol, timeframe_enum, limit=300
            )
            if candles:
                serialized = [self._candle_to_dict(c) for c in candles]
                payload = {
                    "candles": serialized,
                    "lastUpdated": now.isoformat(),
                    "isStale": False,
                    "raw_candles": candles,
                }
                self._ohlc_cache[key] = payload
                self._ohlc_fetch_times[key] = now
                return payload, candles
        except Exception as e:
            logger.error(f"Failed to fetch OHLC for {symbol} ({timeframe}): {e}")

        if cached:
            cached["isStale"] = True
            return cached, cached.get("raw_candles", [])

        return {
            "candles": [],
            "lastUpdated": None,
            "isStale": True,
            "raw_candles": [],
        }, []

    def _candle_to_dict(self, candle: Candle) -> Dict:
        return {
            "timestamp": int(candle.timestamp.timestamp() * 1000),
            "open": float(candle.open),
            "high": float(candle.high),
            "low": float(candle.low),
            "close": float(candle.close),
            "volume": float(candle.volume),
        }

    def _calculate_indicators(self, candles: List[Candle]) -> Dict:
        if not candles:
            return {}

        try:
            rsi_values = calculate_rsi(candles)
            macd_values = calculate_macd(candles)
            ema20 = calculate_ema(candles, 20)
            ema50 = calculate_ema(candles, 50)
            ema200 = calculate_ema(candles, 200)
            volatility = calculate_volatility(candles)

            def _last(values):
                if not values:
                    return None
                for value in reversed(values):
                    if value is not None:
                        return float(value)
                return None

            return {
                "rsi": _last(rsi_values),
                "macd": {
                    "line": _last(macd_values.get("macdLine")),
                    "signal": _last(macd_values.get("signalLine")),
                    "histogram": _last(macd_values.get("histogram")),
                },
                "ema": {
                    "ema20": _last(ema20),
                    "ema50": _last(ema50),
                    "ema200": _last(ema200),
                },
                "volatility": {
                    "sigma": float(volatility.get("sigma", Decimal(0))),
                    "score": float(volatility.get("normalizedScore", Decimal(0))),
                },
            }
        except Exception as e:
            logger.error(f"Indicator calculation failed: {e}")
            return {}

