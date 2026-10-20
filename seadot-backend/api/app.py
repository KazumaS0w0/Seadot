"""
Seadot Main API Application (FastAPI) - CONVERSION PHASE 3
Entry point untuk backend server dengan SQLAlchemy ORM integration.
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Dict, Any
from contextlib import asynccontextmanager
import logging
import asyncio
import json
import os
import sys
import uuid
from pathlib import Path
from datetime import datetime
from urllib.parse import unquote, urlsplit

from seadot_backend.core.downloader import Downloader
from seadot_backend.db.state import init_database, get_db_session, close_all_sessions
from seadot_backend.db.models import Download, DownloadStatus
from seadot_backend.db.service import (
    save_download_state,
    update_download_progress,
    stop_download,
    complete_download,
    cleanup_failed_downloads,
    get_download_by_id,
    get_all_downloads,
    get_download_history,
    get_stats
)
from desktop.system_actions import (
    PowerActionManager,
    initialize_default_settings,
    load_settings,
    save_settings,
    set_startup_enabled,
)
from desktop.download_folders import (
    CATEGORIES,
    category_for_filename,
    ensure_download_folders,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
power_action_manager = PowerActionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management"""
    # Startup - Initialize database schema
    logger.info("Seadot Backend starting...")
    init_database()
    ensure_download_folders()
    
    yield
    
    # Shutdown - Close all database sessions
    logger.info("Seadot Backend shutting down...")
    close_all_sessions()


def _compat_test_client(self, *args, **kwargs):
    """Back-compat wrapper for older FastAPI test_client usage."""
    return TestClient(self, *args, **kwargs)


if not hasattr(FastAPI, "test_client"):
    FastAPI.test_client = _compat_test_client


app = FastAPI(
    title="Seadot Download Manager API",
    description="Modern async download engine dengan pause/resume & real-time updates (Phase 3)",
    version="0.3.0",
    lifespan=lifespan,
)
app.state.db_path = "seadot.db"


def create_app(db_path: str = "seadot.db") -> FastAPI:
    """Create a new FastAPI app bound to the specified SQLite database path."""
    app.state.db_path = db_path
    init_database(db_path)
    return app


def _get_app_db_session():
    """Get a session bound to the active app database path."""
    return get_db_session(app.state.db_path)


def _coerce_download_status(value: Optional[str]):
    """Normalize string status values to the ORM enum used by the database."""
    if value is None:
        return DownloadStatus.PENDING
    if isinstance(value, DownloadStatus):
        return value
    mapping = {
        "pending": DownloadStatus.PENDING,
        "downloading": DownloadStatus.DOWNLOADING,
        "paused": DownloadStatus.PAUSED,
        "completed": DownloadStatus.COMPLETED,
        "failed": DownloadStatus.FAILED,
    }
    status = mapping.get(str(value).strip().lower())
    if status is None:
        raise ValueError(f"Invalid status value: {value}")
    return status


