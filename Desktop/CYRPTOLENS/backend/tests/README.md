# CryptoLens Backend Tests

## Test Structure

```
tests/
├── unit/              # Unit tests (fast, isolated)
│   ├── test_auth_service.py
│   ├── test_batch_endpoint.py
│   └── ...
├── integration/       # Integration tests (slower, require services)
│   ├── test_api_gateway.py
│   └── ...
└── conftest.py        # Shared fixtures and configuration
```

## Running Tests

### All Tests
```bash
pytest
```

### Unit Tests Only
```bash
pytest tests/unit -m unit
```

### Integration Tests Only
```bash
pytest tests/integration -m integration
```

### With Coverage
```bash
pytest --cov=services --cov=shared --cov-report=html
```

### Specific Test File
```bash
pytest tests/unit/test_auth_service.py
```

### Specific Test Function
```bash
pytest tests/unit/test_auth_service.py::TestAuthService::test_register_user_success
```

## Test Markers

Tests are marked with pytest markers:

- `@pytest.mark.unit` - Unit tests (fast, no external dependencies)
- `@pytest.mark.integration` - Integration tests (require services)
- `@pytest.mark.slow` - Slow running tests
- `@pytest.mark.requires_db` - Tests that require database
- `@pytest.mark.requires_redis` - Tests that require Redis
- `@pytest.mark.requires_api` - Tests that require external APIs

## Running Marked Tests

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Run tests that don't require external APIs
pytest -m "not requires_api"
```

## Fixtures

Common fixtures available in `conftest.py`:

- `db_session` - SQLite in-memory database session
- `override_get_db` - Override get_db dependency
- `test_client` - FastAPI test client
- `async_client` - Async HTTP client
- `mock_redis` - Mock Redis client
- `mock_httpx_client` - Mock HTTPX client for external APIs

## Writing Tests

### Unit Test Example

```python
@pytest.mark.unit
class TestMyService:
    def test_my_function(self, db_session):
        service = MyService()
        result = service.my_function(db_session)
        assert result is not None
```

### Integration Test Example

```python
@pytest.mark.integration
@pytest.mark.requires_api
class TestMyEndpoint:
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_endpoint(self, client):
        response = client.get("/api/my-endpoint")
        assert response.status_code == 200
```

## CI/CD

Tests should be run in CI/CD pipeline:

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest --cov --cov-report=xml

# Generate coverage report
coverage report
```

