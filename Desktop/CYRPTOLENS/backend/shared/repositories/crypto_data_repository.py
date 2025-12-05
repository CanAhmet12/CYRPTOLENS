"""
Crypto Data Repository.
Central data access layer following CryptoLens Data Architecture Specification.
"""
from typing import List, Dict, Optional
from decimal import Decimal
from datetime import datetime
from shared.data_providers.interfaces import (
    MarketDataProvider,
    OhlcDataProvider,
    Timeframe,
    CoinMeta,
    PriceData,
    MarketOverview,
    Candle as ProviderCandle
)
from shared.data_providers.symbol_resolver import SymbolResolver
from shared.analytics import (
    Candle,
    calculate_rsi,
    calculate_macd,
    calculate_ema,
    calculate_volatility,
    calculate_trend_score,
    calculate_momentum,
)


class CryptoDataRepository:
    """
    Central repository for crypto data.
    Uses MarketDataProvider (CoinGecko) and OhlcDataProvider (Binance).
    """
    
    def __init__(
        self,
        market_provider: MarketDataProvider,
        ohlc_provider: OhlcDataProvider
    ):
        self.market_provider = market_provider
        self.ohlc_provider = ohlc_provider
        self.symbol_resolver = SymbolResolver()
    
    async def get_dashboard_data(self) -> Dict:
        """Get data for dashboard screen."""
        market_overview = await self.market_provider.get_market_overview()
        trending_coins = await self.market_provider.get_trending_coins()
        
        # Get prices for trending coins
        trending_symbols = [coin.symbol for coin in trending_coins]
        prices = await self.market_provider.get_prices_for_symbols(trending_symbols)
        
        return {
            "market_overview": market_overview,
            "trending_coins": trending_coins,
            "prices": prices
        }
    
    async def get_coin_detail_data(
        self,
        symbol: str,
        timeframe: Timeframe
    ) -> Dict:
        """
        Get data for coin detail screen with indicators.
        Following Indicator & Analytics Engine Specification.
        
        Flow:
        1. Get OHLC from Binance (via OhlcDataProvider)
        2. Get market data from CoinGecko (via MarketDataProvider)
        3. Pass OHLC to Indicator Engine
        4. Return composed DTO with indicators
        """
        mapping = self.symbol_resolver.get_mapping(symbol)
        
        # Get market data from CoinGecko
        prices = await self.market_provider.get_prices_for_symbols([symbol])
        price_data = prices.get(symbol.upper())
        
        # Get OHLC data from Binance (if supported)
        provider_candles = []
        is_binance_supported = self.symbol_resolver.is_binance_supported(symbol)
        
        if is_binance_supported:
            try:
                provider_candles = await self.ohlc_provider.get_ohlc_for_symbol(
                    symbol,
                    timeframe,
                    limit=500
                )
            except Exception:
                # If Binance fails, return empty
                provider_candles = []
        
        # Convert provider candles to analytics candles
        analytics_candles = []
        for c in provider_candles:
            try:
                analytics_candle = AnalyticsCandle.from_provider_candle(c)
                analytics_candles.append(analytics_candle)
            except Exception:
                continue
        
        # Calculate indicators (pure functions, no side effects)
        indicators = {}
        
        if analytics_candles and len(analytics_candles) >= 14:
            try:
                # RSI
                rsi_list = calculate_rsi(analytics_candles)
                indicators["rsi"] = rsi_list[-1] if rsi_list and rsi_list[-1] is not None else None
                
                # MACD
                macd_data = calculate_macd(analytics_candles)
                if macd_data and macd_data.get("histogram"):
                    hist_list = macd_data["histogram"]
                    last_hist = None
                    for h in reversed(hist_list):
                        if h is not None:
                            last_hist = h
                            break
                else:
                    last_hist = None
                
                indicators["macd"] = {
                    "macdLine": macd_data.get("macdLine", []),
                    "signalLine": macd_data.get("signalLine", []),
                    "histogram": macd_data.get("histogram", [])
                }
                
                # EMAs
                ema20_list = calculate_ema(analytics_candles, 20)
                ema50_list = calculate_ema(analytics_candles, 50)
                ema200_list = calculate_ema(analytics_candles, 200)
                indicators["ema20"] = ema20_list[-1] if ema20_list else None
                indicators["ema50"] = ema50_list[-1] if ema50_list else None
                indicators["ema200"] = ema200_list[-1] if ema200_list else None
                
                # Volatility
                vol_data = calculate_volatility(analytics_candles)
                indicators["volatility"] = vol_data
                
                # Momentum
                momentum_data = calculate_momentum(analytics_candles)
                indicators["momentum"] = momentum_data
                
                # Trend Score
                trend_data = calculate_trend_score(
                    analytics_candles,
                    ema20=indicators.get("ema20"),
                    ema50=indicators.get("ema50"),
                    ema200=indicators.get("ema200"),
                    macd_histogram=last_hist,
                    rsi=indicators.get("rsi")
                )
                indicators["trendScore"] = trend_data
                
            except Exception as e:
                # If indicator calculation fails, continue without indicators
                # Log error in production
                pass
        
        return {
            "symbol": symbol.upper(),
            "mapping": mapping,
            "price_data": price_data,
            "ohlc_data": provider_candles,  # Return original provider candles for chart
            "is_binance_supported": is_binance_supported,
            "indicators": indicators
        }
    
    async def get_portfolio_data(self, symbols: List[str]) -> Dict[str, PriceData]:
        """Get prices for portfolio coins."""
        return await self.market_provider.get_prices_for_symbols(symbols)
    
    async def get_market_list(self, limit: int = 250) -> List[CoinMeta]:
        """Get list of coins for market screen."""
        return await self.market_provider.get_coin_list(limit)
    
    async def get_market_overview(self) -> MarketOverview:
        """Get global market overview."""
        return await self.market_provider.get_market_overview()
    
    async def get_ohlc_for_analytics(
        self,
        symbol: str,
        timeframe: Timeframe = Timeframe.DAY_1,
        limit: int = 500
    ) -> List[Candle]:
        """Get OHLC data for technical analysis with fallback to CoinGecko."""
        # Try Binance first
        candles = []
        if self.symbol_resolver.is_binance_supported(symbol):
            try:
                candles = await self.ohlc_provider.get_ohlc_for_symbol(
                    symbol,
                    timeframe,
                    limit
                )
            except Exception:
                # Binance failed, try CoinGecko fallback
                pass
        
        # If Binance failed or not supported, try CoinGecko
        if not candles:
            try:
                from shared.data_providers.coingecko_ohlc_provider import CoinGeckoOhlcDataProvider
                coingecko_ohlc = CoinGeckoOhlcDataProvider()
                candles = await coingecko_ohlc.get_ohlc_for_symbol(
                    symbol,
                    timeframe,
                    limit
                )
            except Exception:
                # Both failed, return empty
                pass
        
        return candles
    
    async def check_binance_support(self, symbol: str) -> bool:
        """Check if coin is supported on Binance."""
        return self.symbol_resolver.is_binance_supported(symbol)

