"""
Seadot Main API Application (FastAPI) - CONVERSION PHASE 3
Entry point untuk backend server dengan SQLAlchemy ORM integration.
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
import logging
import asyncio
import json
import uuid
from datetime import datetime

from seadot_backend.core.downloader import Downloader
from seadot_backend.db.state import init_database, get_db_session, close_all_sessions
from seadot_backend.db.service import (
    save_download_state,
    update_download_progress,
    pause_download,
    resume_download,
    stop_download,
    complete_download,
    cleanup_failed_downloads,
    get_download_by_id,
    get_all_downloads,
    get_download_history,
    get_stats
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management"""
    # Startup - Initialize database schema
    logger.info("Seadot Backend starting...")
    init_database()
    
    yield
    
    # Shutdown - Close all database sessions
    logger.info("Seadot Backend shutting down...")
    close_all_sessions()


app = FastAPI(
    title="Seadot Download Manager API",
    description="Modern async download engine dengan pause/resume & real-time updates (Phase 3)",
    version="0.3.0",
    lifespan=lifespan,
)

# CORS untuk frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production: ganti ke origin frontend saja
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DownloadState(BaseModel):
    """Download state model untuk in-memory tracking"""
    download_id: str
    url: str
    dest_path: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    progress: float = 0.0
    speed: float = 0.0
    total_size: Optional[int] = None
    downloaded_size: int = 0
    eta: Optional[int] = None
    status: str = "downloading"
    created_at: datetime = datetime.utcnow()
    completed_at: Optional[datetime] = None

class DownloadCreateRequest(BaseModel):
    url: str
    dest_path: str
    headers: Optional[Dict[str, str]] = None

class DownloadPauseRequest(BaseModel):
    pass # Request body mungkin kosong atau hanya perlu ID yang sudah di-path

class DownloadResumeRequest(BaseModel):
    pass # Request body mungkin kosong atau hanya perlu ID yang sudah di-path

class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "0.3.0"

class StatsResponse(BaseModel):
    # Struktur stat akan disesuaikan berdasarkan output get_stats()
    total_downloads: int
    completed_downloads: int
    failed_downloads: int
    total_downloaded_bytes: int


class DownloadListResponse(BaseModel):
    """Response untuk /api/downloads, list semua download."""
    downloads: List[Dict[str, Any]]

class DownloadDetailResponse(DownloadState):
    """Response detail single download, mewarisi dari DownloadState."""
    pass


