# Seadot Testing Guide

## 📋 Overview

This directory contains the comprehensive testing suite for the Seadot project.

```
tests/
├── __init__.py              # Test package initialization
├── conftest.py              # Pytest fixtures and configuration
├── README.md                # This file
├── unit/                    # Unit tests (isolated component testing)
│   ├── __init__.py
│   └── test_db_models.py    # Database model tests
├── integration/             # Integration tests (end-to-end testing)
│   └── test_api.py          # API endpoints and WebSocket tests
└── fixtures/                # Test database fixtures (future)
    └── downloads.json       # Sample download data
```

## 🚀 Quick Start

### Prerequisites

Make sure you're in the `seadot-backend` directory and activated the virtual environment:

```cmd
cd seadot-backend
venv\Scripts\activate
```

### Run All Tests

```cmd
pip install pytest pytest-asyncio  # If not already installed
pytest tests/ -v
```

### Run Specific Test Categories

```cmd
# Run only unit tests
pytest tests/unit/ -v

# Run only integration tests
pytest tests/integration/ -v

# Run specific test file
pytest tests/unit/test_db_models.py -v

# Run with coverage report
pytest tests/ --cov=seadot-backend --cov-report=html
```

## 📚 Test Structure

### Unit Tests (`tests/unit/`)

**Purpose**: Test individual components in isolation.

**test_db_models.py**:
- ✅ Model creation and serialization
- ✅ CRUD operations through service functions
- ✅ Foreign key relationships
- ✅ Status transitions (pause/resume/stop)
- ✅ Cleanup operations

**Test Classes**:
- `TestDownloadModel`: Download model tests
- `TestDownloadHistoryModel`: History model tests

### Integration Tests (`tests/integration/`)

**Purpose**: Test API endpoints and end-to-end flows.

**test_api.py**:
- ✅ REST endpoint responses (201, 400, etc.)
- ✅ Database persistence across requests
- ✅ WebSocket communication
- ✅ Error handling and validation
- ✅ Download status state machine transitions

**Test Classes**:
- `TestRESTEndpoints`: All POST/GET endpoints
- `TestDatabasePersistence`: Data persistence tests
- `TestWebSocketEndpoint`: WebSocket tests (future)
- `TestErrorHandling`: Validation and error cases
- `TestDownloadStatusTransitions`: State machine tests

## 🔧 Test Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_TEST_PATH` | None | SQLite database path for integration tests. Use temp file or specify your own. |

Example usage:
```cmd
set DB_TEST_PATH=C:\temp\seadot_test.db
pytest tests/integration/ -v
```

### Pytest Markers

Use markers to organize tests:

```python
import pytest

@pytest.mark.slow  # Skip by default unless -m slow is used
def test_something():
    pass

@pytest.mark.db  # Tests requiring database access
def test_database_operation():
    pass
```

Run specific markers:
```cmd
pytest tests/ -m "integration and not slow"
```

## 🛠️ Fixtures

Available fixtures (defined in `conftest.py`):

| Fixture | Usage | Description |
|---------|-------|-------------|
| `db_session()` | `session = db_session()` | Get a database session |
| `app` | `self.app = app` | Flask test client |
| `client` | `self.client = client` | Test client instance |

Example:
```python
def test_something(db_session):
    session = db_session()
    download = Download(url="http://...", dest_path="...")
    session.add(download)
    session.commit()
```

## 📊 Test Coverage

Generate coverage report:

```cmd
pytest tests/ --cov=seadot-backend --cov-report=html --cov-report=term-missing
```

View HTML report in browser:
```cmd
start htmlcov\index.html
```

## 🔍 Debugging Tests

### Run Single Test

```cmd
pytest tests/unit/test_db_models.py::TestDownloadModel::test_create_download -v -s
```

`-s`: Print stdout (useful for debugging)

### Add Debug Prints

In test code:
```python
import logging
logger = logging.getLogger(__name__)

def test_something():
    logger.debug("Starting test...")
    # Your test code
    logger.debug("Test completed")
```

### View Full Output

```cmd
pytest tests/ -vvs  # Verbose with stdout
```

## 🐛 Troubleshooting

### "No module named 'seadot-backend'" Error

Make sure you're in the correct directory:
```cmd
cd seadot-backend
venv\Scripts\activate
pip install -e .  # If project is packaged
```

### Database Tests Failing

Ensure test database exists:
```cmd
set DB_TEST_PATH=C:\temp\seadot_test.db
mkdir C:\temp
pytest tests/integration/ -v
```

### Import Errors in conftest.py

The fixtures use project modules. If imports fail, check that `db/` and `api/` directories exist with proper module files.

## ✅ Best Practices

1. **Keep unit tests fast**: Use in-memory SQLite database
2. **Use integration tests sparingly**: They're slower and require more setup
3. **Test one thing per test**: Don't combine unrelated operations
4. **Use fixtures**: Reuse database sessions and clients
5. **Name tests clearly**: `test_<action>_<object>` pattern

## 📖 References

- [Pytest Documentation](https://docs.pytest.org/)
- [Flask Testing Guide](https://flask.palletsprojects.com/en/2.3/testing/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html)
