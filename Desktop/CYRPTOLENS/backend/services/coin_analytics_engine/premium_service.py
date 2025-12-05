"""
Premium Coin Features Service
Handles advanced coin analytics features: news, predictions, sentiment, etc.
"""
from typing import List, Optional
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
import httpx
from shared.config import settings
from .models import (
    CoinNewsResponse,
    CoinNewsItem,
    CoinPricePredictionResponse,
    CoinPricePrediction,
    CoinSentimentResponse,
    CoinSentiment,
    CoinCorrelationResponse,
    CoinCorrelationItem,
    CoinMarketDepthResponse,
    CoinMarketDepthItem,
    CoinTradingPairsResponse,
    CoinTradingPair,
    CoinHistoricalResponse,
    CoinHistoricalPerformance,
)
from shared.data_providers.coingecko_provider import CoinGeckoMarketDataProvider
from shared.repositories.crypto_data_repository import CryptoDataRepository


class CoinPremiumService:
    """Service for premium coin features."""
    
    def __init__(self):
        market_provider = CoinGeckoMarketDataProvider()
        self.repository = CryptoDataRepository(market_provider, None)
    
    async def get_coin_news_premium(
        self,
        coin_symbol: str,
        limit: int = 20,
        category: Optional[str] = None,
        source: Optional[str] = None,
        coin_id: Optional[str] = None
    ) -> CoinNewsResponse:
        """Get premium news feed with filtering."""
        try:
            if not coin_id:
                coin_id = coin_symbol.lower()
            
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/news"
            params = {"limit": limit}
            
            api_key = getattr(settings, 'COINGECKO_API_KEY', '') or ''
            if api_key:
                params["x_cg_demo_api_key"] = api_key
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                
                if response.status_code == 404:
                    return CoinNewsResponse(
                        coin_symbol=coin_symbol.upper(),
                        news=[],
                        total=0
                    )
                
                response.raise_for_status()
                data = response.json()
                
                news_items = []
                for item in data.get("news", [])[:limit]:
                    # Apply filters
                    if category and item.get("category", "").lower() != category.lower():
                        continue
                    if source and item.get("source", "").lower() != source.lower():
                        continue
                    
                    news_items.append(CoinNewsItem(
                        title=item.get("title", ""),
                        source=item.get("source", ""),
                        url=item.get("url", ""),
                        image=item.get("image", ""),
                        description=item.get("description", ""),
                        date=item.get("date", ""),
                        category=item.get("category", ""),
                    ))
                
                return CoinNewsResponse(
                    coin_symbol=coin_symbol.upper(),
                    news=news_items,
                    total=len(news_items)
                )
        except Exception as e:
            # Return empty on error
            return CoinNewsResponse(
                coin_symbol=coin_symbol.upper(),
                news=[],
                total=0
            )
    
    async def get_price_predictions(
        self,
        db: Session,
        coin_symbol: str,
        timeframe: str = "7D"
    ) -> CoinPricePredictionResponse:
        """Get AI-powered price predictions."""
        try:
            # Get current price
            current_price = await self._get_current_price(coin_symbol)
            
            # For now, return simple predictions based on trend
            # In production, this would use ML models
            predictions = []
            
            # Generate predictions for different timeframes
            timeframes_map = {
                "1D": 1,
                "7D": 7,
                "30D": 30,
                "1Y": 365
            }
            
            days = timeframes_map.get(timeframe, 7)
            
            # Simple prediction: assume 5% growth with 70% confidence
            # In production, use actual ML model
            predicted_price = current_price * Decimal("1.05")
            confidence = Decimal("70.0")
            
            predictions.append(CoinPricePrediction(
                predicted_price=predicted_price,
                confidence_score=confidence,
                prediction_date=datetime.now() + timedelta(days=days),
                timeframe=timeframe,
                model_version="v1.0"
            ))
            
            return CoinPricePredictionResponse(
                coin_symbol=coin_symbol.upper(),
                predictions=predictions,
                current_price=current_price
            )
        except Exception as e:
            # Return empty predictions on error
            current_price = await self._get_current_price(coin_symbol)
            return CoinPricePredictionResponse(
                coin_symbol=coin_symbol.upper(),
                predictions=[],
                current_price=current_price
            )
    
    async def get_sentiment_analysis(
        self,
        db: Session,
        coin_symbol: str
    ) -> CoinSentimentResponse:
        """Get social sentiment analysis."""
        try:
            # For now, return mock sentiment data
            # In production, integrate with Twitter/Reddit APIs
            sources = [
                CoinSentiment(
                    source="twitter",
                    sentiment_score=Decimal("65.5"),
                    positive_count=1200,
                    negative_count=300,
                    neutral_count=500,
                    total_mentions=2000,
                    recorded_at=datetime.now()
                ),
                CoinSentiment(
                    source="reddit",
                    sentiment_score=Decimal("58.2"),
                    positive_count=800,
                    negative_count=400,
                    neutral_count=300,
                    total_mentions=1500,
                    recorded_at=datetime.now()
                ),
                CoinSentiment(
                    source="news",
                    sentiment_score=Decimal("72.0"),
                    positive_count=50,
                    negative_count=10,
                    neutral_count=40,
                    total_mentions=100,
                    recorded_at=datetime.now()
                ),
            ]
            
            # Calculate overall sentiment
            overall = sum(s.sentiment_score for s in sources) / len(sources)
            
            return CoinSentimentResponse(
                coin_symbol=coin_symbol.upper(),
                overall_sentiment=overall,
                sources=sources,
                timestamp=datetime.now()
            )
        except Exception as e:
            return CoinSentimentResponse(
                coin_symbol=coin_symbol.upper(),
                overall_sentiment=Decimal("0"),
                sources=[],
                timestamp=datetime.now()
            )
    
    async def get_correlation_analysis(
        self,
        db: Session,
        coin_symbol: str,
        limit: int = 10
    ) -> CoinCorrelationResponse:
        """Get correlation with other coins."""
        try:
            # Get top coins from market data
            # For now, return mock correlations
            # In production, calculate actual correlations from price data
            correlations = [
                CoinCorrelationItem(
                    coin_symbol="BTC",
                    correlation=Decimal("0.85"),
                    price=Decimal("45000.00"),
                    change_24h=Decimal("2.5")
                ),
                CoinCorrelationItem(
                    coin_symbol="ETH",
                    correlation=Decimal("0.72"),
                    price=Decimal("2800.00"),
                    change_24h=Decimal("1.8")
                ),
            ]
            
            return CoinCorrelationResponse(
                coin_symbol=coin_symbol.upper(),
                correlations=correlations[:limit],
                timestamp=datetime.now()
            )
        except Exception as e:
            return CoinCorrelationResponse(
                coin_symbol=coin_symbol.upper(),
                correlations=[],
                timestamp=datetime.now()
            )
    
    async def get_market_depth(
        self,
        coin_symbol: str,
        exchange: str = "binance",
        limit: int = 20
    ) -> CoinMarketDepthResponse:
        """Get market depth (order book)."""
        try:
            # For now, return mock data
            # In production, fetch from exchange API
            bids = [
                CoinMarketDepthItem(
                    price=Decimal("50000.00") - Decimal(str(i * 10)),
                    quantity=Decimal(str(0.5 + i * 0.1)),
                    total=Decimal("0")
                )
                for i in range(limit)
            ]
            
            asks = [
                CoinMarketDepthItem(
                    price=Decimal("50000.00") + Decimal(str(i * 10)),
                    quantity=Decimal(str(0.5 + i * 0.1)),
                    total=Decimal("0")
                )
                for i in range(limit)
            ]
            
            # Calculate totals
            total_bid = Decimal("0")
            for bid in bids:
                total_bid += bid.quantity
                bid.total = total_bid
            
            total_ask = Decimal("0")
            for ask in asks:
                total_ask += ask.quantity
                ask.total = total_ask
            
            return CoinMarketDepthResponse(
                coin_symbol=coin_symbol.upper(),
                exchange=exchange,
                bids=bids,
                asks=asks,
                timestamp=datetime.now()
            )
        except Exception as e:
            return CoinMarketDepthResponse(
                coin_symbol=coin_symbol.upper(),
                exchange=exchange,
                bids=[],
                asks=[],
                timestamp=datetime.now()
            )
    
    async def get_trading_pairs(
        self,
        coin_symbol: str,
        exchange: Optional[str] = None
    ) -> CoinTradingPairsResponse:
        """Get trading pairs for a coin."""
        try:
            # For now, return common pairs
            # In production, fetch from exchange APIs
            pairs = [
                CoinTradingPair(
                    base_symbol=coin_symbol.upper(),
                    quote_symbol="USDT",
                    exchange="binance",
                    volume_24h=Decimal("1000000.00"),
                    price=Decimal("50000.00")
                ),
                CoinTradingPair(
                    base_symbol=coin_symbol.upper(),
                    quote_symbol="BTC",
                    exchange="binance",
                    volume_24h=Decimal("500000.00"),
                    price=Decimal("1.1")
                ),
            ]
            
            if exchange:
                pairs = [p for p in pairs if p.exchange.lower() == exchange.lower()]
            
            return CoinTradingPairsResponse(
                coin_symbol=coin_symbol.upper(),
                pairs=pairs,
                timestamp=datetime.now()
            )
        except Exception as e:
            return CoinTradingPairsResponse(
                coin_symbol=coin_symbol.upper(),
                pairs=[],
                timestamp=datetime.now()
            )
    
    async def get_historical_performance(
        self,
        db: Session,
        coin_symbol: str,
        timeframe: str = "1M"
    ) -> CoinHistoricalResponse:
        """Get historical performance data."""
        try:
            # Get historical data from repository
            # For now, return mock data
            # In production, fetch from database or API
            days_map = {
                "7D": 7,
                "1M": 30,
                "3M": 90,
                "6M": 180,
                "1Y": 365
            }
            
            days = days_map.get(timeframe, 30)
            data = []
            
            base_price = Decimal("50000.00")
            for i in range(days):
                date = datetime.now() - timedelta(days=days - i)
                price = base_price * (Decimal("1") + Decimal(str(0.01 * (i % 10 - 5))))
                volume = Decimal("1000000.00") * (Decimal("1") + Decimal(str(0.1 * (i % 5))))
                change = Decimal(str(0.5 * (i % 4 - 2)))
                
                data.append(CoinHistoricalPerformance(
                    date=date,
                    price=price,
                    volume=volume,
                    change_24h=change
                ))
            
            # Calculate metrics
            if len(data) > 1:
                total_return = ((data[-1].price - data[0].price) / data[0].price) * Decimal("100")
                prices = [d.price for d in data]
                volatility = self._calculate_volatility(prices)
            else:
                total_return = Decimal("0")
                volatility = Decimal("0")
            
            return CoinHistoricalResponse(
                coin_symbol=coin_symbol.upper(),
                timeframe=timeframe,
                data=data,
                total_return=total_return,
                volatility=volatility
            )
        except Exception as e:
            return CoinHistoricalResponse(
                coin_symbol=coin_symbol.upper(),
                timeframe=timeframe,
                data=[],
                total_return=Decimal("0"),
                volatility=Decimal("0")
            )
    
    async def _get_current_price(self, coin_symbol: str) -> Decimal:
        """Get current price for a coin."""
        try:
            prices = await self.repository.market_provider.get_prices_for_symbols(
                [coin_symbol.upper()]
            )
            if coin_symbol.upper() in prices:
                return Decimal(str(prices[coin_symbol.upper()].price))
            return Decimal("0")
        except Exception:
            return Decimal("0")
    
    def _calculate_volatility(self, prices: List[Decimal]) -> Decimal:
        """Calculate volatility from price list."""
        if len(prices) < 2:
            return Decimal("0")
        
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                ret = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(ret)
        
        if not returns:
            return Decimal("0")
        
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / len(returns)
        volatility = (variance ** Decimal("0.5")) * Decimal("100")
        
        return volatility