class DownloadManager:
    """In-memory download manager dengan WebSocket support & DB integration"""
    
    def __init__(self):
        self.active_downloads = {}  # download_id -> DownloadState
        self._downloader = None
        self.db_session_pool = []  # Track active sessions for cleanup
    
    async def initialize(self, max_workers: int = 4, chunk_size: int = 8 * 1024 * 1024):
        """Initialize downloader dengan configuration"""
        self._downloader = Downloader(
            max_workers=max_workers,
            chunk_size=chunk_size,
            chunk_count_threshold=16
        )
        logger.info(f"Downloader initialized with {max_workers} workers")
        
    async def start_download(
        self, 
        download_id: str, 
        url: str, 
        dest_path: str,
        headers: Optional[Dict[str, str]] = None,
        pause_resume: bool = True
    ) -> dict:
        """Initiate download dengan WebSocket untuk real-time updates"""
        try:
            # Get database session
            session = get_db_session()
            self.db_session_pool.append(session)
            
            # Create state object
            initial_state = DownloadState(
                download_id=download_id,
                url=url,
                dest_path=dest_path,
                headers=headers,
                status="downloading"
            )
            
            # Save to database
            save_download_state(session, download_id, url, dest_path, headers)
            
            # Start download task di background
            async def download_task():
                try:
                    state = await self._downloader.download_streamed(
                        url, dest_path, headers=headers
                    )
                    
                    # Update progress to completion
                    if pause_resume:
                        update_download_progress(session, download_id, {
                            "total_size": state.total_size,
                            "downloaded_size": state.downloaded_size
                        })
                        
                        # Create history record via complete_download
                        complete_download(session, download_id, {
                            "total_size": state.total_size,
                            "downloaded_size": state.downloaded_size
                        })
                    
                    return state
                except Exception as e:
                    logger.error(f"Download error: {str(e)}")
                    
                    # Stop download and mark as failed
                    stop_download(session, download_id)
                    raise
            
            # Run download task
            final_state = await download_task()
            
            # Update in-memory state
            self.active_downloads[download_id] = DownloadState(
                download_id=download_id,
                url=url,
                dest_path=dest_path,
                progress=100.0,
                total_size=final_state.total_size,
                downloaded_size=final_state.downloaded_size,
                status="completed",
                completed_at=datetime.utcnow()
            )
            
            return {
                "success": True,
                "download_id": download_id,
                "url": url,
                "dest_path": dest_path,
                "status": "completed" if pause_resume else "downloading",
                "progress": final_state.progress,
                "total_size": final_state.total_size,
                "downloaded_size": final_state.downloaded_size,
                "speed": final_state.speed,
                "eta": final_state.eta
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Start download error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "download_id": download_id
            }
    
    async def get_download_state(self, download_id: str) -> dict:
        """Get current download state"""
        if download_id not in self.active_downloads:
            # Try to get from DB
            db_record = get_download_by_id(get_db_session(), download_id)
            if db_record:
                return db_record.to_dict()
            raise HTTPException(status_code=404, detail="Download not found")
        
        state = self.active_downloads[download_id]
        return {
            "download_id": state.download_id,
            "url": state.url,
            "dest_path": state.dest_path,
            "progress": state.progress,
            "speed": state.speed,
            "total_size": state.total_size,
            "downloaded_size": state.downloaded_size,
            "eta": state.eta,
            "status": state.status,
            "created_at": state.created_at.isoformat(),
            "completed_at": state.completed_at.isoformat() if state.completed_at else None
        }
    
    async def pause_download(self, download_id: str) -> dict:
        """Pause ongoing download"""
        session = get_db_session()
        
        # Try to pause in DB (if status allows)
        try:
            pause_download(session, download_id)
        except Exception as e:
            logger.error(f"Pause error: {str(e)}")
            raise HTTPException(status_code=404, detail="Download not found")
        
        return {
            "success": True,
            "download_id": download_id,
            "status": "paused"
        }
    
    async def resume_download(self, download_id: str) -> dict:
        """Resume paused download"""
        session = get_db_session()
        
        try:
            resume_download(session, download_id)
            
            # Update in-memory state
            if download_id in self.active_downloads:
                self.active_downloads[download_id].status = "downloading"
            
            return {
                "success": True,
                "download_id": download_id,
                "status": "downloading"
            }
        except Exception as e:
            logger.error(f"Resume error: {str(e)}")
            raise HTTPException(status_code=404, detail="Download not found")
    
    async def stop_download(self, download_id: str) -> dict:
        """Stop ongoing download"""
        session = get_db_session()
        
        try:
            stop_download(session, download_id)
            
            # Update in-memory state
            if download_id in self.active_downloads:
                self.active_downloads[download_id].status = "failed"
            
            return {
                "success": True,
                "download_id": download_id,
                "status": "failed"
            }
        except Exception as e:
            logger.error(f"Stop error: {str(e)}")
            raise HTTPException(status_code=404, detail="Download not found")
    
    async def cleanup_old_downloads(self, age_hours: int = 24) -> dict:
        """Cleanup old failed downloads"""
        session = get_db_session()
        
        try:
            result = cleanup_failed_downloads(session, age_hours)
            
            return {
                "success": True,
                "message": result
            }
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))


# Initialize download manager (singleton pattern)
download_manager = DownloadManager()


# ============================================================================
# WebSocket Endpoint - Real-time Progress Updates
# ============================================================================

@app.websocket("/ws/{download_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    download_id: str
):
    """WebSocket endpoint for real-time download progress"""
    await websocket.accept()
    
    try:
        # Connect to in-memory state
        if download_id not in download_manager.active_downloads:
            # Try to get from DB and create in-memory state
            session = get_db_session()
            db_record = get_download_by_id(session, download_id)
            
            if db_record:
                # Create in-memory state from DB record
                state = DownloadState(
                    download_id=db_record.download_id,
                    url=db_record.url,
                    dest_path=db_record.dest_path,
                    progress=100.0 if db_record.status == "completed" else 0.0,
                    total_size=db_record.total_size,
                    downloaded_size=db_record.downloaded_size,
                    status=db_record.status
                )
                download_manager.active_downloads[download_id] = state
            else:
                await websocket.send_json({"type": "error", "message": "Download not found"})
                await websocket.close()
                return
        
        # Send initial state
        state = download_manager.active_downloads[download_id]
        await websocket.send_json({
            "type": "connected",
            "download_id": download_id,
            "status": state.status,
            "progress": state.progress,
            "speed": state.speed
        })
        
        # Handle messages from client
        while True:
            data = await websocket.receive_text()
            
            # Parse message (can be pause/resume commands)
            try:
                message = json.loads(data)
                
                if message["type"] == "pause":
                    state.status = "paused"
                    await websocket.send_json({"type": "paused"})
                    
                elif message["type"] == "resume":
                    state.status = "downloading"
                    await websocket.send_json({"type": "resumed"})
                    
            except json.JSONDecodeError:
                # Ignore non-JSON messages (progress updates are sent by server)
                pass
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for download {download_id}")
        
    finally:
        # Clean up in-memory state on disconnect
        if download_id in download_manager.active_downloads:
            del download_manager.active_downloads[download_id]


