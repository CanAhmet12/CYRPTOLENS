"""
Binance WebSocket Real-time Client
Manages WebSocket connections for ticker data with automatic reconnection.
"""
import asyncio
import json
import logging
from typing import Dict, Optional, Callable
from datetime import datetime
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException
import websockets.exceptions  # FIX: Import for ConnectionClosedOK, ConnectionClosedError

logger = logging.getLogger(__name__)


class BinanceRealtimeClient:
    """Manages Binance WebSocket connections for real-time ticker data."""
    
    WS_BASE_URL = "wss://stream.binance.com:9443/ws"
    RECONNECT_DELAY_INITIAL = 1  # seconds
    RECONNECT_DELAY_MAX = 60  # seconds
    
    def __init__(self):
        self.connections: Dict[str, websockets.WebSocketClientProtocol] = {}
        self.ticker_cache: Dict[str, Dict] = {}
        self.reconnect_delays: Dict[str, float] = {}
        self.is_running = False
        self.subscribers: Dict[str, list] = {}  # symbol -> list of callbacks
        
    async def subscribe_ticker(self, symbol: str, callback: Optional[Callable] = None):
        """
        Subscribe to ticker updates for a symbol.
        
        Args:
            symbol: Coin symbol (e.g., 'BTC', 'ETH')
            callback: Optional callback function to call on price updates
        """
        pair = f"{symbol.upper()}USDT"
        stream_name = f"{pair.lower()}@ticker"
        
        if callback:
            if symbol not in self.subscribers:
                self.subscribers[symbol] = []
            self.subscribers[symbol].append(callback)
        
        if pair in self.connections:
            logger.info(f"Already subscribed to {pair}")
            return
        
        # Start connection task
        asyncio.create_task(self._connect_stream(pair, stream_name))
    
    async def _connect_stream(self, pair: str, stream_name: str):
        """
        Connect to a WebSocket stream with automatic reconnection.
        FIX: Improved reconnection logic - reset count on successful connection, better error handling.
        """
        url = f"{self.WS_BASE_URL}/{stream_name}"
        delay = self.RECONNECT_DELAY_INITIAL
        max_reconnect_attempts = 20  # FIX: Increased attempts for better reliability
        reconnect_count = 0
        consecutive_failures = 0
        
        while True:  # FIX: Infinite loop with max attempts check inside
            try:
                # Log connection attempt
                if reconnect_count == 0:
                    logger.info(f"Connecting to Binance WebSocket: {stream_name}")
                elif reconnect_count <= 3:
                    logger.info(f"Reconnecting to {stream_name} (attempt {reconnect_count})...")
                
                # FIX: Improved connection parameters for stability
                async with websockets.connect(
                    url,
                    ping_interval=30,  # FIX: Increased ping interval (30 seconds)
                    ping_timeout=15,   # FIX: Increased ping timeout (15 seconds)
                    close_timeout=10,  # Wait 10 seconds for close
                    max_size=2**20,    # FIX: Set max message size (1MB)
                    read_limit=2**16   # FIX: Set read buffer limit (64KB)
                ) as websocket:
                    # FIX: Reset counters on successful connection
                    self.connections[pair] = websocket
                    delay = self.RECONNECT_DELAY_INITIAL
                    reconnect_count = 0
                    consecutive_failures = 0
                    
                    logger.info(f"✅ Connected to {stream_name}")
                    
                    # FIX: Keep connection alive with message loop
                    try:
                        async for message in websocket:
                            try:
                                data = json.loads(message)
                                await self._handle_ticker_update(pair, data)
                            except json.JSONDecodeError as e:
                                # Don't log every parse error to reduce spam
                                if consecutive_failures == 0:
                                    logger.debug(f"Failed to parse WebSocket message: {e}")
                                consecutive_failures = 0  # Reset on successful parse
                            except Exception as e:
                                # Don't log every handling error
                                if consecutive_failures == 0:
                                    logger.debug(f"Error handling ticker update: {e}")
                                consecutive_failures = 0  # Reset on successful handling
                    except websockets.exceptions.ConnectionClosedOK:
                        # Normal closure - reconnect
                        logger.info(f"WebSocket {stream_name} closed normally, reconnecting...")
                        reconnect_count += 1
                    except websockets.exceptions.ConnectionClosedError as e:
                        # Error closure - reconnect with backoff
                        logger.warning(f"WebSocket {stream_name} closed with error: {e}")
                        reconnect_count += 1
                        consecutive_failures += 1
                            
            except (ConnectionClosed, WebSocketException) as e:
                reconnect_count += 1
                consecutive_failures += 1
                error_msg = str(e)
                
                # Check for HTTP 451 (geographic restriction) or other connection errors
                if "451" in error_msg or "rejected" in error_msg.lower():
                    if reconnect_count == 1:
                        logger.warning(f"⚠️ Binance WebSocket rejected for {pair} (possibly geographic restriction): {e}")
                    # Don't retry immediately for 451 errors, use longer delay
                    delay = self.RECONNECT_DELAY_MAX
                else:
                    # Only log first few connection errors
                    if reconnect_count <= 3:
                        logger.warning(f"WebSocket connection closed for {pair}: {e}")
                
                if pair in self.connections:
                    del self.connections[pair]
                    
            except Exception as e:
                reconnect_count += 1
                consecutive_failures += 1
                error_msg = str(e)
                if "451" in error_msg or "rejected" in error_msg.lower():
                    if reconnect_count == 1:
                        logger.warning(f"⚠️ Binance WebSocket rejected for {pair} (possibly geographic restriction): {e}")
                    delay = self.RECONNECT_DELAY_MAX
                else:
                    if reconnect_count <= 3:
                        logger.error(f"Unexpected error in WebSocket connection for {pair}: {e}")
                
                if pair in self.connections:
                    del self.connections[pair]
            
            # FIX: Check max attempts and stop if exceeded
            if reconnect_count >= max_reconnect_attempts:
                logger.error(f"❌ Max reconnect attempts ({max_reconnect_attempts}) reached for {stream_name}. Stopping reconnection.")
                # FIX: Remove from connections dict
                if pair in self.connections:
                    del self.connections[pair]
                break
            
            # Exponential backoff for reconnection (with max delay)
            if reconnect_count <= 3:
                logger.info(f"Reconnecting to {stream_name} in {delay} seconds... (attempt {reconnect_count}/{max_reconnect_attempts})")
            await asyncio.sleep(delay)
            delay = min(delay * 2, self.RECONNECT_DELAY_MAX)
    
    async def _handle_ticker_update(self, pair: str, data: Dict):
        """Handle incoming ticker update from WebSocket."""
        try:
            symbol = pair.replace("USDT", "").upper()
            price = float(data.get('c', 0))  # Last price
            change_24h = float(data.get('P', 0))  # 24h price change percent
            
            ticker_data = {
                'symbol': symbol,
                'price': price,
                'change24h': change_24h,
                'volume24h': float(data.get('v', 0)),
                'high24h': float(data.get('h', 0)),
                'low24h': float(data.get('l', 0)),
                'lastUpdated': datetime.utcnow().isoformat()
            }
            
            # Update cache
            self.ticker_cache[symbol] = ticker_data
            
            # Notify subscribers
            if symbol in self.subscribers:
                for callback in self.subscribers[symbol]:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(ticker_data)
                        else:
                            callback(ticker_data)
                    except Exception as e:
                        logger.error(f"Error in subscriber callback: {e}")
                        
        except Exception as e:
            logger.error(f"Error processing ticker update for {pair}: {e}")
    
    def get_latest_ticker(self, symbol: str) -> Optional[Dict]:
        """
        Get latest ticker data from cache.
        
        Returns:
            Dict with price, change24h, lastUpdated, or None if not available
        """
        return self.ticker_cache.get(symbol.upper())
    
    def get_all_tickers(self) -> Dict[str, Dict]:
        """Get all cached ticker data."""
        return self.ticker_cache.copy()
    
    async def unsubscribe(self, symbol: str):
        """Unsubscribe from a symbol's ticker updates."""
        pair = f"{symbol.upper()}USDT"
        if pair in self.connections:
            try:
                await self.connections[pair].close()
            except Exception:
                pass
            del self.connections[pair]
        
        if symbol in self.subscribers:
            del self.subscribers[symbol]
    
    async def close_all(self):
        """Close all WebSocket connections."""
        for pair, websocket in list(self.connections.items()):
            try:
                await websocket.close()
            except Exception:
                pass
        self.connections.clear()
        self.subscribers.clear()

