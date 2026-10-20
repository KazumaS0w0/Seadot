"""
Seadot Database Models (SQLAlchemy ORM)
Models untuk Download & History tracking dengan SQLite.
"""

from enum import Enum
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, BigInteger, ForeignKey, Enum as SQLEnum
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

    id = Column(Integer, primary_key=True, autoincrement=True)
    download_id = Column(String(32), unique=True, nullable=False, index=True)
    url = Column(String(2048), nullable=False)
    dest_path = Column(Text, nullable=False)
    headers_json = Column(Text)
    status = Column(
        SQLEnum(
            DownloadStatus,
            native_enum=False,
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        default=DownloadStatus.PENDING,
        nullable=False,
    )
    total_size = Column(BigInteger, default=0)
    downloaded_size = Column(BigInteger, default=0)
    chunk_size = Column(Integer, default=8 * 1024 * 1024)
    chunk_count_threshold = Column(Integer, default=16)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    paused_at = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0)

    history_records = relationship(
        "DownloadHistory",
        back_populates="download",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        """Convert to dictionary for API response"""
        status_value = self.status.value if isinstance(self.status, DownloadStatus) else str(self.status)
        return {
            "id": self.id,
            "download_id": self.download_id,
            "url": self.url,
            "dest_path": self.dest_path,
            "headers_json": self.headers_json,
            "status": status_value,
            "progress": round((self.downloaded_size / self.total_size * 100), 2) if self.total_size > 0 else 0,
            "downloaded_size": self.downloaded_size,
            "total_size": self.total_size,
            "chunk_size": self.chunk_size,
            "chunk_count_threshold": self.chunk_count_threshold,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "paused_at": self.paused_at.isoformat() if self.paused_at else None,
            "retry_count": self.retry_count,
        }


class DownloadHistory(Base):
    """Completed download history dengan detailed stats"""

    __tablename__ = 'download_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    download_id = Column(String(32), ForeignKey('downloads.download_id'), unique=True, nullable=False, index=True)
    url = Column(String(2048), nullable=False)
    dest_path = Column(Text, nullable=False)
    headers_json = Column(Text)
    status = Column(
        SQLEnum(
            DownloadStatus,
            native_enum=False,
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        default=DownloadStatus.COMPLETED,
        nullable=False,
    )
    total_size = Column(BigInteger, nullable=False)
    downloaded_size = Column(BigInteger, nullable=False)
    chunk_size = Column(Integer, default=8 * 1024 * 1024)
    duration_seconds = Column(Float, nullable=True)
    avg_speed_mbps = Column(Float, nullable=True)
    peak_speed_mbps = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    download = relationship("Download", back_populates="history_records")

    def to_dict(self) -> dict:
        """Convert to dictionary for API response"""
        status_value = self.status.value if isinstance(self.status, DownloadStatus) else str(self.status)
        return {
            "id": self.id,
            "download_id": self.download_id,
            "url": self.url,
            "dest_path": self.dest_path,
            "headers_json": self.headers_json,
            "status": status_value,
            "total_size": self.total_size,
            "downloaded_size": self.downloaded_size,
            "chunk_size": self.chunk_size,
            "duration_seconds": self.duration_seconds,
            "avg_speed_mbps": self.avg_speed_mbps,
            "peak_speed_mbps": self.peak_speed_mbps,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }



def get_db_state(db_path: str = "seadot.db"):
    """Compatibility wrapper for tests and callers expecting a database state factory."""
    try:
        from seadot_backend.db.state import get_db_state as _get_db_state
        return _get_db_state(db_path)
    except ModuleNotFoundError:
        from db.state import get_db_state as _get_db_state
        return _get_db_state(db_path)


__all__ = ["Base", "Download", "DownloadHistory", "DownloadStatus", "get_db_state"]
