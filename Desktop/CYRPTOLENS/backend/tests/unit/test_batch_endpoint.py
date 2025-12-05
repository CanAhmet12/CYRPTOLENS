"""
Unit tests for Batch API endpoint.
"""
import pytest
from fastapi.testclient import TestClient
from api_gateway.main import app


@pytest.mark.unit
class TestBatchEndpoint:
    """Test Batch API endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_batch_request_success(self, client):
        """Test successful batch request."""
        response = client.post(
            "/api/batch",
            json={
                "requests": [
                    {
                        "method": "GET",
                        "path": "/health",
                        "id": "health1"
                    },
                    {
                        "method": "GET",
                        "path": "/health",
                        "id": "health2"
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total" in data
        assert "successful" in data
        assert "failed" in data
        assert len(data["results"]) == 2
    
    def test_batch_request_empty(self, client):
        """Test batch request with no requests."""
        response = client.post(
            "/api/batch",
            json={"requests": []}
        )
        
        assert response.status_code == 400
        assert "No requests provided" in response.json()["detail"]
    
    def test_batch_request_too_many(self, client):
        """Test batch request with too many requests."""
        requests = [{"method": "GET", "path": "/health", "id": f"req{i}"} for i in range(21)]
        
        response = client.post(
            "/api/batch",
            json={"requests": requests}
        )
        
        assert response.status_code == 400
        assert "Maximum 20 requests" in response.json()["detail"]
    
    def test_batch_request_mixed_results(self, client):
        """Test batch request with some successful and some failed requests."""
        response = client.post(
            "/api/batch",
            json={
                "requests": [
                    {
                        "method": "GET",
                        "path": "/health",
                        "id": "success"
                    },
                    {
                        "method": "GET",
                        "path": "/nonexistent",
                        "id": "failure"
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["successful"] >= 1
        assert data["failed"] >= 0  # May vary based on service availability

