"""
Seadot Database Models (SQLAlchemy ORM)
Models untuk Download & History tracking dengan SQLite.
"""

from enum import Enum
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, BigInteger, ForeignKey
from sqlalchemy.dialects.sqlite import REAL as SQLiteReal
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import uuid

# Base class untuk declarative model registry
Base = declarative_base()


class DownloadStatus(Enum):
    """Download status enum dengan values"""
    
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class Download(Base):
    """Active download record dengan real-time progress"""
    
    __tablename__ = 'downloads'
    
    # Primary key - SQLAlchemy will generate Integer automatically
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # User-friendly ID (UUID v4) - unique constraint for identification
    download_id = Column(String(32), unique=True, nullable=False, index=True)
    
    # URL and destination
    url = Column(String(2048), nullable=False)
    dest_path = Column(Text, nullable=False)
    
    # Headers as JSON string
    headers_json = Column(Text)
    
    # Status tracking
    status = Column(Enum(DownloadStatus), default=DownloadStatus.PENDING)
    
    # Progress tracking (bytes)
    total_size = Column(BigInteger, default=0)
    downloaded_size = Column(BigInteger, default=0)
    
    # Chunk configuration
    chunk_size = Column(Integer, default=8 * 1024 * 1024)  # 8MB chunks
    chunk_count_threshold = Column(Integer, default=16)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    paused_at = Column(DateTime, nullable=True)
    
    # Retry logic
    retry_count = Column(Integer, default=0)
    
    # Relationships
    history_records = relationship("DownloadHistory", back_populates="history_records", cascade="all, delete-orphan")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response"""
        return {
            "id": self.id,
            "download_id": self.download_id,
            "url": self.url,
            "dest_path": self.dest_path,
            "headers_json": self.headers_json,
            "status": self.status.value if hasattr(self.status, 'value') else str(self.status),
            "progress": round((self.downloaded_size / self.total_size * 100), 2) if self.total_size > 0 else 0,
            "downloaded_size": self.downloaded_size,
            "total_size": self.total_size,
            "chunk_size": self.chunk_size,
            "chunk_count_threshold": self.chunk_count_threshold,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "paused_at": self.paused_at.isoformat() if self.paused_at else None,
            "retry_count": self.retry_count
        }


class DownloadHistory(Base):
    """Completed download history dengan detailed stats"""
    
    __tablename__ = 'download_history'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key reference to downloads (unique constraint for joining)
    download_id = Column(String(32), ForeignKey('downloads.download_id'), unique=True, nullable=False, index=True)
    
    # URL and destination (copied from download for redundancy)
    url = Column(String(2048), nullable=False)
    dest_path = Column(Text, nullable=False)
    
    # Headers as JSON string
    headers_json = Column(Text)
    
    # Status
    status = Column(Enum(DownloadStatus), default=DownloadStatus.COMPLETED)
    
    # Performance metrics (bytes)
    total_size = Column(BigInteger, nullable=False)
    downloaded_size = Column(BigInteger, nullable=False)
    chunk_size = Column(Integer, default=8 * 1024 * 1024)
    
    # Performance metrics (speed)
    duration_seconds = Column(Float, nullable=True)
    avg_speed_mbps = Column(Float, nullable=True)
    peak_speed_mbps = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship back to download table
    download = relationship("Download", back_populates="download")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response"""
        return {
            "id": self.id,
            "download_id": self.download_id,
            "url": self.url,
            "dest_path": self.dest_path,
            "headers_json": self.headers_json,
            "status": self.status.value if hasattr(self.status, 'value') else str(self.status),
            "total_size": self.total_size,
            "downloaded_size": self.downloaded_size,
            "chunk_size": self.chunk_size,
            "duration_seconds": self.duration_seconds,
            "avg_speed_mbps": self.avg_speed_mbps,
            "peak_speed_mbps": self.peak_speed_mbps,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


# Session factory
from seadot_backend.db.state import get_db_session
session = get_db_session()
