"""
External API clients for fetching market data.
Integrates with CoinGecko and Binance APIs.
"""
import httpx
import asyncio
from typing import List, Dict, Optional
from decimal import Decimal
from datetime import datetime
from shared.config import settings


class CoinGeckoClient:
    """Client for CoinGecko API."""
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    def __init__(self):
        self.api_key = settings.COINGECKO_API_KEY
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"x-cg-demo-api-key": self.api_key} if self.api_key else {}
        )
    
    async def get_market_overview(self) -> Dict:
        """Get global market overview."""
        url = f"{self.BASE_URL}/global"
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()
    
    async def get_coins_market_data(
        self,
        vs_currency: str = "usd",
        order: str = "market_cap_desc",
        per_page: int = 100,
        page: int = 1
    ) -> List[Dict]:
        """Get market data for multiple coins."""
        url = f"{self.BASE_URL}/coins/markets"
        params = {
            "vs_currency": vs_currency,
            "order": order,
            "per_page": per_page,
            "page": page,
            "sparkline": False
        }
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    async def get_coin_data(self, coin_id: str) -> Dict:
        """Get detailed data for a specific coin."""
        url = f"{self.BASE_URL}/coins/{coin_id}"
        params = {
            "localization": False,
            "tickers": False,
            "market_data": True,
            "community_data": False,
            "developer_data": False,
            "sparkline": False
        }
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


class BinanceClient:
    """Client for Binance API (optional, for additional data)."""
    
    BASE_URL = "https://api.binance.com/api/v3"
    
    def __init__(self):
        self.api_key = settings.BINANCE_API_KEY
        self.api_secret = settings.BINANCE_API_SECRET
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_24h_ticker(self, symbol: str = "BTCUSDT") -> Dict:
        """Get 24hr ticker price change statistics."""
        url = f"{self.BASE_URL}/ticker/24hr"
        params = {"symbol": symbol}
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


class FearGreedClient:
    """Client for Fear & Greed Index API."""
    
    BASE_URL = "https://api.alternative.me/fng"
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_fear_greed_index(self) -> Dict:
        """Get current Fear & Greed Index."""
        url = f"{self.BASE_URL}/"
        response = await self.client.get(url)
        response.raise_for_status()
        data = response.json()
        return data.get("data", [{}])[0] if data.get("data") else {}
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