@app.post("/api/v1/download/create", status_code=201)
async def create_download_v1(request: Request):
    """Compatibility POST route for tests using /api/v1/download/create."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Request body must be valid JSON")

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON payload must be an object")

    download_id = payload.get("download_id")
    url = payload.get("url")
    dest_path = payload.get("dest_path")
    if not download_id or not url or not dest_path:
        raise HTTPException(status_code=400, detail="download_id, url, and dest_path are required")

    try:
        status_value = _coerce_download_status(payload.get("status", "pending"))
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid status value")

    session = _get_app_db_session()
    try:
        existing = session.query(Download).filter_by(download_id=download_id).first()
        if existing:
            existing.url = url
            existing.dest_path = dest_path
            existing.status = status_value
            if payload.get("headers") is not None:
                existing.headers_json = json.dumps(payload["headers"]) if isinstance(payload["headers"], dict) else str(payload["headers"])
            session.commit()
            record = existing
        else:
            record = Download(
                download_id=download_id,
                url=url,
                dest_path=dest_path,
                headers_json=json.dumps(payload.get("headers")) if isinstance(payload.get("headers"), dict) else None,
                status=status_value,
            )
            session.add(record)
            session.commit()
            session.refresh(record)

        return {
            "download_id": record.download_id,
            "url": record.url,
            "dest_path": record.dest_path,
            "status": record.status.value if hasattr(record.status, "value") else str(record.status),
            "total_size": record.total_size,
            "downloaded_size": record.downloaded_size,
        }
    finally:
        session.close()


@app.get("/api/v1/download")
async def list_downloads_v1(status: str = "all"):
    session = _get_app_db_session()
    try:
        query = session.query(Download)
        if status and status != "all":
            try:
                query = query.filter(Download.status == _coerce_download_status(status))
            except ValueError:
                raise HTTPException(status_code=422, detail="Invalid status value")
        downloads = query.order_by(Download.created_at.desc()).all()
        return {"downloads": [d.to_dict() for d in downloads]}
    finally:
        session.close()


@app.post("/api/v1/download/update")
async def update_download_v1(request: Request):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Request body must be valid JSON")

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON payload must be an object")

    if "download_id" not in payload:
        raise HTTPException(status_code=400, detail="download_id is required")

    session = _get_app_db_session()
    try:
        record = session.query(Download).filter_by(download_id=payload["download_id"]).first()
        if record is None:
            raise HTTPException(status_code=404, detail="Download not found")

        if "total_size" in payload:
            record.total_size = payload["total_size"]
        if "downloaded_size" in payload:
            record.downloaded_size = payload["downloaded_size"]
        if "paused_at" in payload:
            record.paused_at = datetime.fromisoformat(payload["paused_at"]) if isinstance(payload["paused_at"], str) else payload["paused_at"]

        if record.downloaded_size >= record.total_size and record.total_size > 0:
            record.status = DownloadStatus.COMPLETED
        elif "status" in payload:
            try:
                record.status = _coerce_download_status(payload["status"])
            except ValueError:
                raise HTTPException(status_code=422, detail="Invalid status value")
        elif payload.get("paused_at") is not None:
            record.status = DownloadStatus.PAUSED
        else:
            record.status = DownloadStatus.DOWNLOADING

        session.commit()
        return {"download_id": record.download_id, "status": record.status.value if hasattr(record.status, "value") else str(record.status)}
    finally:
        session.close()

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


class SystemSettings(BaseModel):
    auto_start: bool = False
    completion_action: Literal["none", "shutdown", "sleep", "hibernate", "restart"] = "none"
    countdown_minutes: int = Field(default=2, ge=1, le=120)
    split_count: Literal[1, 2, 4, 8, 16] = 4


class CreateDownloadRequest(BaseModel):
    url: str
    filename: Optional[str] = None
    category: Optional[str] = None
    destination_folder: Optional[str] = None
    split_count: int = Field(default=4, ge=1, le=16)
    conflict_policy: Optional[Literal["overwrite", "number"]] = None


class DownloadOptionsRequest(BaseModel):
    speed_limit_bps: int = Field(default=0, ge=0, le=1_073_741_824)
    split_count: int = Field(default=4, ge=1, le=16)
    completion_action: Literal["none", "shutdown", "sleep", "hibernate", "restart"] = "none"
    countdown_minutes: int = Field(default=2, ge=1, le=120)


class DownloadManager:
    """In-memory download manager dengan WebSocket support & DB integration"""
    
    def __init__(self):
        self.active_downloads = {}  # download_id -> DownloadState
        self.download_tasks: Dict[str, asyncio.Task] = {}
        self.pause_events: Dict[str, asyncio.Event] = {}
        self.download_options: Dict[str, dict] = {}
        self._downloader = None
        self.db_session_pool = []  # Track active sessions for cleanup
    
    async def initialize(self, max_workers: int = 4, chunk_size: int = 8 * 1024 * 1024):
        """Initialize downloader dengan configuration"""
        self._downloader = Downloader(
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
        pause_resume: bool = True,
        persist_headers: bool = True,
        db_path: Optional[str] = None,
    ) -> dict:
        """Initiate download dengan WebSocket untuk real-time updates"""
        if self._downloader is None:
            await self.initialize()

        pause_event = self.pause_events.get(download_id)
        if pause_event is None:
            pause_event = asyncio.Event()
            pause_event.set()
            self.pause_events[download_id] = pause_event
        session = get_db_session(db_path or app.state.db_path)
        try:
            self.db_session_pool.append(session)

            record = get_download_by_id(session, download_id)
            if record is None:
                save_download_state(
                    session,
                    download_id,
                    url,
                    dest_path,
                    headers if persist_headers else None,
                )
                record = get_download_by_id(session, download_id)
            else:
                record.url = url
                record.dest_path = dest_path
                record.status = DownloadStatus.DOWNLOADING
                record.started_at = datetime.utcnow()
                record.completed_at = None
                if persist_headers:
                    record.headers_json = json.dumps(headers) if headers else None
                session.commit()

            state = DownloadState(
                download_id=download_id,
                url=url,
                dest_path=dest_path,
                headers=headers,
                status="downloading"
            )
            self.active_downloads[download_id] = state

            def update_state(progress_state):
                state.total_size = progress_state.total_size or None
                state.downloaded_size = progress_state.downloaded_size
                state.progress = progress_state.progress
                state.speed = progress_state.speed
                state.eta = progress_state.eta

            options = self.download_options.setdefault(
                download_id,
                {
                    "speed_limit_bps": 0,
                    "split_count": 4,
                    "completion_action": "none",
                    "countdown_minutes": 2,
                },
            )
            final_state = await self._downloader.download_streamed(
                url,
                dest_path,
                headers=headers,
                callback=update_state,
                pause_event=pause_event,
                split_count=options["split_count"],
                speed_limit_getter=lambda: options["speed_limit_bps"],
            )

            if pause_resume:
                update_download_progress(session, download_id, {
                    "total_size": final_state.total_size,
                    "downloaded_size": final_state.downloaded_size
                })
                complete_download(session, download_id, {
                    "total_size": final_state.total_size,
                    "downloaded_size": final_state.downloaded_size
                })

            state.status = "completed"
            state.progress = 100.0
            state.total_size = final_state.total_size
            state.downloaded_size = final_state.downloaded_size
            state.speed = final_state.speed
            state.eta = 0
            state.completed_at = datetime.utcnow()

            return {
                "success": True,
                "download_id": download_id,
                "url": url,
                "dest_path": dest_path,
                "status": "completed",
                "progress": final_state.progress,
                "total_size": final_state.total_size,
                "downloaded_size": final_state.downloaded_size,
                "speed": final_state.speed,
                "eta": final_state.eta
            }
            
        except HTTPException:
            raise
        except asyncio.CancelledError:
            logger.info("Download cancelled: %s", download_id)
            raise
        except Exception as e:
            logger.error(f"Start download error: {str(e)}")
            failed_session = get_db_session(db_path or app.state.db_path)
            try:
                record = get_download_by_id(failed_session, download_id)
                if record and record.status != DownloadStatus.COMPLETED:
                    record.status = DownloadStatus.FAILED
                    failed_session.commit()
            finally:
                failed_session.close()
            if download_id in self.active_downloads:
                self.active_downloads[download_id].status = "failed"
            return {
                "success": False,
                "error": str(e),
                "download_id": download_id
            }
        finally:
            session.close()
            if session in self.db_session_pool:
                self.db_session_pool.remove(session)

    def schedule_download(
        self,
        download_id: str,
        url: str,
        dest_path: str,
        headers: Optional[Dict[str, str]] = None,
        *,
        persist_headers: bool = True,
        db_path: Optional[str] = None,
    ) -> asyncio.Task:
        power_action_manager.cancel_pending()
        task = self.download_tasks.get(download_id)
        if task and not task.done():
            return task

        pause_event = asyncio.Event()
        pause_event.set()
        self.pause_events[download_id] = pause_event
        task = asyncio.create_task(
            self.start_download(
                download_id,
                url,
                dest_path,
                headers=headers,
                persist_headers=persist_headers,
                db_path=db_path,
            )
        )
        self.download_tasks[download_id] = task
        task.add_done_callback(
            lambda completed_task, key=download_id: self._download_task_done(
                key, completed_task
            )
        )
        return task

    def _download_task_done(self, download_id: str, task: asyncio.Task) -> None:
        if self.download_tasks.get(download_id) is task:
            self.download_tasks.pop(download_id, None)
        if task.cancelled():
            return
        error = task.exception()
        if error:
            logger.error("Download task %s failed: %s", download_id, error)
        state = self.active_downloads.get(download_id)
        if state is None or state.status != "paused":
            self.pause_events.pop(download_id, None)
        asyncio.create_task(self._schedule_completion_action_if_idle())

    async def _schedule_completion_action_if_idle(self) -> None:
        settings = load_settings()
        session = get_db_session(app.state.db_path)
        try:
            records = session.query(Download).all()
            if not records:
                return
            if any(
                record.status
                in {
                    DownloadStatus.PENDING,
                    DownloadStatus.DOWNLOADING,
                    DownloadStatus.PAUSED,
                }
                for record in records
            ):
                return
            if not any(record.status == DownloadStatus.COMPLETED for record in records):
                return
            completed_downloads = sorted(
                (
                    record
                    for record in records
                    if record.status == DownloadStatus.COMPLETED
                ),
                key=lambda record: record.completed_at or datetime.min,
            )
        finally:
            session.close()

        action_download_id = next(
            (
                record.download_id
                for record in reversed(completed_downloads)
                if record.download_id in self.download_options
                and self.download_options[record.download_id]["completion_action"] != "none"
            ),
            None,
        )
        action_settings = (
            self.download_options[action_download_id]
            if action_download_id
            else settings
        )
        action = action_settings["completion_action"]
        if action == "none":
            return
        await power_action_manager.schedule(
            action,
            action_settings["countdown_minutes"],
        )
        if action_download_id:
            action_settings["completion_action"] = "none"

    async def remove_state(self, download_id: str) -> None:
        task = self.download_tasks.get(download_id)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self.download_tasks.pop(download_id, None)
        self.pause_events.pop(download_id, None)
        self.active_downloads.pop(download_id, None)
    
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
        session = get_db_session(app.state.db_path)
        try:
            record = get_download_by_id(session, download_id)
            if record is None:
                raise HTTPException(status_code=404, detail="Download not found")
            if record.status == DownloadStatus.COMPLETED:
                return {"message": f"Already completed: {download_id}", "download_id": download_id}
            event = self.pause_events.get(download_id)
            if event is not None and not event.is_set():
                record.status = DownloadStatus.PAUSED
                record.paused_at = datetime.utcnow()
                session.commit()
                return {"success": True, "download_id": download_id, "status": "paused"}
            if event is None or download_id not in self.download_tasks:
                raise HTTPException(
                    status_code=409,
                    detail="No active transfer to pause",
                )
            event.clear()
            record.status = DownloadStatus.PAUSED
            record.paused_at = datetime.utcnow()
            session.commit()
            if download_id in self.active_downloads:
                self.active_downloads[download_id].status = "paused"
            return {"success": True, "download_id": download_id, "status": "paused"}
        finally:
            session.close()
    
    async def resume_download(self, download_id: str) -> dict:
        """Resume paused download"""
        session = get_db_session(app.state.db_path)
        try:
            record = get_download_by_id(session, download_id)
            if record is None:
                raise HTTPException(status_code=404, detail="Download not found")
            if record.status == DownloadStatus.COMPLETED:
                return {"message": f"Already completed: {download_id}", "download_id": download_id}
            record.status = DownloadStatus.DOWNLOADING
            record.paused_at = None
            session.commit()
            event = self.pause_events.get(download_id)
            task = self.download_tasks.get(download_id)
            if event is not None and task and not task.done():
                event.set()
            else:
                headers = json.loads(record.headers_json) if record.headers_json else None
                self.schedule_download(
                    download_id,
                    record.url,
                    record.dest_path,
                    headers=headers,
                    db_path=app.state.db_path,
                )
            if download_id in self.active_downloads:
                self.active_downloads[download_id].status = "downloading"
            return {
                "success": True,
                "download_id": download_id,
                "status": "downloading"
            }
        finally:
            session.close()
    
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


@app.get("/api/downloads/categories")
async def get_download_categories():
    """Create and return the standard folders under the user's Downloads folder."""
    try:
        return {"categories": ensure_download_folders()}
    except OSError as exc:
        logger.exception("Could not initialize download category folders")
        raise HTTPException(status_code=500, detail="Could not initialize download folders") from exc


