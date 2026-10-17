"""
Seadot Database Service Layer (Repository Pattern)
Abstraction untuk operasi database dengan SQLite + WebSocket real-time streaming.
"""

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, text, and_
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
import uuid
from .models import Base, Download, DownloadHistory, DownloadStatus


class DBService:
    """Database service dengan singleton pattern + WebSocket event streaming"""
    
    _instance = None
    session_local = None
    
    def __init__(self, db_path: str = "../seadot.db"):
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        
        # Create tables if not exist
        Base.metadata.create_all(bind=self.engine)
        
    @classmethod
    def get_session(cls, db_path: Optional[str] = None):
        """Get session factory"""
        cls.db_path = db_path or cls.db_path
        cls.engine = create_engine(f"sqlite:///{cls.db_path}", echo=False)
        cls.session_local = sessionmaker(bind=cls.engine)
        return cls.session_local
    
    def get_session(self):
        """Create new session (connection pooling enabled)"""
        return self.session_local()


# ============================================================================
# State Management Functions (Download Lifecycle)
# ============================================================================

def generate_download_id() -> str:
    """Generate unique download ID (UUID v4)"""
    return str(uuid.uuid4())[:8]  # Short user-friendly ID


def save_download_state(db: DBService, download_id: str, url: str, dest_path: str, headers=None):
    """Save/create download state di database"""
    session = db.get_session()
    
    existing = session.query(Download).filter_by(download_id=download_id).first()
    
    if existing:
        # Update existing
        existing.url = url
        existing.dest_path = dest_path
        if headers:
            existing.headers_json = json.dumps(headers) if isinstance(headers, dict) else headers
    else:
        # Create new
        download = Download(
            download_id=download_id,
            url=url,
            dest_path=dest_path,
            headers_json=json.dumps(headers) if headers else None,
            status="downloading"
        )
        session.add(download)
    
    session.commit()
    return download


def update_download_progress(db: DBService, download_id: str, progress_data: dict):
    """Update download progress (streaming mode - zero-latency updates)"""
    session = db.get_session()
    download = session.query(Download).filter_by(download_id=download_id).first()
    
    if download:
        # Update progress with minimal overhead
        total_size = progress_data.get("total_size", 0)
        downloaded_size = progress_data.get("downloaded_size", 0)
        
        # Only update if values changed (optimization)
        if total_size != download.total_size or downloaded_size != download.downloaded_size:
            download.total_size = total_size
            download.downloaded_size = downloaded_size
            download.status = "downloading"
            
            session.commit()


def pause_download(db: DBService, download_id: str):
    """Pause download & save state"""
    session = db.get_session()
    download = session.query(Download).filter_by(download_id=download_id).first()
    
    if download and download.status in ["downloading", "paused"]:
        now = datetime.utcnow().isoformat()
        download.status = "paused"
        download.paused_at = now
        
        session.commit()


def resume_download(db: DBService, download_id: str):
    """Resume paused download"""
    session = db.get_session()
    download = session.query(Download).filter_by(download_id=download_id).first()
    
    if download and download.status == "paused":
        now = datetime.utcnow()
        download.status = "downloading"
        download.paused_at = None
        download.completed_at = None
        
        session.commit()


def stop_download(db: DBService, download_id: str):
    """Stop download & mark as failed"""
    session = db.get_session()
    download = session.query(Download).filter_by(download_id=download_id).first()
    
    if download and download.status in ["downloading", "paused"]:
        now = datetime.utcnow()
        download.status = "failed"
        download.completed_at = None
        
        session.commit()


def complete_download(db: DBService, download_id: str, final_state: dict):
    """Mark download as completed & create history record"""
    session = db.get_session()
    download = session.query(Download).filter_by(download_id=download_id).first()
    
    if download and download.status != "failed":
        # Update existing download status
        total_size = final_state.get("total_size", 0)
        downloaded_size = final_state.get("downloaded_size", 0)
        
        download.total_size = total_size
        download.downloaded_size = downloaded_size
        download.completed_at = datetime.utcnow()
        download.status = "completed"
        
        session.commit()
        
        # Create history record (detached from active downloads)
        history = DownloadHistory(
            download_id=download.download_id,
            url=download.url,
            dest_path=download.dest_path,
            headers_json=download.headers_json,
            total_size=total_size,
            downloaded_size=downloaded_size,
            chunk_size=download.chunk_size if hasattr(download, 'chunk_size') else 8*1024*1024,
            status="completed",
            duration_seconds=(download.completed_at - download.started_at).total_seconds() if download.completed_at and download.started_at else None,
            avg_speed_mbps=downloaded_size / (download.completed_at - download.started_at) / 1024 / 1024 if download.completed_at != download.started_at else None,
            peak_speed_mbps=None  # Can be added later via metrics collection
        )
        
        session.add(history)
        session.commit()


