"""
Integration tests for API Gateway.
"""
import pytest
from fastapi.testclient import TestClient
from api_gateway.main import app


@pytest.mark.integration
class TestAPIGateway:
    """Test API Gateway integration."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "service" in data
        assert data["service"] == "api_gateway"
    
    @pytest.mark.requires_api
    def test_market_overview_proxy(self, client):
        """Test market overview proxy (requires market service)."""
        response = client.get("/api/market/overview")
        # May return 503 if service is not running, which is acceptable
        assert response.status_code in [200, 503]
    
    @pytest.mark.requires_api
    def test_market_heatmap_proxy(self, client):
        """Test market heatmap proxy (requires market service)."""
        response = client.get("/api/market/heatmap?limit=10")
        assert response.status_code in [200, 503]

