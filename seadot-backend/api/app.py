"""
Seadot Main API Application (FastAPI)
Entry point untuk backend server.
"""

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import asyncio

from ..core.downloader import Downloader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management"""
    # Startup
    logger.info("Seadot Backend starting...")
    
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
    """In-memory download manager (untuk MVP, bisa diganti dengan DB-backed queue nanti)"""
    
    def __init__(self):
        self.active_downloads = {}  # download_id -> DownloadState
        self._downloader = Downloader(max_workers=4, chunk_size=8*1024*1024)
        
    async def start_download(
        self, 
        download_id: str, 
        url: str, 
        dest_path: str,
        headers=None
    ) -> dict:
        """Initiate download"""
        try:
            state = await self._downloader.download(url, dest_path, headers=headers)
            self.active_downloads[download_id] = state
            
            return {
                "success": True,
                "download_id": download_id,
                "state": {
                    "progress": round(state.progress, 2),
                    "speed": state.speed,
                    "total_size": state.total_size,
                    "downloaded_size": state.downloaded_size,
                    "eta": int(state.eta) if state.eta != float('inf') else -1,
                }
            }
        except Exception as e:
            logger.error(f"Download error: {e}")
            return {"success": False, "error": str(e)}
            
    async def get_download_state(self, download_id: str) -> dict:
        """Get current download state"""
        if download_id not in self.active_downloads:
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


# Initialize download manager
download_manager = DownloadManager()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Seadot Download Manager"}


@app.post("/start")
async def start_download(
    download_id: str,
    url: str,
    dest_path: str,
    headers: dict = None
):
    """Start new download"""
    result = await download_manager.start_download(download_id, url, dest_path, headers)
    
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
        return {"error": str(e)}, 404


@app.post("/remove/{download_id}")
async def remove_download(download_id: str):
    """Remove from queue"""
    if download_id in download_manager.active_downloads:
        del download_manager.active_downloads[download_id]
    return {"message": f"Download {download_id} removed"}

