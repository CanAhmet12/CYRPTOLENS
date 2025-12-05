"""
Main business logic service for AI Insight Service.
Orchestrates prompt generation, AI calls, and safety filtering.
Following AI Specification exactly.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import json
import hashlib
import asyncio
from .prompt_engine import PromptOrchestrationEngine
from .safety_filters import SafetyFilters
from .ai_client import AIClient
from .models import (
    MarketDataInput,
    CoinDataInput,
    PortfolioDataInput,
    MarketInsightResponse,
    PortfolioInsightResponse,
    CoinInsightResponse,
)


class AIInsightService:
    """Main service for AI insight generation."""
    
    def __init__(self):
        self.prompt_engine = PromptOrchestrationEngine()
        self.safety_filters = SafetyFilters()
        self.ai_client = AIClient()
        
        # Initialize Redis client for caching
        try:
            from shared.redis_client import get_redis
            self.redis_client = get_redis()
        except Exception:
            self.redis_client = None
    
    def _get_cache_key(self, insight_type: str, data_hash: str = None) -> str:
        """Generate cache key for insight."""
        if data_hash:
            return f"ai_insights:{insight_type}:{data_hash}"
        return f"ai_insights:{insight_type}:default"
    
    def _hash_market_data(self, market_json: Dict[str, Any]) -> str:
        """Generate hash for market data to use as cache key."""
        # Create a stable hash from key market indicators
        key_data = {
            "trend_score": market_json.get("trend_score", 50),
            "volatility_index": round(market_json.get("volatility_index", 0.5), 2),
            "btc_dominance": round(market_json.get("btc_dominance", 50), 1),
            "fear_greed": market_json.get("fear_greed", 50),
        }
        data_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()[:8]
    
    def _hash_coin_data(self, coin_json: Dict[str, Any]) -> str:
        """Generate hash for coin data to use as cache key."""
        # Create a stable hash from key coin indicators
        key_data = {
            "symbol": coin_json.get("symbol", ""),
            "trend_score": coin_json.get("trend_score", 50),
            "momentum_score": coin_json.get("momentum_score", 50),
            "rsi": round(coin_json.get("rsi", 50), 1),
            "volatility_score": round(coin_json.get("volatility_score", 0.5), 2),
        }
        data_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()[:8]
    
    async def generate_market_insight(
        self, market_data: MarketDataInput, user_id: str = None
    ) -> MarketInsightResponse:
        """Generate market AI insight with caching."""
        # Extract market JSON from input
        market_json = market_data.market
        
        # Check cache first
        if self.redis_client:
            try:
                data_hash = self._hash_market_data(market_json)
                cache_key = self._get_cache_key("market", data_hash)
                cached_response = self.redis_client.get(cache_key)
                if cached_response:
                    cached_data = json.loads(cached_response)
                    return MarketInsightResponse(**cached_data)
            except Exception:
                pass  # Continue if cache fails
        
        # Create prompts
        system_prompt, user_prompt = self.prompt_engine.create_market_prompt(market_json)
        
        # Generate insight using OpenAI Chat Completions API
        raw_response = await self.ai_client.generate_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=500,
            temperature=0.7
        )
        
        if not raw_response:
            # Fallback response
            return MarketInsightResponse(
                market_summary="Market analysis unavailable at this time.",
                risk_comment="Unable to assess risk levels."
            )
        
        # Calculate premium metrics from market data
        trend_score = market_json.get("trend_score", 50)
        volatility_index = market_json.get("volatility_index", 0.5)
        fear_greed = market_json.get("fear_greed", 50)
        
        # Calculate risk score (0-100)
        risk_score = min(100, max(0, int(
            (volatility_index * 50) +  # Volatility contributes up to 50
            ((100 - abs(fear_greed - 50)) / 2)  # Extreme fear/greed adds risk
        )))
        
        # Determine trend prediction
        if trend_score > 60:
            trend_prediction = "bullish"
        elif trend_score < 40:
            trend_prediction = "bearish"
        else:
            trend_prediction = "neutral"
        
        # Calculate confidence score based on data quality
        confidence_score = min(100, max(50, int(
            50 + (abs(trend_score - 50) / 2)  # Higher confidence if trend is clear
        )))
        
        # Parse JSON response from AI
        try:
            # Try to parse as JSON first
            parsed = json.loads(raw_response)
            market_summary = parsed.get("market_summary", raw_response)
            risk_comment = parsed.get("risk_comment", "Standard risk considerations apply.")
            
            # Extract premium fields if available
            ai_risk_score = parsed.get("risk_score")
            ai_trend_prediction = parsed.get("trend_prediction")
            ai_confidence_score = parsed.get("confidence_score")
            ai_key_opportunities = parsed.get("key_opportunities", [])
            ai_key_risks = parsed.get("key_risks", [])
        except (json.JSONDecodeError, AttributeError):
            # If not JSON, split the response intelligently
            sentences = raw_response.split('.')
            mid_point = len(sentences) // 2
            market_summary = '. '.join(sentences[:mid_point]).strip() + '.'
            risk_comment = '. '.join(sentences[mid_point:]).strip() + '.'
            ai_risk_score = None
            ai_trend_prediction = None
            ai_confidence_score = None
            ai_key_opportunities = []
            ai_key_risks = []
        
        # Sanitize and validate
        market_summary = self.safety_filters.sanitize_text(market_summary)
        risk_comment = self.safety_filters.sanitize_text(risk_comment)
        
        # Validate both fields
        is_valid_summary, _ = self.safety_filters.validate_insight(market_summary)
        is_valid_risk, _ = self.safety_filters.validate_insight(risk_comment)
        
        # Use AI values if available, otherwise use calculated values
        final_risk_score = ai_risk_score if ai_risk_score is not None else risk_score
        final_trend_prediction = ai_trend_prediction if ai_trend_prediction else trend_prediction
        final_confidence_score = ai_confidence_score if ai_confidence_score is not None else confidence_score
        
        if not is_valid_summary:
            market_summary = "Market analysis indicates stable conditions with balanced indicators."
        if not is_valid_risk:
            risk_comment = "Standard risk considerations apply to all market conditions."
        
        # Generate key opportunities and risks if not provided by AI
        if not ai_key_opportunities:
            if trend_score > 60:
                ai_key_opportunities = ["Strong upward momentum", "Positive market sentiment"]
            elif volatility_index < 0.3:
                ai_key_opportunities = ["Low volatility environment", "Stable market conditions"]
            else:
                ai_key_opportunities = ["Market consolidation", "Potential trend reversal"]
        
        if not ai_key_risks:
            if volatility_index > 0.7:
                ai_key_risks = ["High volatility", "Increased price swings"]
            elif abs(fear_greed - 50) > 40:
                ai_key_risks = ["Extreme sentiment", "Potential reversal"]
            else:
                ai_key_risks = ["Market uncertainty", "Mixed signals"]
        
        response = MarketInsightResponse(
            market_summary=market_summary,
            risk_comment=risk_comment,
            risk_score=final_risk_score,
            trend_prediction=final_trend_prediction,
            confidence_score=final_confidence_score,
            key_opportunities=ai_key_opportunities if isinstance(ai_key_opportunities, list) else [],
            key_risks=ai_key_risks if isinstance(ai_key_risks, list) else []
        )
        
        # Cache response (5 minutes TTL)
        if self.redis_client:
            try:
                data_hash = self._hash_market_data(market_json)
                cache_key = self._get_cache_key("market", data_hash)
                cache_data = response.dict()
                self.redis_client.setex(cache_key, 300, json.dumps(cache_data))
            except Exception:
                pass  # Continue if cache fails
        
        return response
    
    async def generate_portfolio_insight(
        self, portfolio_data: PortfolioDataInput, user_id: str = None
    ) -> PortfolioInsightResponse:
        """Generate portfolio AI insight."""
        # Extract portfolio JSON from input
        portfolio_json = portfolio_data.portfolio
        
        # Create prompts
        system_prompt, user_prompt = self.prompt_engine.create_portfolio_prompt(portfolio_json)
        
        # Generate insight using OpenAI Chat Completions API
        raw_response = await self.ai_client.generate_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=600,
            temperature=0.7
        )
        
        if not raw_response:
            # Fallback response
            return PortfolioInsightResponse(
                portfolio_summary="Portfolio analysis unavailable at this time.",
                risk_summary="Unable to assess risk levels."
            )
        
        # Calculate premium metrics from portfolio data
        portfolio_risk_score = portfolio_json.get("risk_score", 50)
        diversification_score = portfolio_json.get("diversification_score", 0.5) * 100
        assets = portfolio_json.get("assets", [])
        
        # Calculate performance score (simplified)
        # In a real scenario, this would be based on actual performance data
        performance_score = min(100, max(0, int(
            50 + (diversification_score / 2) - (portfolio_risk_score / 4)
        )))
        
        # Identify top and underperformers (simplified - based on volatility)
        top_performers = []
        underperformers = []
        for asset in assets[:5]:  # Limit to top 5
            symbol = asset.get("symbol", "")
            volatility = asset.get("volatility", 0.5)
            if volatility < 0.3:
                top_performers.append(symbol)
            elif volatility > 0.7:
                underperformers.append(symbol)
        
        # Parse JSON response from AI
        try:
            # Try to parse as JSON first
            parsed = json.loads(raw_response)
            portfolio_summary = parsed.get("portfolio_summary", raw_response)
            risk_summary = parsed.get("risk_summary", "Standard risk considerations apply.")
            
            # Extract premium fields if available
            ai_risk_score = parsed.get("risk_score")
            ai_diversification_score = parsed.get("diversification_score")
            ai_performance_score = parsed.get("performance_score")
            ai_recommended_actions = parsed.get("recommended_actions", [])
            ai_top_performers = parsed.get("top_performers", [])
            ai_underperformers = parsed.get("underperformers", [])
        except (json.JSONDecodeError, AttributeError):
            # If not JSON, split the response intelligently
            sentences = raw_response.split('.')
            mid_point = len(sentences) // 2
            portfolio_summary = '. '.join(sentences[:mid_point]).strip() + '.'
            risk_summary = '. '.join(sentences[mid_point:]).strip() + '.'
            ai_risk_score = None
            ai_diversification_score = None
            ai_performance_score = None
            ai_recommended_actions = []
            ai_top_performers = []
            ai_underperformers = []
        
        # Sanitize and validate
        portfolio_summary = self.safety_filters.sanitize_text(portfolio_summary)
        risk_summary = self.safety_filters.sanitize_text(risk_summary)
        
        # Validate both fields
        is_valid_summary, _ = self.safety_filters.validate_insight(portfolio_summary)
        is_valid_risk, _ = self.safety_filters.validate_insight(risk_summary)
        
        if not is_valid_summary:
            portfolio_summary = "Portfolio analysis indicates balanced allocation with moderate risk."
        if not is_valid_risk:
            risk_summary = "Standard risk considerations apply to portfolio structure."
        
        # Generate recommended actions if not provided by AI
        if not ai_recommended_actions:
            if diversification_score < 50:
                ai_recommended_actions = ["Consider diversifying across more assets", "Reduce concentration risk"]
            elif portfolio_risk_score > 70:
                ai_recommended_actions = ["Review high-risk positions", "Consider risk management strategies"]
            else:
                ai_recommended_actions = ["Monitor portfolio performance", "Rebalance if needed"]
        
        response = PortfolioInsightResponse(
            portfolio_summary=portfolio_summary,
            risk_summary=risk_summary,
            risk_score=ai_risk_score if ai_risk_score is not None else float(portfolio_risk_score),
            diversification_score=ai_diversification_score if ai_diversification_score is not None else float(diversification_score),
            performance_score=ai_performance_score if ai_performance_score is not None else float(performance_score),
            recommended_actions=ai_recommended_actions if isinstance(ai_recommended_actions, list) else [],
            top_performers=ai_top_performers if isinstance(ai_top_performers, list) else top_performers,
            underperformers=ai_underperformers if isinstance(ai_underperformers, list) else underperformers
        )
        
        # Cache response (5 minutes TTL, user-specific)
        if self.redis_client and user_id:
            try:
                cache_key = f"ai_insights:portfolio:{user_id}"
                cache_data = response.dict()
                self.redis_client.setex(cache_key, 300, json.dumps(cache_data))
            except Exception:
                pass  # Continue if cache fails
        
        return response
    
    async def generate_coin_insight(
        self, coin_data: CoinDataInput, user_id: str = None
    ) -> CoinInsightResponse:
        """Generate coin AI insight with caching."""
        # Extract coin JSON from input
        coin_json = coin_data.coin
        
        # Check cache first
        if self.redis_client:
            try:
                data_hash = self._hash_coin_data(coin_json)
                cache_key = self._get_cache_key("coin", data_hash)
                cached_response = self.redis_client.get(cache_key)
                if cached_response:
                    cached_data = json.loads(cached_response)
                    return CoinInsightResponse(**cached_data)
            except Exception:
                pass  # Continue if cache fails
        
        # Create prompts
        system_prompt, user_prompt = self.prompt_engine.create_coin_prompt(coin_json)
        
        # Generate insight using OpenAI Chat Completions API
        raw_response = await self.ai_client.generate_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=500,
            temperature=0.7
        )
        
        if not raw_response:
            # Fallback response
            return CoinInsightResponse(
                coin_summary="Coin analysis unavailable at this time.",
                technical_comment="Unable to assess technical indicators."
            )
        
        # Calculate premium metrics from coin data
        trend_score = coin_json.get("trend_score", 50)
        momentum_score = coin_json.get("momentum_score", 50)
        volatility_score = coin_json.get("volatility_score", 0.5)
        rsi = coin_json.get("rsi", 50)
        
        # Calculate risk score based on volatility and RSI extremes
        risk_score = min(100, max(0, int(
            (volatility_score * 60) +  # Volatility contributes up to 60
            (abs(rsi - 50) / 2)  # Extreme RSI adds risk
        )))
        
        # Determine price prediction
        if trend_score > 60 and momentum_score > 60:
            price_prediction = "up"
        elif trend_score < 40 and momentum_score < 40:
            price_prediction = "down"
        else:
            price_prediction = "sideways"
        
        # Calculate confidence score
        confidence_score = min(100, max(50, int(
            50 + (abs(trend_score - 50) / 3) + (abs(momentum_score - 50) / 3)
        )))
        
        # Extract key levels from coin data if available
        # In a real scenario, these would come from technical analysis
        key_levels = []
        current_price = coin_json.get("price_usd", 0)
        if current_price > 0:
            # Generate support/resistance levels (simplified)
            key_levels = [
                current_price * 0.95,  # Support
                current_price * 1.05,  # Resistance
            ]
        
        # Parse JSON response from AI
        try:
            # Try to parse as JSON first
            parsed = json.loads(raw_response)
            coin_summary = parsed.get("coin_summary", raw_response)
            technical_comment = parsed.get("technical_comment", "Technical indicators show balanced conditions.")
            
            # Extract premium fields if available
            ai_trend_score = parsed.get("trend_score")
            ai_momentum_score = parsed.get("momentum_score")
            ai_risk_score = parsed.get("risk_score")
            ai_price_prediction = parsed.get("price_prediction")
            ai_confidence_score = parsed.get("confidence_score")
            ai_key_levels = parsed.get("key_levels", [])
        except (json.JSONDecodeError, AttributeError):
            # If not JSON, split the response intelligently
            sentences = raw_response.split('.')
            mid_point = len(sentences) // 2
            coin_summary = '. '.join(sentences[:mid_point]).strip() + '.'
            technical_comment = '. '.join(sentences[mid_point:]).strip() + '.'
            ai_trend_score = None
            ai_momentum_score = None
            ai_risk_score = None
            ai_price_prediction = None
            ai_confidence_score = None
            ai_key_levels = []
        
        # Sanitize and validate
        coin_summary = self.safety_filters.sanitize_text(coin_summary)
        technical_comment = self.safety_filters.sanitize_text(technical_comment)
        
        # Validate both fields
        is_valid_summary, _ = self.safety_filters.validate_insight(coin_summary)
        is_valid_tech, _ = self.safety_filters.validate_insight(technical_comment)
        
        if not is_valid_summary:
            coin_summary = "Coin analysis indicates stable technical conditions."
        if not is_valid_tech:
            technical_comment = "Technical indicators show balanced conditions."
        
        response = CoinInsightResponse(
            coin_summary=coin_summary,
            technical_comment=technical_comment,
            trend_score=ai_trend_score if ai_trend_score is not None else float(trend_score),
            momentum_score=ai_momentum_score if ai_momentum_score is not None else float(momentum_score),
            risk_score=ai_risk_score if ai_risk_score is not None else float(risk_score),
            price_prediction=ai_price_prediction if ai_price_prediction else price_prediction,
            confidence_score=ai_confidence_score if ai_confidence_score is not None else float(confidence_score),
            key_levels=ai_key_levels if isinstance(ai_key_levels, list) and ai_key_levels else key_levels
        )
        
        # Cache response (5 minutes TTL)
        if self.redis_client:
            try:
                data_hash = self._hash_coin_data(coin_json)
                cache_key = self._get_cache_key("coin", data_hash)
                cache_data = response.dict()
                self.redis_client.setex(cache_key, 300, json.dumps(cache_data))
            except Exception:
                pass  # Continue if cache fails
        
        return response
    
    # Phase 1.1: Dashboard endpoint implementation
    async def get_insights_dashboard(
        self,
        user_id: Optional[str] = None,
        include_market: bool = True,
        include_portfolio: bool = True,
        include_coin_cache: bool = True,
    ) -> Dict[str, Any]:
        """Get comprehensive AI insights dashboard."""
        cache_key = f"ai_insights:dashboard:{user_id or 'anonymous'}"
        
        # Check L2 cache (Redis) first
        if self.redis_client:
            try:
                redis_cached = self.redis_client.get(cache_key)
                if redis_cached:
                    cached_data = json.loads(redis_cached)
                    cached_data["metadata"]["cacheHit"] = True
                    return cached_data
            except Exception:
                pass  # Continue if cache fails
        
        # Parallel batch requests
        tasks = []
        
        if include_market:
            tasks.append(self._fetch_market_insight_cached())
        
        if include_portfolio and user_id:
            tasks.append(self._fetch_portfolio_insight_cached(user_id))
        
        if include_coin_cache:
            tasks.append(self._fetch_recent_coin_insights())
        
        # Execute in parallel with error handling
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Build response with error handling
        result_index = 0
        market_insight = None
        portfolio_insight = None
        recent_coin_insights = []
        
        if include_market:
            if not isinstance(results[result_index], Exception) and results[result_index] is not None:
                market_insight = results[result_index]
            result_index += 1
        
        if include_portfolio and user_id:
            if result_index < len(results) and not isinstance(results[result_index], Exception) and results[result_index] is not None:
                portfolio_insight = results[result_index]
            result_index += 1
        
        if include_coin_cache:
            if result_index < len(results) and not isinstance(results[result_index], Exception):
                recent_coin_insights = results[result_index] if isinstance(results[result_index], list) else []
        
        response = {
            "marketInsight": market_insight,
            "portfolioInsight": portfolio_insight,
            "recentCoinInsights": recent_coin_insights,
            "metadata": {
                "lastUpdated": datetime.utcnow().isoformat(),
                "dataFreshness": "real-time",
                "cacheHit": False,
                "insightCount": sum(1 for r in [market_insight, portfolio_insight] if r is not None),
            }
        }
        
        # Cache response (1 minute TTL)
        if self.redis_client:
            try:
                cache_data = json.dumps(response)
                self.redis_client.setex(cache_key, 60, cache_data)
            except Exception:
                pass  # Continue if cache fails
        
        return response
    
    async def _fetch_market_insight_cached(self) -> Optional[Dict[str, Any]]:
        """Fetch market insight with caching."""
        cache_key = "ai_insights:market:latest"
        if self.redis_client:
            try:
                cached = self.redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception:
                pass
        
        # Return None if not cached (will be generated on-demand)
        return None
    
    async def _fetch_portfolio_insight_cached(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Fetch portfolio insight with caching (user-specific)."""
        cache_key = f"ai_insights:portfolio:{user_id}"
        if self.redis_client:
            try:
                cached = self.redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception:
                pass
        
        # Return None if not cached (will be generated on-demand)
        return None
    
    async def _fetch_recent_coin_insights(self) -> List[Dict[str, Any]]:
        """Fetch recently generated coin insights."""
        # Return empty list (coin insights are generated on-demand)
        # In future, we can implement a cache of recent coin insights
        return []
    
    async def close(self):
        """Close service connections."""
        await self.ai_client.close()

