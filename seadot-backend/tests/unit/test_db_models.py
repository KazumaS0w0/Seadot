"""
Unit Tests for Seadot Database Models (SQLAlchemy ORM)
Tests model creation, serialization, CRUD operations, and status transitions.

Usage:
    cd seadot-backend
    venv\Scripts\activate
    pytest tests/unit/test_db_models.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import text


# Import models (need to adjust path)
from db.models import Download, DownloadHistory, DownloadStatus, Base


class TestDownloadModel:
    """Test cases for Download model"""
    
    def setup_method(self):
        """Set up test database before each test method"""
        engine = create_engine("sqlite:///:memory:", echo=False, pool_pre_ping=True)
        Base.metadata.create_all(bind=engine)
        
        # Create session factory
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        self.session = SessionLocal()
    
    def test_create_download(self):
        """Test creating a new download record"""
        # Create new download - use headers_json as JSON string
        download = Download(
            download_id="abc123",
            url="https://example.com/file.zip",
            dest_path="C:/Downloads/file.zip",
            headers_json='{"User-Agent": "Mozilla/5.0"}',
            status=DownloadStatus.DOWNLOADING
        )
        
        self.session.add(download)
        self.session.commit()
        self.session.refresh(download)
        
        # Verify creation
        assert download.download_id == "abc123"
        assert download.url == "https://example.com/file.zip"
        assert download.dest_path == "C:/Downloads/file.zip"
        assert hasattr(download.status, 'value')
        assert download.status.value == "downloading"
    
    def test_update_download_progress(self):
        """Test updating download progress"""
        # Create download with size
        download = Download(
            download_id="test123",
            url="https://example.com/large.zip",
            dest_path="C:/Downloads/large.zip",
            status=DownloadStatus.DOWNLOADING,
            total_size=104857600  # 100 MB
        )
        self.session.add(download)
        self.session.commit()
        
        # Update progress
        download.downloaded_size = 52428800  # 50 MB
        self.session.commit()
        
        assert download.total_size == 104857600
        assert download.downloaded_size == 52428800
    
    def test_pause_download(self):
        """Test pausing a downloading task"""
        # Create downloading task
        download = Download(
            download_id="pause123",
            url="https://example.com/file.zip",
            dest_path="C:/Downloads/file.zip",
            status=DownloadStatus.DOWNLOADING,
            total_size=104857600
        )
        self.session.add(download)
        self.session.commit()
        
        # Pause it
        now = datetime.utcnow()
        download.status = DownloadStatus.PAUSED
        download.paused_at = now
        self.session.commit()
        
        assert hasattr(download.status, 'value')
        assert download.status.value == "paused"
        assert download.paused_at is not None
    
    def test_resume_download(self):
        """Test resuming a paused task"""
        # Create paused task
        download = Download(
            download_id="resume123",
            url="https://example.com/file.zip",
            dest_path="C:/Downloads/file.zip",
            status=DownloadStatus.PAUSED,
            total_size=104857600
        )
        self.session.add(download)
        now = datetime.utcnow()
        download.paused_at = now
        self.session.commit()
        
        # Resume it
        download.status = DownloadStatus.DOWNLOADING
        download.paused_at = None
        self.session.commit()
        
        assert hasattr(download.status, 'value')
        assert download.status.value == "downloading"
        assert download.paused_at is None
    
    def test_stop_download(self):
        """Test stopping a downloading task"""
        # Create downloading task
        download = Download(
            download_id="stop123",
            url="https://example.com/file.zip",
            dest_path="C:/Downloads/file.zip",
            status=DownloadStatus.DOWNLOADING,
            total_size=104857600
        )
        self.session.add(download)
        self.session.commit()
        
        # Stop it
        download.status = DownloadStatus.FAILED
        download.paused_at = None
        self.session.commit()
        
        assert hasattr(download.status, 'value')
        assert download.status.value == "failed"
    
    def test_create_history(self):
        """Test creating a history record"""
        # Create an existing download first
        download = Download(
            download_id="history123",
            url="https://example.com/file.zip",
            dest_path="C:/Downloads/file.zip",
            status=DownloadStatus.COMPLETED,
            total_size=50485760,
            downloaded_size=50485760
        )
        self.session.add(download)
        self.session.commit()
        
        # Create history record
        history = DownloadHistory(
            download_id="history123",
            url="https://example.com/file.zip",
            dest_path="C:/Downloads/file.zip",
            headers_json='{"User-Agent": "Mozilla/5.0"}',
            total_size=50485760,
            downloaded_size=50485760,
            status=DownloadStatus.COMPLETED
        )
        
        self.session.add(history)
        self.session.commit()
        self.session.refresh(history)
        
        # Verify history creation
        assert history.download_id == "history123"
        assert history.url == "https://example.com/file.zip"
        assert history.dest_path == "C:/Downloads/file.zip"
        assert hasattr(history.status, 'value')
        assert history.status.value == "completed"
    
    def test_serialize_history(self):
        """Test history serialization to dict"""
        # Create a completed download and history
        download = Download(
            download_id="serialize123",
            url="https://example.com/file.zip",
            dest_path="C:/Downloads/file.zip",
            status=DownloadStatus.COMPLETED,
            total_size=50485760,
            downloaded_size=50485760,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        self.session.add(download)
        
        history = DownloadHistory(
            download_id="serialize123",
            url="https://example.com/file.zip",
            dest_path="C:/Downloads/file.zip",
            headers_json='{"User-Agent": "Mozilla/5.0"}',
            total_size=50485760,
            downloaded_size=50485760,
            status=DownloadStatus.COMPLETED
        )
        
        self.session.add(history)
        self.session.commit()
        self.session.refresh(history)
        
        # Test to_dict serialization
        history_dict = history.to_dict()
        
        assert isinstance(history_dict, dict)
        assert history_dict["download_id"] == "serialize123"
        assert history_dict["url"] == "https://example.com/file.zip"
        assert history_dict["dest_path"] == "C:/Downloads/file.zip"
        assert history_dict["status"] == "completed"
        assert history_dict["total_size"] == 50485760