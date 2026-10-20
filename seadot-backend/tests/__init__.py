"""
Seadot Test Suite
=================

Test infrastructure and configurations for Seadot project.

Tests are organized into two categories:
- Unit Tests (tests/unit/): Test individual models, services, and components in isolation
- Integration Tests (tests/integration/): Test API endpoints, database persistence, and end-to-end flows

Running Tests:
--------------
From the seadot-backend directory:

    venv\Scripts\activate
    pytest tests/ -v

Or run specific test files:

    pytest tests/unit/test_db_models.py -v
    pytest tests/integration/test_api.py -v

Test Configuration:
-------------------
- Database: SQLite in-memory for unit tests, file-based for integration tests
- Test database path is configured via DB_TEST_PATH environment variable (optional)
- Flask app factory pattern used for test client creation
"""

import os


# Allow configuring test database path from environment
DB_TEST_PATH = os.environ.get("DB_TEST_PATH", None)


def get_test_db_path():
    """
    Get the test database path.
    
    Returns:
        str or None: Path to SQLite database, or None for in-memory
    
    Environment variable:
        DB_TEST_PATH: If set, use this path for SQLite database
                     Otherwise returns None for in-memory database
    """
    return DB_TEST_PATH