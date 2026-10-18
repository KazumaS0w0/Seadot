"""
Seadot Database Service Layer (SQLAlchemy ORM Pattern)
Repository pattern dengan session-injected approach untuk operasi database.
"""

from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
import uuid
from .models import Download, DownloadHistory, DownloadStatus, Base


# ============================================================================
# Utility Functions (ID Generation)
# ============================================================================

def generate_download_id(session) -> str:
    """Generate unique download ID (UUID v4)"""
    return str(uuid.uuid4())[:8]  # Short user-friendly ID


# ============================================================================
# CRUD Operations - Active Downloads (Download Table)
# ============================================================================

def save_download_state(session, download_id: str, url: str, dest_path: str, headers=None):
    """Save/create download state di database"""
    existing = session.query(Download).filter_by(download_id=download_id).first()
    
    if existing:
        # Update existing
        existing.url = url
        existing.dest_path = dest_path
        if headers:
            existing.headers_json = json.dumps(headers) if isinstance(headers, dict) else headers
    else:
        # Create new download record
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


def update_download_progress(session, download_id: str, progress_data: dict):
    """Update download progress (streaming mode - zero-latency updates)"""
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


def pause_download(session, download_id: str):
    """Pause download & save state"""
    download = session.query(Download).filter_by(download_id=download_id).first()
    
    if download and download.status in ["downloading", "paused"]:
        now = datetime.utcnow()
        download.status = "paused"
        download.paused_at = now
        
        session.commit()


def resume_download(session, download_id: str):
    """Resume paused download"""
    download = session.query(Download).filter_by(download_id=download_id).first()
    
    if download and download.status == "paused":
        download.status = "downloading"
        download.paused_at = None
        download.completed_at = None
        
        session.commit()


def stop_download(session, download_id: str):
    """Stop download & mark as failed"""
    download = session.query(Download).filter_by(download_id=download_id).first()
    
    if download and download.status in ["downloading", "paused"]:
        now = datetime.utcnow()
        download.status = "failed"
        download.completed_at = None
        
        session.commit()


def complete_download(session, download_id: str, final_state: dict):
    """Mark download as completed & create history record"""
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
        chunk_size = getattr(download, 'chunk_size', 8*1024*1024)
        duration = (download.completed_at - download.started_at).total_seconds() if download.completed_at and download.started_at else None
        avg_speed = downloaded_size / (duration * 1024 * 1024) if duration else None
        
        history = DownloadHistory(
            download_id=download.download_id,
            url=download.url,
            dest_path=download.dest_path,
            headers_json=download.headers_json,
            total_size=total_size,
            downloaded_size=downloaded_size,
            chunk_size=chunk_size,
            status="completed",
            duration_seconds=duration,
            avg_speed_mbps=avg_speed,
            peak_speed_mbps=None  # Can be added later via metrics collection
        )
        
        session.add(history)
        session.commit()


def cleanup_failed_downloads(session, age_hours: int = 24):
    """Cleanup old failed downloads"""
    now = datetime.utcnow()
    cutoff_time = (now - __import__('datetime').timedelta(hours=age_hours)).isoformat()
    
    # Delete failed downloads older than X hours
    query = """
        DELETE FROM downloads 
        WHERE status = 'failed' AND (paused_at < :cutoff_time OR paused_at IS NULL)
    """
    session.execute(text(query), {"cutoff_time": cutoff_time})
    session.commit()
    
    return "Cleanup completed"


# ============================================================================
# Query Functions - API Responses
# ============================================================================

def get_download_by_id(session, download_id: str):
    """Get download by user-friendly ID"""
    return session.query(Download).filter_by(download_id=download_id).first()


def get_all_downloads(session, status_filter: Optional[str] = None):
    """Get all downloads (active + completed) with optional status filter"""
    query = session.query(Download)
    
    if status_filter and status_filter != "all":
        query = query.filter(Download.status == status_filter)
    
    results = query.order_by(Download.created_at.desc()).all()
    
    return [d.to_dict() for d in results]


def get_download_history(session, limit: int = 50):
    """Get recent download history (most recent first)"""
    query = session.query(DownloadHistory).order_by(DownloadHistory.created_at.desc())
    
    results = query.limit(limit).all()
    
    return [h.to_dict() for h in results]


def get_stats(session):
    """Get download statistics (for dashboard)"""
    # Active downloads count
    active_count = session.query(Download).filter(
        Download.status.in_([DownloadStatus.DOWNLOADING.value, DownloadStatus.PAUSED.value])
    ).count()
    
    # Completed downloads count (from history table)
    completed_count = session.query(DownloadHistory).count()
    
    # Total downloaded size (from completed history only)
    total_downloaded = sum(h.downloaded_size for h in session.query(DownloadHistory).filter(
        DownloadHistory.status == DownloadStatus.COMPLETED.value
    ).all())
    
    # Recent activity
    recent_downloads = get_download_history(session, limit=5)
    
    return {
        "active_downloads": active_count,
        "completed_downloads": completed_count,
        "total_downloaded_bytes": total_downloaded,
        "recent_downloads": recent_downloads
    }


# ============================================================================
# WebSocket Event Handlers (Real-time Updates)
# ============================================================================

def on_download_progress(downloader_id: str, progress_data: dict):
    """Prepare WebSocket payload for download progress updates"""
    payload = {
        "type": "progress",
        "data": progress_data
    }
    return payload


def on_download_completed(downloader_id: str, final_state: dict):
    """Prepare WebSocket payload for download completion"""
    payload = {
        "type": "completed",
        "data": final_state
    }
    return payload


def on_download_error(downloader_id: str, error_msg: str, status_code: int):
    """Prepare WebSocket payload for download errors"""
    payload = {
        "type": "error",
        "data": {
            "message": error_msg,
            "status_code": status_code
        }
    }
    return payload


def on_download_paused(downloader_id: str, state: dict):
    """Prepare WebSocket payload for pause event"""
    payload = {
        "type": "paused",
        "data": state
    }
    return payload


def on_download_resumed(downloader_id: str):
    """Prepare WebSocket payload for resume event"""
    payload = {
        "type": "resumed"
    }
    return payload