@app.get("/api/extension/info")
async def get_extension_info():
    extension_folder = Path(__file__).resolve().parents[2] / "seadot-extension"
    if not (extension_folder / "manifest.json").is_file():
        raise HTTPException(status_code=404, detail="Seadot browser extension files were not found")
    return {"folder": str(extension_folder)}


@app.post("/api/downloads/create", status_code=201)
async def create_and_start_download(payload: CreateDownloadRequest):
    parsed_url = urlsplit(payload.url.strip())
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.hostname:
        raise HTTPException(status_code=422, detail="url must be http or https")

    raw_name = payload.filename or unquote(Path(parsed_url.path.replace("\\", "/")).name)
    filename = Path(raw_name.replace("\\", "/")).name.strip()
    if not filename or filename in {".", ".."}:
        filename = "download.bin"

    detected_category = category_for_filename(filename)
    category_id = payload.category or detected_category["id"]
    category = next((item for item in CATEGORIES if item["id"] == category_id), None)
    if category is None:
        raise HTTPException(status_code=422, detail="Unknown download category")

    try:
        category_folders = ensure_download_folders()
        default_folder = next(folder["folder"] for folder in category_folders if folder["id"] == category_id)
        destination_folder = Path(payload.destination_folder or default_folder).expanduser()
        destination_folder.mkdir(parents=True, exist_ok=True)
        dest_path_obj = destination_folder / filename
        if dest_path_obj.exists() and payload.conflict_policy == "number":
            stem, suffix = dest_path_obj.stem, dest_path_obj.suffix
            index = 1
            while dest_path_obj.exists():
                dest_path_obj = destination_folder / f"{stem} ({index}){suffix}"
                index += 1
        elif dest_path_obj.exists() and payload.conflict_policy is None:
            raise HTTPException(
                status_code=409,
                detail=f"File already exists: {dest_path_obj.name}",
            )
        elif dest_path_obj.exists() and not dest_path_obj.is_file():
            raise HTTPException(status_code=409, detail="The destination exists and is not a file")
        dest_path = str(dest_path_obj)
    except OSError as exc:
        logger.exception("Could not create download destination")
        raise HTTPException(status_code=400, detail="Could not create download destination folder") from exc

    download_id = str(uuid.uuid4())[:8]
    session = _get_app_db_session()
    try:
        save_download_state(session, download_id, payload.url.strip(), dest_path)
    except Exception as exc:
        logger.exception("Could not queue download")
        raise HTTPException(status_code=500, detail="Could not queue download") from exc
    finally:
        session.close()

    download_manager.download_options[download_id] = {
        "speed_limit_bps": 0,
        "split_count": payload.split_count,
        "completion_action": "none",
        "countdown_minutes": 2,
    }
    download_manager.schedule_download(
        download_id,
        payload.url.strip(),
        dest_path,
        db_path=app.state.db_path,
    )
    return {
        "accepted": True,
        "download_id": download_id,
        "url": payload.url.strip(),
        "filename": dest_path_obj.name,
        "category": category_id,
        "dest_path": dest_path,
        "status": "downloading",
        "split_count": payload.split_count,
    }


