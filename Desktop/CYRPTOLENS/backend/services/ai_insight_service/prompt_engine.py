"""
Prompt Orchestration Engine
Following AI Specification exactly.
"""
from typing import Dict, Any, Tuple
import json


class PromptOrchestrationEngine:
    """Orchestrates prompts for AI insight generation."""
    
    BASE_SYSTEM_PROMPT = """You are CryptoLens AI, a professional crypto analytics assistant. 
You ONLY explain analytics, technical indicators, risk, volatility and portfolio structure. 
You MUST NOT give direct investment advice, trading signals, or guarantee any outcome. 
You must not say 'buy', 'sell', or 'hold'. 
Always keep a neutral, analytical tone and use plain language."""

    @staticmethod
    def create_market_prompt(market_data: Dict[str, Any]) -> Tuple[str, str]:
        """
        Create prompts for market insight generation.
        Returns: (system_prompt, user_prompt)
        """
        # Serialize market data to JSON
        market_json = json.dumps(market_data, indent=2)
        
        system_prompt = PromptOrchestrationEngine.BASE_SYSTEM_PROMPT + """
        
Mode: MARKET
You are analyzing global crypto market conditions. Explain trends, volatility, dominance, and sentiment in neutral, analytical language."""
        
        user_prompt = f"""Mode: MARKET

Here is the pre-computed market analytics JSON:

{market_json}

Using ONLY this JSON:
- Explain the current global crypto market trend.
- Comment on volatility level.
- Comment on BTC dominance and what it implies for altcoins.
- Mention the general market sentiment based on fear_greed and trend_score.
- Highlight risks in a neutral tone.

Rules:
- 3–5 sentences.
- Do not recommend buying or selling.
- Do not mention specific price targets.
- Return your response as a JSON object with the following fields:
  - "market_summary": string (main analysis)
  - "risk_comment": string (risk assessment)
  - "risk_score": number 0-100 (calculated risk level)
  - "trend_prediction": string ("bullish", "bearish", or "neutral")
  - "confidence_score": number 0-100 (confidence in analysis)
  - "key_opportunities": array of strings (2-3 key opportunities)
  - "key_risks": array of strings (2-3 key risks)"""
        
        return system_prompt, user_prompt
    
    @staticmethod
    def create_portfolio_prompt(portfolio_data: Dict[str, Any]) -> Tuple[str, str]:
        """
        Create prompts for portfolio insight generation.
        Returns: (system_prompt, user_prompt)
        """
        # Serialize portfolio data to JSON
        portfolio_json = json.dumps(portfolio_data, indent=2)
        
        system_prompt = PromptOrchestrationEngine.BASE_SYSTEM_PROMPT + """
        
Mode: PORTFOLIO
You are analyzing a user's cryptocurrency portfolio. Explain diversification, risk profile, and structure in neutral, analytical language."""
        
        user_prompt = f"""Mode: PORTFOLIO

Here is the user's portfolio analytics JSON:

{portfolio_json}

Using ONLY this JSON:
- Describe the diversification level of the portfolio.
- Describe the risk profile (e.g. low, medium, high) and why.
- Comment on stablecoin_share and what it means for volatility exposure.
- Comment on concentration in the top assets.
- If risk_score is high, explain in neutral language what drives that risk.

Rules:
- 3–6 sentences.
- Do not tell the user to buy or sell anything.
- Do not mention leverage or trading strategies.
- Focus only on structure, risk and diversification.
- Return your response as a JSON object with the following fields:
  - "portfolio_summary": string (main analysis)
  - "risk_summary": string (risk assessment)
  - "risk_score": number 0-100 (portfolio risk level)
  - "diversification_score": number 0-100 (diversification quality)
  - "performance_score": number 0-100 (overall performance)
  - "recommended_actions": array of strings (2-4 actionable recommendations)
  - "top_performers": array of strings (coin symbols performing well)
  - "underperformers": array of strings (coin symbols underperforming)"""
        
        return system_prompt, user_prompt
    
    @staticmethod
    def create_coin_prompt(coin_data: Dict[str, Any]) -> Tuple[str, str]:
        """
        Create prompts for coin insight generation.
        Returns: (system_prompt, user_prompt)
        """
        # Serialize coin data to JSON
        coin_json = json.dumps(coin_data, indent=2)
        
        system_prompt = PromptOrchestrationEngine.BASE_SYSTEM_PROMPT + """
        
Mode: COIN
You are analyzing a single cryptocurrency's technical indicators. Explain RSI, MACD, EMA, trend, momentum, and volatility in neutral, analytical language."""
        
        user_prompt = f"""Mode: COIN

Here is the analytics JSON for a single coin:

{coin_json}

Using ONLY this JSON:
- Explain the technical situation of this coin in plain language.
- Use RSI, MACD state, EMA alignment, trend_score, momentum_score, and volatility_score to guide your explanation.
- If momentum_score and trend_score are high, explain that the trend is strong.
- If volatility_score is high, explain that price swings can be large.
- Do NOT suggest any trades or price targets.

Rules:
- 3–5 sentences.
- No 'you should buy/sell' statements.
- No explicit recommendations, only analysis.
- Return your response as a JSON object with the following fields:
  - "coin_summary": string (main analysis)
  - "technical_comment": string (technical assessment)
  - "trend_score": number 0-100 (trend strength)
  - "momentum_score": number 0-100 (momentum strength)
  - "risk_score": number 0-100 (risk level)
  - "price_prediction": string ("up", "down", or "sideways")
  - "confidence_score": number 0-100 (confidence in analysis)
  - "key_levels": array of numbers (important support/resistance levels)"""
        
        return system_prompt, user_prompt
    
    @staticmethod
    def format_input_summary(
        market: Dict[str, Any] = None,
        coin: Dict[str, Any] = None,
        portfolio: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Format input data summary for caching."""
        summary = {}
        
        if market:
            summary["market"] = market
        
        if coin:
            summary["coin"] = coin
        
        if portfolio:
            summary["portfolio"] = portfolio
        
        return summary

