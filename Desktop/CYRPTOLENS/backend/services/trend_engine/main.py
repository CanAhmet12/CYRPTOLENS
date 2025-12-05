"""
Trend Engine main application.
Will be implemented in Phase 4.
"""
from fastapi import FastAPI
from shared.config import settings

app = FastAPI(
    title="CryptoLens Trend Engine",
    version=settings.APP_VERSION
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "trend_engine"}