@app.get("/api/system/settings", response_model=SystemSettings)
async def get_system_settings():
    return initialize_default_settings()


@app.put("/api/system/settings", response_model=SystemSettings)
async def update_system_settings(settings: SystemSettings):
    previous = load_settings()
    requested = settings.model_dump()
    if requested["completion_action"] != "none" and sys.platform != "win32":
        raise HTTPException(
            status_code=501,
            detail="Automatic shutdown, sleep, hibernate, and restart are supported on Windows only.",
        )
    try:
        if requested["auto_start"] != previous["auto_start"]:
            set_startup_enabled(requested["auto_start"])
        save_settings(requested)
    except (OSError, RuntimeError) as exc:
        if requested["auto_start"] != previous["auto_start"]:
            try:
                set_startup_enabled(previous["auto_start"])
            except OSError:
                logger.exception("Could not roll back Windows startup registration")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    await power_action_manager.cancel()
    return requested


@app.get("/api/system/action")
async def get_system_action_status():
    return power_action_manager.status()


@app.post("/api/system/action/cancel")
async def cancel_system_action():
    cancelled = await power_action_manager.cancel()
    return {"cancelled": cancelled, **power_action_manager.status()}


@app.get("/api/downloads", response_model=DownloadListResponse)
async def list_downloads(status_filter: Optional[str] = None):
    """Get all downloads (active + completed)"""
    session = _get_app_db_session()
    try:
        downloads = get_all_downloads(session, status_filter or "all")
        return {"downloads": downloads}
    finally:
        session.close()


