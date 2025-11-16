# OpenMesh Tests

This directory contains tests for the OpenMesh platform.

## Test Structure

```
tests/
├── test_websocket.py        # WebSocket functionality tests
├── test_topology_api.py     # Topology API endpoint tests
├── test_metrics_api.py      # Metrics API endpoint tests
└── README.md                # This file
```

## Running Tests

### Prerequisites

Install development dependencies:

```bash
pip install -e ".[dev]"
```

Or install pytest manually:

```bash
pip install pytest pytest-asyncio pytest-cov
```

### Run All Tests

```bash
# From project root
pytest

# With coverage report
pytest --cov=backend --cov-report=term-missing

# With verbose output
pytest -v

# Run specific test file
pytest tests/test_websocket.py

# Run specific test class
pytest tests/test_websocket.py::TestConnectionManager

# Run specific test
pytest tests/test_websocket.py::TestConnectionManager::test_manager_initialization
```

### Test Coverage

Generate HTML coverage report:

```bash
pytest --cov=backend --cov-report=html
```

View the report by opening `htmlcov/index.html` in a browser.

## Test Categories

### WebSocket Tests (`test_websocket.py`)

- **ConnectionManager Tests**: Test subscription management, connection tracking
- **WebSocket Endpoint Tests**: Test WebSocket protocol, subscriptions, error handling
- **Broadcast Tests**: Test broadcasting updates to connected clients

### Topology API Tests (`test_topology_api.py`)

- **Data Structure Tests**: Verify topology API returns correct data format
- **Filtering Tests**: Test network-based filtering
- **Data Integrity Tests**: Verify link relationships, unique IDs, no self-references

### Metrics API Tests (`test_metrics_api.py`)

- **Device Metrics Tests**: Test device metrics retrieval, time ranges, multiple fields
- **Network Metrics Tests**: Test network-wide metrics (placeholder)
- **System Metrics Tests**: Test system-level metrics (placeholder)
- **Data Validation Tests**: Verify data types and formats

## Frontend Tests

Frontend tests are not yet implemented. To add frontend tests:

1. Install testing dependencies:
   ```bash
   cd frontend
   npm install --save-dev @testing-library/react @testing-library/jest-dom vitest jsdom
   ```

2. Create test files:
   - `frontend/src/components/__tests__/NetworkTopology.test.jsx`
   - `frontend/src/components/__tests__/MetricsChart.test.jsx`
   - `frontend/src/components/__tests__/DeviceMetrics.test.jsx`
   - `frontend/src/hooks/__tests__/useWebSocket.test.js`

3. Run frontend tests:
   ```bash
   cd frontend
   npm test
   ```

## Continuous Integration

Tests should be run automatically on:
- Pre-commit hooks
- Pull request creation
- Merge to main branch

Example GitHub Actions workflow:

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -e ".[dev]"
      - run: pytest --cov=backend
```

## Writing New Tests

### Backend Tests

Follow these patterns:

```python
import pytest
from fastapi.testclient import TestClient
from backend.main import app

@pytest.fixture
def client():
    return TestClient(app)

class TestMyFeature:
    def test_something(self, client):
        response = client.get("/api/v1/endpoint")
        assert response.status_code == 200
```

### Async Tests

For async code:

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await my_async_function()
    assert result is not None
```

### Database Tests

For tests requiring database:

```python
from backend.core.database import get_db

@pytest.fixture
async def db():
    # Setup test database
    async for session in get_db():
        yield session
```

## Test Best Practices

1. **Isolation**: Each test should be independent
2. **Clear Names**: Test names should describe what they test
3. **Arrange-Act-Assert**: Structure tests clearly
4. **Mock External Services**: Don't depend on external APIs
5. **Fast Execution**: Keep tests fast (< 1 second each)
6. **Coverage**: Aim for >80% code coverage

## Debugging Tests

```bash
# Run with debugging output
pytest -vv --tb=long

# Stop on first failure
pytest -x

# Run with Python debugger
pytest --pdb

# Show print statements
pytest -s
```
