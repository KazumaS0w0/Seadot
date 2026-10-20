"""
Pytest Fixtures for Seadot Backend Tests (FastAPI)
=========================================

Provides shared fixtures for database sessions, test clients, and cleanup operations.
"""
import pytest
import os
import tempfile
from pathlib import Path
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base


# Create Base for declarative models
Base = declarative_base()


@pytest.fixture(scope="function")
def temp_db_file():
    """
    Provide a temporary database file that is cleaned up after the test.
    
    Usage:
        def test_with_temp_db(temp_db_file):
            # use temp_db_file (path to temporary SQLite database)
            ...
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = Path(tmp_file.name)
    yield str(db_path)
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture(scope="function")
def temp_db_engine_and_tables(temp_db_file):
    """
    Provide database engine with tables created for the test.
    
    Usage:
        def test_with_engine(engine, temp_db_file):
            # use engine and tables are already created
            ...
    """
    from seadot_backend.db.models import Base
    
    engine = create_engine(f"sqlite:///{temp_db_file}", echo=False, pool_pre_ping=True)
    
    # Create all tables
    metadata = MetaData()
    metadata.reflect(bind=engine)  # Reflect existing schema if any
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Cleanup is handled by temp_db_file fixture


@pytest.fixture(scope="function")
def client(temp_db_engine_and_tables, temp_db_file):
    """
    Provide the FastAPI test client.
    
    Usage:
        def test_api(client, temp_db_file):
            response = client.post('/api/downloads', json=...)
            ...
    """
    from seadot_backend.api.app import create_app
    
    app = create_app(temp_db_file)
    with app.test_client() as client:
        yield client


@pytest.fixture(scope="function")
def db_session(temp_db_engine_and_tables):
    """
    Provide a fresh database session for the test.
    
    Usage:
        def test_with_session(db_session, temp_db_file):
            session = get_session()
            download = Download(download_id="test")
            session.add(download)
            session.commit()
            ...
    """
    from seadot_backend.db.state import get_db_state
    
    # Get fresh session for this test
    db_state = get_db_state(temp_db_file)
    yield db_state.get("session_factory")()


@pytest.fixture(scope="function")
def sample_download_data():
    """
    Provide a sample download record data for testing.
    
    Usage:
        def test_with_sample(sample_download_data):
            response = client.post('/api/downloads', json=sample_download_data)
            ...
    """
    return {
        "download_id": f"test-{id(__import__('time').time())}",
        "url": "https://example.com/sample.zip",
        "dest_path": r"C:\Downloads\sample.zip",
        "headers": {"User-Agent": "Mozilla/5.0"},
        "progress": 0.0,
        "speed": 0.0,
        "total_size": None,
        "downloaded_size": 0,
        "eta": None,
        "status": "downloading"
    }

