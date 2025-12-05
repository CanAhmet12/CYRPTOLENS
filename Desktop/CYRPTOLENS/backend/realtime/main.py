"""
Real-time Data Service FastAPI Application
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import json
from typing import Set
from shared.config import settings
from shared.sentry_init import init_sentry
from .realtime_data_service import RealtimeDataService

# Initialize Sentry
init_sentry()

logger = logging.getLogger(__name__)

# Global service instance
realtime_service = RealtimeDataService()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.subscriptions: dict = {}  # websocket -> set of symbols
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        self.subscriptions[websocket] = set()
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        if websocket in self.subscriptions:
            del self.subscriptions[websocket]
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        # PERFORMANCE FIX: Better error handling for connection issues
        try:
            await websocket.send_json(message)
        except Exception as e:
            # PERFORMANCE FIX: Don't log every connection error (reduces log spam)
            error_msg = str(e).lower()
            if "connection" not in error_msg and "closed" not in error_msg:
                logger.error(f"Error sending message to WebSocket: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: dict, symbols: set = None):
        """
        Broadcast message to all connections or connections subscribed to specific symbols.
        PERFORMANCE FIX: Better error handling and reduced log spam.
        """
        disconnected = []
        for connection in self.active_connections:
            if symbols is None or symbols.intersection(self.subscriptions.get(connection, set())):
                try:
                    await connection.send_json(message)
                except Exception as e:
                    # PERFORMANCE FIX: Don't log every connection error (reduces log spam)
                    error_msg = str(e).lower()
                    if "connection" not in error_msg and "closed" not in error_msg:
                        logger.error(f"Error broadcasting to WebSocket: {e}")
                    disconnected.append(connection)
        
        for conn in disconnected:
            self.disconnect(conn)
    
    def subscribe(self, websocket: WebSocket, symbol: str):
        if websocket not in self.subscriptions:
            self.subscriptions[websocket] = set()
        self.subscriptions[websocket].add(symbol.upper())
        logger.info(f"WebSocket subscribed to {symbol}. Total subscriptions: {len(self.subscriptions[websocket])}")
    
    def unsubscribe(self, websocket: WebSocket, symbol: str):
        if websocket in self.subscriptions:
            self.subscriptions[websocket].discard(symbol.upper())
            logger.info(f"WebSocket unsubscribed from {symbol}")

manager = ConnectionManager()


async def ticker_update_callback(ticker_data: dict):
    """Callback function to broadcast ticker updates to WebSocket clients."""
    symbol = ticker_data.get('symbol', '').upper()
    if not symbol:
        return
    
    message = {
        "type": "ticker",
        "symbol": symbol,
        "data": ticker_data
    }
    # Broadcast to all connections subscribed to this symbol
    symbols_set = {symbol}
    await manager.broadcast(message, symbols_set)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    # Startup
    logger.info("Starting real-time data service...")
    await realtime_service.initialize()
    
    # Set up ticker update callback for WebSocket broadcasting
    # Note: Binance client callback receives ticker_data dict directly
    for symbol in ['BTC', 'ETH', 'SOL', 'BNB', 'ADA', 'XRP', 'DOGE', 'DOT', 'MATIC', 'AVAX']:
        await realtime_service.binance_client.subscribe_ticker(symbol, ticker_update_callback)
    
    yield
    # Shutdown
    logger.info("Shutting down real-time data service...")
    await realtime_service.shutdown()


app = FastAPI(
    title="CryptoLens Real-time Data Service",
    version=settings.APP_VERSION,
    description="Real-time market data with graceful fallbacks",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "realtime_data_service",
        "version": settings.APP_VERSION
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/health/data")
async def health_data():
    """
    Health endpoint showing when each provider last succeeded.
    """
    market_overview = realtime_service.get_market_overview()
    all_tickers = realtime_service.get_all_tickers()
    
    return {
        "status": "healthy",
        "market_polling": {
            "lastUpdated": market_overview.get("lastUpdated"),
            "isStale": market_overview.get("isStale", True),
            "hasData": bool(market_overview.get("coins"))
        },
        "binance_websocket": {
            "connected_symbols": list(all_tickers.keys()),
            "total_tickers": len(all_tickers)
        }
    }


@app.get("/realtime/market-overview")
async def get_market_overview():
    """
    Get market overview with lastUpdated and isStale fields.
    Always returns last known values, never None.
    """
    return realtime_service.get_market_overview()


@app.get("/realtime/coin/{symbol}")
async def get_coin_data(symbol: str, timeframe: str = "1h"):
    """
    Get real-time data for a specific coin.
    Returns ticker, OHLC, and indicators with lastUpdated and isStale.
    
    Args:
        symbol: Coin symbol (e.g., 'BTC')
    """
    data = await realtime_service.get_coin_data(symbol, timeframe)
    return data


@app.get("/realtime/ticker/{symbol}")
async def get_ticker(symbol: str):
    """
    Get latest ticker data for a symbol.
    """
    return realtime_service.get_latest_ticker(symbol)


@app.get("/realtime/tickers")
async def get_all_tickers():
    """
    Get all ticker data.
    """
    return realtime_service.get_all_tickers()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time market data updates.
    
    PERFORMANCE FIX: Added connection timeout, error handling, and connection limits.
    
    Client can send messages:
    - {"action": "subscribe", "symbol": "BTC"} - Subscribe to symbol updates
    - {"action": "unsubscribe", "symbol": "BTC"} - Unsubscribe from symbol
    - {"action": "ping"} - Keep-alive ping
    
    Server sends:
    - {"type": "ticker", "symbol": "BTC", "data": {...}} - Ticker update
    - {"type": "market_overview", "data": {...}} - Market overview update
    - {"type": "pong"} - Response to ping
    """
    # PERFORMANCE FIX: Connection limit check
    MAX_CONNECTIONS = 100
    if len(manager.active_connections) >= MAX_CONNECTIONS:
        logger.warning(f"WebSocket connection limit reached ({MAX_CONNECTIONS}). Rejecting new connection.")
        await websocket.close(code=1008, reason="Server at capacity")
        return
    
    await manager.connect(websocket)
    
    # Send initial market overview
    try:
        market_overview = realtime_service.get_market_overview()
        await manager.send_personal_message({
            "type": "market_overview",
            "data": market_overview
        }, websocket)
    except Exception as e:
        logger.error(f"Error sending initial market overview: {e}")
    
    try:
        # PERFORMANCE FIX: Add timeout for receive operations
        import asyncio
        while True:
            try:
                # Set timeout for receiving messages (60 seconds)
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=60.0
                )
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await manager.send_personal_message({
                        "type": "ping"
                    }, websocket)
                except Exception:
                    break  # Connection lost
                continue
            
            try:
                message = json.loads(data)
                action = message.get("action")
                
                if action == "subscribe":
                    symbol = message.get("symbol")
                    if symbol:
                        manager.subscribe(websocket, symbol)
                        # Send current ticker data if available
                        ticker = realtime_service.get_latest_ticker(symbol)
                        if ticker:
                            await manager.send_personal_message({
                                "type": "ticker",
                                "symbol": symbol.upper(),
                                "data": ticker
                            }, websocket)
                
                elif action == "unsubscribe":
                    symbol = message.get("symbol")
                    if symbol:
                        manager.unsubscribe(websocket, symbol)
                
                elif action == "ping":
                    await manager.send_personal_message({
                        "type": "pong"
                    }, websocket)
                
            except json.JSONDecodeError:
                await manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON"
                }, websocket)
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                # PERFORMANCE FIX: Don't send error for every exception to reduce spam
                if "connection" not in str(e).lower():
                    await manager.send_personal_message({
                        "type": "error",
                        "message": "Internal server error"
                    }, websocket)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        # PERFORMANCE FIX: Better error handling
        error_msg = str(e)
        if "connection" not in error_msg.lower() and "closed" not in error_msg.lower():
            logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

