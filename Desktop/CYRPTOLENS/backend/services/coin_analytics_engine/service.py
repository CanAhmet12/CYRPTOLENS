"""
Main business logic service for Coin Analytics Engine.
Orchestrates technical indicator calculations.
Following Indicator & Analytics Engine Specification exactly.
"""
from typing import List
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
from shared.analytics import (
    Candle as AnalyticsCandle,
    calculate_rsi,
    calculate_macd,
    calculate_ema,
    calculate_volatility,
    calculate_trend_score,
    calculate_momentum,
)
from shared.repositories.crypto_data_repository import CryptoDataRepository
from shared.data_providers.coingecko_provider import CoinGeckoMarketDataProvider
from shared.data_providers.binance_provider import BinanceOhlcDataProvider
from .trend_engine import TrendEngine
from .data_fetcher import CoinDataFetcher
from .models import (
    CoinOverviewResponse,
    RSIResponse,
    MACDResponse,
    SupportResistanceResponse,
    ChartDataResponse,
    CoinDashboardResponse,
)
from shared.redis_client import get_redis
import json
from datetime import datetime, timedelta


class CoinAnalyticsService:
    """
    Main service for coin analytics operations.
    Following Indicator & Analytics Engine Specification exactly.
    Uses pure indicator functions from shared.analytics module.
    """
    
    def __init__(self):
        # Initialize repository for data access (following architecture spec)
        market_provider = CoinGeckoMarketDataProvider()
        ohlc_provider = BinanceOhlcDataProvider()
        self.repository = CryptoDataRepository(market_provider, ohlc_provider)
        
        self.trend_engine = TrendEngine()
        self.data_fetcher = CoinDataFetcher()
        
        # Initialize premium service
        from .premium_service import CoinPremiumService
        self.premium_service = CoinPremiumService()
    
    async def get_coin_overview(
        self, db: Session, coin_symbol: str, coin_id: str = None
    ) -> CoinOverviewResponse:
        """
        Get complete coin analytics overview.
        Following Indicator & Analytics Engine Specification exactly.
        
        Flow:
        1. Get OHLC candles from Binance (via CryptoDataRepository)
        2. Convert to AnalyticsCandle format
        3. Calculate indicators using pure functions
        4. Return composed response
        """
        # Get current price from database cache, fallback to Binance if not available
        current_price = self.data_fetcher.get_current_price_from_db(
            db, coin_symbol
        )
        
        # Normalize symbol (remove USDT suffix if present)
        normalized_symbol = coin_symbol.replace("USDT", "").replace("usdt", "").upper()
        
        # If price not in DB, try to get from Binance directly, then CoinGecko
        if current_price == 0:
            try:
                from shared.data_providers.binance_provider import BinanceOhlcDataProvider
                binance_provider = BinanceOhlcDataProvider()
                # Get latest ticker price (use normalized symbol)
                ticker_price = await binance_provider.get_ticker_price(normalized_symbol)
                if ticker_price and ticker_price > 0:
                    current_price = ticker_price
            except Exception as e:
                # Binance might be blocked, try CoinGecko
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(f"Binance ticker price fetch failed for {normalized_symbol}: {e}")
            
            # Fallback to CoinGecko if Binance failed
            if current_price == 0:
                try:
                    prices = await self.repository.market_provider.get_prices_for_symbols([normalized_symbol])
                    if normalized_symbol in prices:
                        current_price = Decimal(str(prices[normalized_symbol].price))
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.debug(f"CoinGecko price fetch failed for {normalized_symbol}: {e}")
        
        # Normalize symbol (remove USDT suffix if present)
        normalized_symbol = coin_symbol.replace("USDT", "").replace("usdt", "").upper()
        
        # Get OHLC candles from Binance via repository (following architecture spec)
        from shared.data_providers.interfaces import Timeframe
        provider_candles = await self.repository.get_ohlc_for_analytics(
            normalized_symbol,
            timeframe=Timeframe.DAY_1,
            limit=500
        )
        
        # If no candles from Binance (geographic restriction), try CoinGecko as fallback
        if not provider_candles:
            try:
                # CoinGecko doesn't provide OHLC directly, but we can get price history
                # For now, we'll use CoinGecko to get current price at least
                prices = await self.repository.market_provider.get_prices_for_symbols([normalized_symbol])
                if normalized_symbol in prices and current_price == 0:
                    current_price = Decimal(str(prices[normalized_symbol].price))
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(f"CoinGecko fallback price fetch failed for {normalized_symbol}: {e}")
        
        # Convert to analytics candles
        analytics_candles = [
            AnalyticsCandle.from_provider_candle(c) for c in provider_candles
        ]
        
        # If no candles, try to get at least current price from CoinGecko
        if not analytics_candles or len(analytics_candles) < 14:
            # Try to get current price from CoinGecko (Binance is blocked)
            if current_price == 0:
                try:
                    prices = await self.repository.market_provider.get_prices_for_symbols([normalized_symbol])
                    if normalized_symbol in prices:
                        current_price = Decimal(str(prices[normalized_symbol].price))
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.debug(f"CoinGecko price fetch failed for {normalized_symbol}: {e}")
            
            # If still no price, try to get from latest OHLC candle if available
            if current_price == 0 and provider_candles:
                current_price = provider_candles[-1].close
            
            # Return minimal response if no data
            return CoinOverviewResponse(
                coin_symbol=coin_symbol.upper(),
                current_price=current_price if current_price > 0 else Decimal(0),
                rsi=Decimal(50),
                rsi_interpretation="neutral",
                macd=Decimal(0),
                macd_signal=Decimal(0),
                macd_histogram=Decimal(0),
                macd_interpretation="neutral",
                ema20=current_price if current_price > 0 else Decimal(0),
                ema50=current_price if current_price > 0 else Decimal(0),
                ema200=current_price if current_price > 0 else Decimal(0),
                ema_alignment="neutral",
                volatility=Decimal(0),
                momentum=Decimal(0),
                support_levels=[],
                resistance_levels=[],
                trend_direction="neutral",
                trend_strength=0,
                trend_score=Decimal(50),
                timestamp=datetime.utcnow()
            )
        
        # Calculate indicators using pure functions (following specification)
        # RSI
        rsi_list = calculate_rsi(analytics_candles)
        rsi = rsi_list[-1] if rsi_list and rsi_list[-1] is not None else Decimal(50)
        rsi_interpretation = self._interpret_rsi(rsi)
        
        # MACD
        macd_data = calculate_macd(analytics_candles)
        macd_line = macd_data.get("macdLine", [])
        signal_line = macd_data.get("signalLine", [])
        histogram = macd_data.get("histogram", [])
        
        # Get last non-None values
        macd_value = Decimal(0)
        signal_value = Decimal(0)
        histogram_value = Decimal(0)
        
        for val in reversed(macd_line):
            if val is not None:
                macd_value = val
                break
        
        for val in reversed(signal_line):
            if val is not None:
                signal_value = val
                break
        
        for val in reversed(histogram):
            if val is not None:
                histogram_value = val
                break
        
        macd_interpretation = self._interpret_macd({
            "macd": macd_value,
            "signal": signal_value,
            "histogram": histogram_value
        })
        
        # EMAs
        ema20_list = calculate_ema(analytics_candles, 20)
        ema50_list = calculate_ema(analytics_candles, 50)
        ema200_list = calculate_ema(analytics_candles, 200)
        
        ema20 = ema20_list[-1] if ema20_list else current_price
        ema50 = ema50_list[-1] if ema50_list else current_price
        ema200 = ema200_list[-1] if ema200_list else current_price
        
        ema_alignment = self._interpret_ema_alignment(ema20, ema50, ema200)
        
        # Volatility
        vol_data = calculate_volatility(analytics_candles)
        volatility = vol_data.get("normalizedScore", Decimal(0)) * Decimal(100)  # Convert to 0-100
        
        # Momentum
        momentum_data = calculate_momentum(analytics_candles)
        momentum = momentum_data.get("momentumScore", Decimal(50))
        
        # Trend Score (using new analytics engine)
        trend_data = calculate_trend_score(
            analytics_candles,
            ema20=ema20,
            ema50=ema50,
            ema200=ema200,
            macd_histogram=histogram_value,
            rsi=rsi
        )
        trend_score = trend_data.get("trendScore", Decimal(50))
        trend_direction = trend_data.get("trendLabel", "neutral")
        
        # Trend strength (0-10 scale from trend_score)
        trend_strength = int(float(trend_score) / 10)
        
        # Support/Resistance (keep existing implementation for now)
        from .technical_indicators import TechnicalIndicators
        temp_indicators = TechnicalIndicators()
        closes = [c.close for c in analytics_candles]
        levels = temp_indicators.detect_support_resistance(closes)
        
        return CoinOverviewResponse(
            coin_symbol=normalized_symbol,
            current_price=current_price,
            rsi=rsi,
            rsi_interpretation=rsi_interpretation,
            macd=macd_value,
            macd_signal=signal_value,
            macd_histogram=histogram_value,
            macd_interpretation=macd_interpretation,
            ema20=ema20,
            ema50=ema50,
            ema200=ema200,
            ema_alignment=ema_alignment,
            volatility=volatility,
            momentum=momentum,
            support_levels=levels["support_levels"],
            resistance_levels=levels["resistance_levels"],
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            trend_score=trend_score,
            timestamp=datetime.utcnow()
        )
    
    async def get_rsi(
        self, db: Session, coin_symbol: str, coin_id: str = None
    ) -> RSIResponse:
        """
        Get RSI for a coin.
        Following Indicator & Analytics Engine Specification.
        """
        # Get OHLC candles from Binance via repository
        from shared.data_providers.interfaces import Timeframe
        provider_candles = await self.repository.get_ohlc_for_analytics(
            coin_symbol,
            timeframe=Timeframe.DAY_1,
            limit=500
        )
        
        # Convert to analytics candles
        analytics_candles = [
            AnalyticsCandle.from_provider_candle(c) for c in provider_candles
        ]
        
        if not analytics_candles or len(analytics_candles) < 15:
            return RSIResponse(
                coin_symbol=coin_symbol.upper(),
                rsi=Decimal(50),
                interpretation="neutral",
                timestamp=datetime.utcnow()
            )
        
        # Calculate RSI using pure function
        rsi_list = calculate_rsi(analytics_candles)
        rsi = rsi_list[-1] if rsi_list and rsi_list[-1] is not None else Decimal(50)
        interpretation = self._interpret_rsi(rsi)
        
        return RSIResponse(
            coin_symbol=coin_symbol.upper(),
            rsi=rsi,
            interpretation=interpretation,
            timestamp=datetime.utcnow()
        )
    
    async def get_macd(
        self, db: Session, coin_symbol: str, coin_id: str = None
    ) -> MACDResponse:
        """
        Get MACD for a coin.
        Following Indicator & Analytics Engine Specification.
        """
        # Get OHLC candles from Binance via repository
        from shared.data_providers.interfaces import Timeframe
        provider_candles = await self.repository.get_ohlc_for_analytics(
            coin_symbol,
            timeframe=Timeframe.DAY_1,
            limit=500
        )
        
        # Convert to analytics candles
        analytics_candles = [
            AnalyticsCandle.from_provider_candle(c) for c in provider_candles
        ]
        
        if not analytics_candles or len(analytics_candles) < 35:
            return MACDResponse(
                coin_symbol=coin_symbol.upper(),
                macd=Decimal(0),
                signal=Decimal(0),
                histogram=Decimal(0),
                interpretation="neutral",
                timestamp=datetime.utcnow()
            )
        
        # Calculate MACD using pure function
        macd_data = calculate_macd(analytics_candles)
        
        # Get last non-None values
        macd_value = Decimal(0)
        signal_value = Decimal(0)
        histogram_value = Decimal(0)
        
        for val in reversed(macd_data.get("macdLine", [])):
            if val is not None:
                macd_value = val
                break
        
        for val in reversed(macd_data.get("signalLine", [])):
            if val is not None:
                signal_value = val
                break
        
        for val in reversed(macd_data.get("histogram", [])):
            if val is not None:
                histogram_value = val
                break
        
        interpretation = self._interpret_macd({
            "macd": macd_value,
            "signal": signal_value,
            "histogram": histogram_value
        })
        
        return MACDResponse(
            coin_symbol=coin_symbol.upper(),
            macd=macd_value,
            signal=signal_value,
            histogram=histogram_value,
            interpretation=interpretation,
            timestamp=datetime.utcnow()
        )
    
    async def get_support_resistance(
        self, db: Session, coin_symbol: str, coin_id: str = None
    ) -> SupportResistanceResponse:
        """Get support and resistance levels for a coin."""
        current_price = self.data_fetcher.get_current_price_from_db(
            db, coin_symbol
        )
        
        historical_prices = await self._get_historical_prices(
            db, coin_symbol, coin_id
        )
        
        if not historical_prices or len(historical_prices) < 40:
            return SupportResistanceResponse(
                coin_symbol=coin_symbol.upper(),
                support_levels=[],
                resistance_levels=[],
                current_price=current_price,
                timestamp=datetime.utcnow()
            )
        
        levels = self.indicators.detect_support_resistance(historical_prices)
        
        return SupportResistanceResponse(
            coin_symbol=coin_symbol.upper(),
            support_levels=levels["support_levels"],
            resistance_levels=levels["resistance_levels"],
            current_price=current_price,
            timestamp=datetime.utcnow()
        )
    
    async def _get_historical_prices(
        self, db: Session, coin_symbol: str, coin_id: str = None
    ) -> List[Decimal]:
        """Helper to get historical prices from Binance OHLC."""
        # Always use Binance OHLC (following architecture spec)
        prices = await self.data_fetcher.get_historical_prices(coin_symbol, days=200)
        
        if not prices:
            # Fallback: use current price from DB
            current_price = self.data_fetcher.get_current_price_from_db(
                db, coin_symbol
            )
            return [current_price] if current_price > 0 else []
        
        return prices
    
    def _interpret_rsi(self, rsi: Decimal) -> str:
        """Interpret RSI value."""
        if rsi >= 70:
            return "overbought"
        elif rsi <= 30:
            return "oversold"
        else:
            return "neutral"
    
    def _interpret_macd(self, macd_data: dict) -> str:
        """Interpret MACD data."""
        if macd_data["histogram"] > 0 and macd_data["macd"] > macd_data["signal"]:
            return "bullish"
        elif macd_data["histogram"] < 0 and macd_data["macd"] < macd_data["signal"]:
            return "bearish"
        else:
            return "neutral"
    
    def _interpret_ema_alignment(
        self, ema20: Decimal, ema50: Decimal, ema200: Decimal
    ) -> str:
        """Interpret EMA alignment."""
        if ema20 > ema50 > ema200:
            return "bullish"
        elif ema20 < ema50 < ema200:
            return "bearish"
        else:
            return "neutral"
    
    async def get_chart_data(
        self, db: Session, coin_symbol: str, timeframe: str = "1D", coin_id: str = None
    ) -> ChartDataResponse:
        """Get chart data for a specific timeframe from Binance OHLC."""
        # Get chart data from Binance (following architecture spec)
        chart_data = await self.data_fetcher.get_chart_data(coin_symbol, timeframe)
        
        # If no Binance data, fallback to current price (with minimal OHLC)
        if not chart_data:
            current_price = self.data_fetcher.get_current_price_from_db(
                db, coin_symbol
            )
            if current_price > 0:
                price_float = float(current_price)
                chart_data = [{
                    "timestamp": int(datetime.utcnow().timestamp() * 1000),
                    "open": price_float,
                    "high": price_float,
                    "low": price_float,
                    "close": price_float,
                    "volume": 0.0,
                    "price": price_float  # Keep for backward compatibility
                }]
        
        return ChartDataResponse(
            coin_symbol=coin_symbol.upper(),
            timeframe=timeframe,
            prices=chart_data,
            timestamp=datetime.utcnow()
        )
    
    # Phase 1.1: Coin Dashboard Method
    async def get_coin_dashboard(
        self,
        db: Session,
        coin_symbol: str,
        coin_id: str = None,
        timeframe: str = "1D",
        include_news: bool = True,
        include_portfolio: bool = True,
        include_analytics: bool = True,
        user_id: str = None
    ) -> CoinDashboardResponse:
        """
        Get comprehensive coin dashboard data in a single request.
        Phase 1.1: Batch requests, parallel execution, caching.
        """
        # Phase 1.2: Check Redis cache first
        cache_key = f"coin_dashboard:{coin_symbol}:{timeframe}"
        if self.redis_client and user_id:
            cache_key = f"coin_dashboard:{coin_symbol}:{timeframe}:{user_id}"
        
        if self.redis_client:
            try:
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    cached_dict = json.loads(cached_data)
                    return CoinDashboardResponse(**cached_dict)
            except Exception:
                pass  # Continue if cache fails
        
        # Phase 1.1: Parallel execution of all data fetching
        import asyncio
        
        # Core data (always needed)
        overview_task = self.get_coin_overview(db, coin_symbol, coin_id)
        chart_task = self.get_chart_data(db, coin_symbol, timeframe, coin_id)
        
        # Optional data
        news_task = None
        if include_news:
            news_task = self.premium_service.get_coin_news_premium(coin_symbol, limit=10, coin_id=coin_id)
        
        analytics_tasks = None
        if include_analytics:
            analytics_tasks = asyncio.gather(
                self.premium_service.get_price_predictions(db, coin_symbol, "7D"),
                self.premium_service.get_sentiment_analysis(db, coin_symbol),
                self.premium_service.get_correlation_analysis(db, coin_symbol),
                self.premium_service.get_historical_performance(db, coin_symbol, "1Y"),
                self.premium_service.get_market_depth(db, coin_symbol),
                self.premium_service.get_trading_pairs(db, coin_symbol),
                return_exceptions=True
            )
        
        # Execute all tasks in parallel
        tasks = [overview_task, chart_task]
        if news_task:
            tasks.append(news_task)
        else:
            tasks.append(asyncio.sleep(0))
        
        if analytics_tasks:
            tasks.append(analytics_tasks)
        else:
            tasks.append(asyncio.sleep(0))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Build response
        overview = results[0] if not isinstance(results[0], Exception) else None
        chart_data = results[1] if not isinstance(results[1], Exception) else None
        news = results[2] if news_task and not isinstance(results[2], Exception) else None
        analytics_result = results[3] if analytics_tasks and not isinstance(results[3], Exception) else None
        
        # Process analytics results
        analytics_dict = None
        if analytics_result and not isinstance(analytics_result, Exception):
            predictions, sentiment, correlation, historical, market_depth, trading_pairs = analytics_result
            analytics_dict = {
                "predictions": predictions.dict() if not isinstance(predictions, Exception) and predictions else None,
                "sentiment": sentiment.dict() if not isinstance(sentiment, Exception) and sentiment else None,
                "correlation": correlation.dict() if not isinstance(correlation, Exception) and correlation else None,
                "historical": historical.dict() if not isinstance(historical, Exception) and historical else None,
                "marketDepth": market_depth.dict() if not isinstance(market_depth, Exception) and market_depth else None,
                "tradingPairs": trading_pairs.dict() if not isinstance(trading_pairs, Exception) and trading_pairs else None,
            }
        
        response = CoinDashboardResponse(
            overview=overview,
            chartData=chart_data,
            news=news,
            portfolioPosition=None,  # Will be filled by portfolio service
            analytics=analytics_dict,
            lastUpdated=datetime.utcnow().isoformat() + "Z",
            cacheExpiry=(datetime.utcnow() + timedelta(minutes=1)).isoformat() + "Z",
        )
        
        # Phase 1.2: Cache the response in Redis
        if self.redis_client:
            try:
                cache_data = response.dict()
                self.redis_client.setex(cache_key, 60, json.dumps(cache_data))  # 1 minute cache
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Redis cache write failed for {cache_key}: {e}", exc_info=True)
                # Continue if cache fails
        
        return response
    
    async def close(self):
        """Close service connections."""
        await self.data_fetcher.close()