def cleanup_failed_downloads(db: DBService, age_hours: int = 24):
    """Cleanup old failed downloads"""
    from sqlalchemy import text
    
    session = db.get_session()
    
    now = datetime.utcnow()
    cutoff_time = (now - __import__('datetime').timedelta(hours=age_hours)).isoformat()
    
    # Query for failed downloads older than X hours
    query = """
        DELETE FROM downloads 
        WHERE status = 'failed' AND paused_at < :cutoff_time OR paused_at IS NULL
    """
    session.execute(text(query), {"cutoff_time": cutoff_time})
    session.commit()
    
    return "Cleanup completed"


# ============================================================================
# Query Functions (API Responses)
# ============================================================================

def get_download_by_id(db: DBService, download_id: str):
    """Get download by user-friendly ID"""
    session = db.get_session()
    return session.query(Download).filter_by(download_id=download_id).first()


def get_all_downloads(db: DBService, status_filter: Optional[str] = None):
    """Get all downloads (active + completed) with optional status filter"""
    session = db.get_session()
    
    query = session.query(Download)
    
    if status_filter and status_filter != "all":
        query = query.filter(Download.status == status_filter)
    
    results = query.order_by(Download.created_at.desc()).all()
    
    return [d.to_dict() for d in results]


def get_download_history(db: DBService, limit: int = 50):
    """Get recent download history (most recent first)"""
    session = db.get_session()
    
    query = session.query(DownloadHistory).order_by(DownloadHistory.created_at.desc())
    
    results = query.limit(limit).all()
    
    return [h.to_dict() for h in results]


def get_stats(db: DBService):
    """Get download statistics (for dashboard)"""
    session = db.get_session()
    
    # Active downloads count
    active_query = session.query(Download).filter(Download.status.in_([DownloadStatus.DOWNLOADING.value, DownloadStatus.PAUSED.value]))
    active_count = active_query.count()
    
    # Completed downloads count
    completed_query = session.query(DownloadHistory)
    completed_count = completed_query.count()
    
    # Total downloaded size
    history_query = session.query(DownloadHistory).filter(DownloadHistory.status == DownloadStatus.COMPLETED.value)
    total_downloaded = sum(h.downloaded_size for h in history_query.all())
    
    # Recent activity
    recent_downloads = get_download_history(db, limit=5)
    
    return {
        "active_downloads": active_count,
        "completed_downloads": completed_count,
        "total_downloaded_bytes": total_downloaded,
        "recent_downloads": recent_downloads
    }


# ============================================================================
# WebSocket Event Handlers (Real-time Updates)
# ============================================================================

def on_download_progress(downloader_id: str, progress_data: dict, websocket=None):
    """WebSocket handler for download progress updates"""
    if websocket and hasattr(websocket, "send_text"):
        payload = {
            "type": "progress",
            "data": progress_data
        }
        try:
            websocket.send_json(payload)
        except Exception as e:
            print(f"WebSocket send failed: {e}")


def on_download_completed(downloader_id: str, final_state: dict, websocket=None):
    """WebSocket handler for download completion"""
    if websocket and hasattr(websocket, "send_text"):
        payload = {
            "type": "completed",
            "data": final_state
        }
        try:
            websocket.send_json(payload)
        except Exception as e:
            print(f"WebSocket send failed: {e}")


def on_download_error(downloader_id: str, error_msg: str, status_code: int, websocket=None):
    """WebSocket handler for download errors"""
    if websocket and hasattr(websocket, "send_text"):
        payload = {
            "type": "error",
            "data": {
                "message": error_msg,
                "status_code": status_code
            }
        }
        try:
            websocket.send_json(payload)
        except Exception as e:
            print(f"WebSocket send failed: {e}")


def on_download_paused(downloader_id: str, state: dict, websocket=None):
    """WebSocket handler for pause event"""
    if websocket and hasattr(websocket, "send_text"):
        payload = {
            "type": "paused",
            "data": state
        }
        try:
            websocket.send_json(payload)
        except Exception as e:
            print(f"WebSocket send failed: {e}")


def on_download_resumed(downloader_id: str, websocket=None):
    """WebSocket handler for resume event"""
    if websocket and hasattr(websocket, "send_text"):
        payload = {
            "type": "resumed"
        }
        try:
            websocket.send_json(payload)
        except Exception as e:
            print(f"WebSocket send failed: {e}")
