# CryptoLens Backend

Backend microservices for CryptoLens built with Python FastAPI.

## Architecture

Microservices architecture as defined in Technical Specification:

1. **API Gateway** - Routes requests to services
2. **Auth Service** - JWT authentication
3. **Market Data Service** - Real-time market data
4. **Portfolio Service** - Portfolio management
5. **Coin Analytics Engine** - Technical indicators
6. **Trend Engine** - Trend analysis
7. **AI Insight Service** - AI-generated insights (v6)

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Copy environment file:
```bash
cp env.example .env
```

3. Update `.env` with your configuration

4. Run database migrations:
```bash
# Apply schema.sql to PostgreSQL
psql -U cryptolens_user -d cryptolens_db -f ../database/schema.sql
```

5. Start services with Docker:
```bash
cd ../docker
docker-compose up -d
```

## Development

Each service can be run independently:

```bash
# API Gateway
uvicorn api_gateway.main:app --host 0.0.0.0 --port 8000

# Market Data Service
uvicorn services.market_data_service.main:app --host 0.0.0.0 --port 8002
```

## Status

**Phase 0** - Foundation & Architecture (In Progress)
**Phase 1** - Market Module (Pending)