@app.get("/api/downloads/{download_id}")
async def get_download(download_id: str):
    """Get the latest state for a download, including live in-memory progress."""
    if download_id in download_manager.active_downloads:
        state = await download_manager.get_download_state(download_id)
    else:
        session = _get_app_db_session()
        try:
            download = get_download_by_id(session, download_id)
            if download is None:
                raise HTTPException(status_code=404, detail="Download not found")
            state = download.to_dict()
        finally:
            session.close()

    state.update(
        download_manager.download_options.get(
            download_id,
            {
                "speed_limit_bps": 0,
                "split_count": 4,
                "completion_action": "none",
                "countdown_minutes": 2,
            },
        )
    )
    return state


@app.put("/api/downloads/{download_id}/options")
async def update_download_options(download_id: str, options: DownloadOptionsRequest):
    session = _get_app_db_session()
    try:
        if session.query(Download).filter_by(download_id=download_id).first() is None:
            raise HTTPException(status_code=404, detail="Download not found")
    finally:
        session.close()

    manager_options = download_manager.download_options.setdefault(
        download_id,
        {
            "speed_limit_bps": 0,
            "split_count": 4,
            "completion_action": "none",
            "countdown_minutes": 2,
        },
    )
    manager_options.update(options.model_dump())
    return manager_options