# ============================================================================
# REST API Endpoints
# ============================================================================

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "0.3.0"}


@app.get("/api/downloads", response_model=List[Dict[str, Any]])
async def list_downloads(status_filter: Optional[str] = None):
    """Get all downloads (active + completed)"""
    session = get_db_session()
    try:
        downloads = get_all_downloads(session, status_filter or "all")
        return {"downloads": downloads}
    finally:
        session.close()


@app.get("/api/downloads/{download_id}")
async def get_download(download_id: str):
    """Get specific download by ID"""
    session = get_db_session()
    try:
        download = get_download_by_id(session, download_id)
        if download:
            return download.to_dict()
        raise HTTPException(status_code=404, detail="Download not found")
    finally:
        session.close()


@app.get("/api/downloads/history", response_model=List[Dict[str, Any]])
async def get_download_history(limit: int = 50):
    """Get recent download history"""
    session = get_db_session()
    try:
        history = get_download_history(session, limit)
        return {"history": history}
    finally:
        session.close()


@app.get("/api/stats")
async def get_stats():
    """Get download statistics"""
    session = get_db_session()
    try:
        stats = get_stats(session)
        return stats
    finally:
        session.close()


@app.post("/api/downloads/cleanup")
async def cleanup_downloads(age_hours: int = 24):
    """Cleanup old failed downloads"""
    session = get_db_session()
    try:
        result = cleanup_failed_downloads(session, age_hours)
        return {"message": result}
    finally:
        session.close()


# ============================================================================
# REST API Endpoints - Lifecycle Management
# ============================================================================

@app.post("/api/downloads/start")
async def start_download(
    download_id: str,
    url: Optional[str] = None,
    dest_path: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None
):
    """Start a new download or resume pending download"""
    session = get_db_session()
    try:
        existing = session.query(Download).filter_by(download_id=download_id).first()
        
        if not existing:
            raise HTTPException(status_code=404, detail="Download not found")
        
        # If download is pending or failed, need full URL/path info
        if existing.status in ["pending", "failed"]:
            if not url or not dest_path:
                raise HTTPException(
                    status_code=400,
                    detail="URL and dest_path required for pending/failed downloads"
                )
            
            existing.url = url
            existing.dest_path = dest_path
            existing.headers_json = json.dumps(headers) if headers else None
        
        # Create in-memory state for background task
        download_manager.create_state(download_id, existing.download_id)
        
        existing.status = "downloading"
        existing.started_at = datetime.utcnow()
        session.commit()
        
        return {"message": f"Download started: {download_id}", "download_id": download_id}
    finally:
        session.close()


@app.post("/api/downloads/pause")
async def pause_download(download_id: str):
    """Pause an ongoing download"""
    session = get_db_session()
    try:
        existing = session.query(Download).filter_by(download_id=download_id).first()
        
        if not existing:
            raise HTTPException(status_code=404, detail="Download not found")
        
        if existing.status == "completed":
            return {"message": f"Already completed: {download_id}", "download_id": download_id}
        
        existing.status = "paused"
        existing.paused_at = datetime.utcnow()
        session.commit()
        
        return {"message": f"Download paused: {download_id}", "download_id": download_id}
    finally:
        session.close()


@app.post("/api/downloads/resume")
async def resume_download(download_id: str):
    """Resume a paused download"""
    session = get_db_session()
    try:
        existing = session.query(Download).filter_by(download_id=download_id).first()
        
        if not existing:
            raise HTTPException(status_code=404, detail="Download not found")
        
        if existing.status == "completed":
            return {"message": f"Already completed: {download_id}", "download_id": download_id}
        
        existing.status = "downloading"
        existing.paused_at = None
        session.commit()
        
        return {"message": f"Download resumed: {download_id}", "download_id": download_id}
    finally:
        session.close()


@app.delete("/api/downloads/remove/{download_id}")
async def remove_download(download_id: str):
    """Remove/stops a download (mark as failed)"""
    session = get_db_session()
    try:
        existing = session.query(Download).filter_by(download_id=download_id).first()
        
        if not existing:
            raise HTTPException(status_code=404, detail="Download not found")
        
        existing.status = "failed"
        existing.completed_at = None
        session.commit()
        
        # Remove in-memory state
        download_manager.remove_state(download_id)
        
        return {"message": f"Download removed: {download_id}", "download_id": download_id}
    finally:
        session.close()


# Background task for periodic cleanup (optional)
async def periodic_cleanup():
    """Run cleanup every hour"""
    while True:
        await asyncio.sleep(3600)  # Wait 1 hour
        try:
            await download_manager.cleanup_old_downloads(age_hours=24)
        except Exception as e:
            logger.error(f"Periodic cleanup error: {str(e)}")


# Optional: enable background cleanup
# asyncio.create_task(periodic_cleanup())
