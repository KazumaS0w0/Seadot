"""
Seadot Database Models (SQLAlchemy ORM)
Models untuk Download & History tracking dengan SQLite.
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Enum, BigInteger
from sqlalchemy.dialects.sqlite import REAL as SQLiteReal
from datetime import datetime
from .service import DBService


class DownloadStatus(Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class Download:
    """Active download record dengan real-time progress"""
    
    # Tables
    __tablename__ = 'downloads'
    
    # Columns
    id = Column(Integer, primary_key=True, autoincrement=True)
    download_id = Column(String(256), unique=True, nullable=False)  # User-friendly ID (UUID v4)
    url = Column(String(1024), nullable=False)
    dest_path = Column(Text, nullable=False)
    headers_json = Column(Text)
    
    status = Column(Enum(DownloadStatus), default=DownloadStatus.PENDING)
    
    # Progress tracking (chunk-based streaming)
    total_size = Column(BigInteger, default=0)  # Total file size in bytes
    downloaded_size = Column(BigInteger, default=0)  # Downloaded bytes
    
    chunk_size = Column(Integer, default=8*1024*1024)  # 8MB chunks (dynamic)
    chunk_count_threshold = Column(Integer, default=16)  # Switch to stream mode threshold
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    paused_at = Column(DateTime, nullable=True)
    
    # Metadata
    retry_count = Column(Integer, default=0)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response"""
        return {
            "id": self.id,
            "download_id": self.download_id,
            "url": self.url,
            "dest_path": self.dest_path,
            "headers_json": self.headers_json,
            "status": self.status.value,
            "progress": (self.downloaded_size / self.total_size * 100) if self.total_size > 0 else 0,
            "downloaded_size": self.downloaded_size,
            "total_size": self.total_size,
            "chunk_size": self.chunk_size,
            "chunk_count_threshold": self.chunk_count_threshold,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "retry_count": self.retry_count
        }


class DownloadHistory:
    """Completed download history dengan detailed stats"""
    
    # Tables
    __tablename__ = 'download_history'
    
    # Columns
    id = Column(Integer, primary_key=True, autoincrement=True)
    download_id = Column(String(256), unique=True, nullable=False)  # User-friendly ID (UUID v4)
    url = Column(String(1024), nullable=False)
    dest_path = Column(Text, nullable=False)
    headers_json = Column(Text)
    
    status = Column(Enum(DownloadStatus), default=DownloadStatus.COMPLETED)
    
    # Performance metrics (chunk-based merge stats)
    total_size = Column(BigInteger, nullable=False)  # Total file size in bytes
    downloaded_size = Column(BigInteger, nullable=False)
    chunk_size = Column(Integer, default=8*1024*1024)  # Actual chunk size used
    
    # Performance metrics
    duration_seconds = Column(Float, nullable=True)  # Total download time (seconds)
    avg_speed_mbps = Column(Float, nullable=True)  # Average speed in MB/s
    peak_speed_mbps = Column(Float, nullable=True)  # Peak speed recorded
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response"""
        return {
            "id": self.id,
            "download_id": self.download_id,
            "url": self.url,
            "dest_path": self.dest_path,
            "headers_json": self.headers_json,
            "status": self.status.value,
            "total_size": self.total_size,
            "downloaded_size": self.downloaded_size,
            "chunk_size": self.chunk_size,
            "duration_seconds": self.duration_seconds,
            "avg_speed_mbps": self.avg_speed_mbps,
            "peak_speed_mbps": self.peak_speed_mbps,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


# Helper functions for service layer integration

def save_download_state(db: DBService, download_id: str, url: str, dest_path: str, headers=None):
    """Save/create download state di database"""
    session = db.get_session()
    
    existing = session.query(Download).filter_by(download_id=download_id).first()
    
    if existing:
        # Update existing
        existing.url = url
        existing.dest_path = dest_path
        if headers:
            existing.headers_json = headers
    else:
        # Create new
        download = Download(
            download_id=download_id,
            url=url,
            dest_path=dest_path,
            headers_json=headers,
            status="downloading"
        )
        session.add(download)
    
    session.commit()
    return download


def update_download_progress(db: DBService, download_id: str, progress_data: dict):
    """Update download progress (streaming mode)"""
    session = db.get_session()
    download = session.query(Download).filter_by(download_id=download_id).first()
    
    if download:
        download.total_size = progress_data.get("total_size", download.total_size)
        download.downloaded_size = progress_data.get("downloaded_size", 0)
        download.status = "downloading"
        
        session.commit()


def complete_download(db: DBService, download_id: str, final_state: dict):
    """Mark download as completed & create history record"""
    session = db.get_session()
    download = session.query(Download).filter_by(download_id=download_id).first()
    
    if download:
        # Update existing download status
        download.total_size = final_state.get("total_size", 0)
        download.downloaded_size = final_state.get("downloaded_size", 0)
        download.completed_at = datetime.utcnow()
        download.status = "completed"
        
        session.commit()
        
        # Create history record (detached from active downloads)
        history = DownloadHistory(
            download_id=download.download_id,
            url=download.url,
            dest_path=download.dest_path,
            headers_json=download.headers_json,
            total_size=download.total_size,
            downloaded_size=download.downloaded_size,
            chunk_size=download.chunk_size,
            status="completed"
        )
        
        session.add(history)
        session.commit()


def cleanup_failed_downloads(db: DBService, age_hours: int = 24):
    """Cleanup old failed downloads"""
    session = db.get_session()
    
    now = datetime.utcnow()
    cutoff_time = now.replace(microsecond=0) - __import__('datetime').timedelta(hours=age_hours)
    
    # Query for failed downloads older than X hours
    from sqlalchemy import and_
    old_downloads = session.query(Download).filter(
        Download.status == "failed",
        Download.paused_at < cutoff_time if hasattr(Download, 'paused_at') else True
    )
    
    # Delete old downloads
    for download in old_downloads:
        session.delete(download)
    
    session.commit()
    return len(old_downloads)


def get_download_by_id(db: DBService, download_id: str):
    """Get download by user-friendly ID"""
    return session = db.get_session()
    return session.query(Download).filter_by(download_id=download_id).first()


def get_all_downloads(db: DBService, status_filter=None):
    """Get all downloads (active + completed)"""
    session = db.get_session()
    
    query = session.query(Download)
    
    if status_filter:
        query = query.filter(Download.status == status_filter)
    
    return query.all()


def get_download_history(db: DBService, limit: int = 50):
    """Get recent download history (most recent first)"""
    session = db.get_session()
    
    query = session.query(DownloadHistory).order_by(DownloadHistory.created_at.desc())
    
    return query.limit(limit).all()
