"""
Seadot Main API Application (FastAPI)
Entry point untuk backend server.
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException, WebSocketDisconnect
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
from seadot_backend.db.models import init_db, DownloadModel, HistoryModel
from seadot_backend.db.service import DatabaseService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management"""
    # Startup
    logger.info("Seadot Backend starting...")
    await init_db()  # Initialize DB
    
    yield
    
    # Shutdown
    logger.info("Seadot Backend shutting down...")


app = FastAPI(
    title="Seadot Download Manager API",
    description="Modern async download engine dengan pause/resume & real-time updates",
    version="0.1.0",
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


class DownloadManager:
    """In-memory download manager dengan WebSocket support"""
    
    def __init__(self):
        self.active_downloads = {}  # download_id -> DownloadState
        self._downloader = None
        self.db_service = DatabaseService()
        self._ws_connections = {}  # download_id -> ws
                
    async def initialize(self, max_workers: int = 4, chunk_size: int = 8 * 1024 * 1024):
        """Initialize downloader dengan configuration"""
        self._downloader = Downloader(
            max_workers=max_workers,
            chunk_size=chunk_size,
            chunk_count_threshold=16
        )
        
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
            # Setup downloader untuk download ini
            await self._downloader.initialize(download_id)
            
            # Create state object
            initial_state = DownloadState()
            
            # Start download task di background
            async def download_task():
                state = await self._downloader.download_streamed(
                    url, dest_path, headers=headers
                )
                
                # Save to DB
                if pause_resume:
                    db_record = DownloadModel(
                        id=download_id,
                        url=url,
                        dest_path=str(dest_path),
                        progress=state.progress,
                        total_size=state.total_size,
                        downloaded_size=state.downloaded_size,
                        eta=state.eta,
                        status="completed",
                        created_at=datetime.now(),
                        completed_at=datetime.now()
                    )
                    await self.db_service.add_download(db_record)
                
                # Close WebSocket jika ada
                if download_id in self._ws_connections:
                    ws = self._ws_connections[download_id]
                    try:
                        await ws.send_json({
                            "type": "complete",
                            "progress": state.progress,
                            "speed": state.speed,
                            "total_size": state.total_size,
                            "downloaded_size": state.downloaded_size
                        })
                        await ws.close()
                    except:
                        pass
                
                return state
            
            # Run download task dan simpan state
            final_state = await download_task()
            
            self.active_downloads[download_id] = final_state
            
            # Save to DB untuk real-time tracking
            if pause_resume:
                db_record = DownloadModel(
                    id=download_id,
                    url=url,
                    dest_path=str(dest_path),
                    progress=final_state.progress,
                    total_size=final_state.total_size,
                    downloaded_size=final_state.downloaded_size,
                    eta=final_state.eta,
                    status="completed",
                    created_at=datetime.now(),
                    completed_at=datetime.now()
                )
                await self.db_service.add_download(db_record)
            
            return {
                "success": True,
                "download_id": download_id,
                "state": {
                    "progress": round(final_state.progress, 2),
                    "speed": final_state.speed,
                    "total_size": final_state.total_size,
                    "downloaded_size": final_state.downloaded_size,
                    "eta": int(final_state.eta) if final_state.eta != float('inf') else -1,
                }
            }
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            # Cleanup WebSocket jika ada
            if download_id in self._ws_connections:
                ws = self._ws_connections[download_id]
                try:
                    await ws.send_json({"type": "error", "message": str(e)})
                    await ws.close()
                except:
                    pass
            return {"success": False, "error": str(e)}
            
    async def get_download_state(self, download_id: str) -> dict:
        """Get current download progress"""
        if download_id not in self.active_downloads:
            # Try DB untuk history
            record = await self.db_service.get_download(download_id)
            if record:
                return {
                    "download_id": record.id,
                    "url": record.url,
                    "dest_path": record.dest_path,
                    "progress": record.progress,
                    "speed": None,  # Only available for active downloads
                    "total_size": record.total_size,
                    "downloaded_size": record.downloaded_size,
                    "eta": record.eta,
                    "status": record.status,
                    "created_at": record.created_at.isoformat() if record.created_at else None,
                    "completed_at": record.completed_at.isoformat() if record.completed_at else None,
                }
            raise ValueError("Download tidak ditemukan")
            
        state = self.active_downloads[download_id]
        return {
            "download_id": download_id,
            "progress": round(state.progress, 2),
            "speed": state.speed,
            "total_size": state.total_size,
            "downloaded_size": state.downloaded_size,
            "eta": int(state.eta) if state.eta != float('inf') else -1,
        }
        
    async def stop_download(self, download_id: str) -> dict:
        """Stop download yang sedang berjalan"""
        try:
            # Close WebSocket jika ada
            if download_id in self._ws_connections:
                ws = self._ws_connections[download_id]
                await ws.close()
                
            # Get current state
            if download_id in self.active_downloads:
                state = self.active_downloads[download_id]
            else:
                state = DownloadState()
            
            # Update status ke "stopped" di DB
            if state.total_size > 0:
                db_record = await self.db_service.get_download(download_id)
                if db_record:
                    db_record.status = "stopped"
                    db_record.progress = state.progress
                    db_record.downloaded_size = state.downloaded_size
                    db_record.completed_at = datetime.now()
                    await self.db_service.update_download(db_record)
            
            # Remove dari active downloads
            if download_id in self.active_downloads:
                del self.active_downloads[download_id]
                
            return {"success": True, "message": f"Download {download_id} stopped"}
            
        except Exception as e:
            logger.error(f"Stop download error: {e}")
            return {"success": False, "error": str(e)}
        
    async def pause_download(self, download_id: str) -> dict:
        """Pause download yang sedang berjalan"""
        try:
            if download_id not in self.active_downloads:
                raise ValueError("Download tidak ditemukan")
                
            state = self.active_downloads[download_id]
            
            # Save state untuk resume nanti
            await self._downloader._save_state(state)
            
            # Update status di DB
            db_record = await self.db_service.get_download(download_id)
            if db_record:
                db_record.status = "paused"
                db_record.paused_at = datetime.now()
                await self.db_service.update_download(db_record)
                
            # Close WebSocket jika ada
            if download_id in self._ws_connections:
                ws = self._ws_connections[download_id]
                try:
                    await ws.send_json({"type": "paused"})
                    await ws.close()
                except:
                    pass
                
            return {"success": True, "message": f"Download {download_id} paused"}
            
        except Exception as e:
            logger.error(f"Pause download error: {e}")
            return {"success": False, "error": str(e)}
        
    async def resume_download(self, download_id: str) -> dict:
        """Resume download yang di-pause"""
        try:
            # Load state dari file
            loaded_state = await self._downloader._load_state()
            
            if not loaded_state:
                raise ValueError("State tidak ditemukan")
            
            # Update active downloads
            self.active_downloads[download_id] = loaded_state
            
            # Reset paused_at jika ada
            db_record = await self.db_service.get_download(download_id)
            if db_record and hasattr(db_record, 'paused_at'):
                db_record.paused_at = None
                db_record.status = "downloading"
                await self.db_service.update_download(db_record)
                
            return {"success": True, "message": f"Download {download_id} resumed"}
            
        except Exception as e:
            logger.error(f"Resume download error: {e}")
            return {"success": False, "error": str(e)}
        
    async def cleanup(self) -> None:
        """Cleanup resources"""
        if self._downloader:
            await self._downloader.cleanup()


# Initialize download manager
download_manager = DownloadManager()


# ==================== ROUTES ====================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Seadot Download Manager"}


@app.websocket("/ws/{download_id}")
async def websocket_endpoint(download_id: str, websocket):
    """WebSocket endpoint untuk real-time progress updates"""
    # Store WebSocket connection
    download_manager._ws_connections[download_id] = websocket
    
    try:
        # Send initial state
        await websocket.send_json({
            "type": "connected",
            "download_id": download_id,
            "status": "ready"
        })
        
        # Listen untuk commands dari client
        while True:
            data = await websocket.receive_text()
            command = json.loads(data)
            
            action = command.get("action")
            
            if action == "ping":
                await websocket.send_json({"type": "pong"})
                
            elif action == "cancel":
                # Stop download
                await download_manager.stop_download(download_id)
                await websocket.send_json({"type": "cancelled"})
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for {download_id}")
        if download_id in download_manager._ws_connections:
            del download_manager._ws_connections[download_id]


@app.post("/start")
async def start_download(
    download_id: str,
    url: str,
    dest_path: str,
    headers: Optional[dict] = None,
    pause_resume: bool = True
):
    """Start new download"""
    result = await download_manager.start_download(download_id, url, dest_path, headers, pause_resume)
    
    if not result["success"]:
        return {"error": result["error"]}, 400
        
    return {
        "message": "Download started",
        **result
    }


@app.get("/status/{download_id}")
async def get_download_status(download_id: str):
    """Get download progress"""
    try:
        state = await download_manager.get_download_state(download_id)
        return state
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/stop/{download_id}")
async def stop_download(download_id: str):
    """Stop running download"""
    result = await download_manager.stop_download(download_id)
    
    if not result["success"]:
        return {"error": result["error"]}, 400
        
    return result


@app.post("/pause/{download_id}")
async def pause_download(download_id: str):
    """Pause running download"""
    result = await download_manager.pause_download(download_id)
    
    if not result["success"]:
        return {"error": result["error"]}, 400
        
    return result


@app.post("/resume/{download_id}")
async def resume_download(download_id: str):
    """Resume paused download"""
    result = await download_manager.resume_download(download_id)
    
    if not result["success"]:
        return {"error": result["error"]}, 400
        
    return result


@app.get("/history")
async def get_history(limit: int = 50, offset: int = 0):
    """Get download history"""
    history = await download_manager.db_service.get_history(limit=limit, offset=offset)
    return {
        "total": len(history),
        "downloads": history
    }


@app.delete("/history/{download_id}")
async def delete_from_history(download_id: str):
    """Remove from history"""
    result = await download_manager.db_service.delete_from_history(download_id)
    if not result["success"]:
        return {"error": result["error"]}, 404
    return result


# ==================== Pydantic Models ====================

class DownloadRequest(BaseModel):
    """Model untuk request download"""
    url: str
    dest_path: str
    headers: Optional[Dict[str, str]] = None
    pause_resume: bool = True


@app.post("/start", response_model=dict)
async def start_download_v2(request: DownloadRequest):
    """Start new download (alternative endpoint dengan pydantic validation)"""
    download_id = request.url.split("/")[-1] if "/" in request.url else str(uuid.uuid4())
    
    result = await download_manager.start_download(
        download_id, 
        request.url, 
        request.dest_path, 
        request.headers,
        request.pause_resume
    )
    
    if not result["success"]:
        return {"error": result["error"]}, 400
        
    return {
        "message": "Download started",
        **result
    }