@app.delete("/api/downloads/{download_id}")
async def delete_download(download_id: str, delete_file: bool = False):
    await download_manager.remove_state(download_id)
    session = _get_app_db_session()
    try:
        record = session.query(Download).filter_by(download_id=download_id).first()
        if record is None:
            raise HTTPException(status_code=404, detail="Download not found")

        deleted_path = None
        if delete_file:
            file_path = Path(record.dest_path)
            if file_path.exists():
                if not file_path.is_file():
                    raise HTTPException(
                        status_code=409,
                        detail="The download path is not a file",
                    )
                try:
                    os.remove(file_path)
                    deleted_path = str(file_path)
                except OSError as exc:
                    logger.exception("Could not delete downloaded file %s", file_path)
                    raise HTTPException(
                        status_code=500,
                        detail="Could not delete the downloaded file",
                    ) from exc

        session.delete(record)
        session.commit()
        download_manager.download_options.pop(download_id, None)
        download_manager.active_downloads.pop(download_id, None)
        return {
            "deleted": True,
            "download_id": download_id,
            "file_deleted": deleted_path is not None,
            "deleted_path": deleted_path,
        }
    except Exception:
        session.rollback()
        raise
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
    """Start a download or continue an existing paused transfer."""
    session = _get_app_db_session()
    try:
        existing = session.query(Download).filter_by(download_id=download_id).first()
        if not existing:
            raise HTTPException(status_code=404, detail="Download not found")

        if existing.status == DownloadStatus.COMPLETED:
            return {"message": f"Already completed: {download_id}", "download_id": download_id}

        if existing.status in {DownloadStatus.PENDING, DownloadStatus.FAILED}:
            url = url or existing.url
            dest_path = dest_path or existing.dest_path
            if not url or not dest_path:
                raise HTTPException(
                    status_code=400,
                    detail="URL and dest_path are required to start this download"
                )

            existing.url = url
            existing.dest_path = dest_path
            if headers is not None:
                existing.headers_json = json.dumps(headers)
        elif url is not None or dest_path is not None or headers is not None:
            if url is not None:
                existing.url = url
            if dest_path is not None:
                existing.dest_path = dest_path
            if headers is not None:
                existing.headers_json = json.dumps(headers)

        active_task = download_manager.download_tasks.get(download_id)
        pause_event = download_manager.pause_events.get(download_id)
        if active_task and not active_task.done():
            if existing.status == DownloadStatus.PAUSED and pause_event is not None:
                pause_event.set()
                existing.status = DownloadStatus.DOWNLOADING
                existing.paused_at = None
                session.commit()
                if download_id in download_manager.active_downloads:
                    download_manager.active_downloads[download_id].status = "downloading"
                return {"message": f"Download resumed: {download_id}", "download_id": download_id}
            return {"message": f"Download already running: {download_id}", "download_id": download_id}

        request_headers = json.loads(existing.headers_json) if existing.headers_json else None
        existing.status = "downloading"
        existing.started_at = datetime.utcnow()
        existing.paused_at = None
        session.commit()

        download_manager.schedule_download(
            download_id,
            existing.url,
            existing.dest_path,
            headers=request_headers,
            db_path=app.state.db_path,
        )
        return {"message": f"Download started: {download_id}", "download_id": download_id}
    finally:
        session.close()


@app.post("/api/downloads/pause")
async def pause_download(download_id: str):
    """Pause an ongoing download"""
    return await download_manager.pause_download(download_id)


@app.post("/api/downloads/resume")
async def resume_download(download_id: str):
    """Resume a paused download"""
    return await download_manager.resume_download(download_id)


@app.delete("/api/downloads/remove/{download_id}")
async def remove_download(download_id: str):
    """Remove/stops a download (mark as failed)"""
    await download_manager.remove_state(download_id)
    session = _get_app_db_session()
    try:
        existing = session.query(Download).filter_by(download_id=download_id).first()
        if not existing:
            raise HTTPException(status_code=404, detail="Download not found")
        existing.status = DownloadStatus.FAILED
        existing.completed_at = None
        session.commit()
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
