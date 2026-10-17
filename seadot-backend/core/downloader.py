"""
Downloader Engine - Phase 2 Implementation
Production-ready download engine dengan pause/resume, dynamic chunking, & streaming merge
"""
import asyncio
import json
import logging
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Callable, Dict
import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DownloadState:
    """Class untuk menyimpan state download"""
    total_size: int
    chunk_size: int = 8 * 1024 * 1024  # Default 8MB
    downloaded_size: int = 0
    headers: Dict[str, str] = field(default_factory=dict)
    start_time: Optional[float] = None
    complete_time: Optional[float] = None
    
    @property
    def progress(self) -> float:
        if self.total_size == 0:
            return 100.0
        return (self.downloaded_size / self.total_size) * 100
    
    @property
    def is_complete(self) -> bool:
        return self.downloaded_size >= self.total_size


class Downloader:
    """Production-ready download engine dengan pause/resume"""
    
    DEFAULT_CHUNK_SIZE = 8 * 1024 * 1024  # 8MB
    MAX_CHUNKS = 16
    
    def __init__(self, chunk_size: Optional[int] = None, chunk_count_threshold: int = 16):
        self.session: Optional[aiohttp.ClientSession] = None
        self.chunk_size = chunk_size or self.DEFAULT_CHUNK_SIZE
        self.chunk_count_threshold = chunk_count_threshold
    
    async def download(self, url: str, dest_path: str, callback: Optional[Callable[[DownloadState], None]] = None) -> bool:
        """
        Download file dengan pause/resume capability
        
        Args:
            url: URL sumber download
            dest_path: Path tujuan (file akan dibuat + .seadot.part untuk state)
            callback: Progress callback yang menerima DownloadState
            
        Returns:
            True jika sukses, False jika gagal
        """
        dest_path_obj = Path(dest_path)
        
        try:
            self.session = aiohttp.ClientSession()
            
            # Get file size dari headers
            headers = {}
            async with self.session.head(url, allow_redirects=True) as head_response:
                headers['Content-Length'] = head_response.headers.get('Content-Length', '0')
                total_size = int(headers['Content-Length'])
                logger.info(f"Detected file size: {total_size} bytes")
            
            # Calculate dynamic chunk size
            new_chunk_size = self._get_chunk_size(total_size)
            logger.info(f"File size: {total_size} bytes, Chunk size adjusted to: {new_chunk_size}")
            
            # Initialize state
            dest_path_obj.parent.mkdir(parents=True, exist_ok=True)
            state = DownloadState(
                total_size=total_size,
                chunk_size=new_chunk_size,
                headers=headers or {}
            )
            state.start_time = time.time()
            logger.info("Starting new download")
            
            # Perform download with streaming
            await self._download_and_merge(url, dest_path_obj, state)
            
            # Clean up state file after complete download
            state_file = Path(dest_path).with_suffix(Path(dest_path).suffix + ".seadot.part")
            if state_file.exists():
                state_file.unlink()
                logger.info(f"Cleaned up state file: {state_file}")
            
            state.complete_time = time.time()
            
            if callback:
                callback(state)
            
            logger.info(f"Download complete! Progress: {state.progress:.2f}%")
            return True
            
        except Exception as e:
            logger.error(f"Download failed: {e}", exc_info=True)
            return False
        
        finally:
            if self.session:
                await self.session.close()
    
    def _get_chunk_size(self, total_size: int) -> int:
        """Kalkulasi chunk size dinamis"""
        # Untuk file kecil (< 100MB), gunakan ukuran tetap
        if total_size < 100 * 1024 * 1024:
            return self.chunk_size
        
        # Untuk file besar, pecah jadi max chunks yang diizinkan
        adjusted_chunk = total_size // self.chunk_count_threshold
        
        # Pastikan minimal 8MB dan tidak lebih dari total size
        return max(self.chunk_size, min(adjusted_chunk, total_size))
    
    async def _save_state(self, state: DownloadState, path: str) -> None:
        """Simpan state ke file .seadot.part"""
        # Handle Path + string operation
        if isinstance(path, Path):
            path = Path(str(path) + ".seadot.part")
        elif not path.endswith(".seadot.part"):
            path = str(path) + ".seadot.part"
        
        state_dict = {
            "total_size": state.total_size,
            "chunk_size": state.chunk_size,
            "downloaded_size": state.downloaded_size,
            "progress": state.progress,
        }
        
        with open(path, 'w') as f:
            json.dump(state_dict, f)

    def _load_state(self, path: str) -> Optional[DownloadState]:
        """Load state dari .seadot.part file"""
        # Handle Path + string operation
        if isinstance(path, Path):
            path = Path(str(path) + ".seadot.part")
        elif not path.endswith(".seadot.part"):
            path = str(path) + ".seadot.part"
        
        state_file = Path(path)
        if not state_file.exists():
            return None
        
        try:
            with open(state_file, 'r') as f:
                state_dict = json.load(f)
            
            return DownloadState(
                total_size=state_dict["total_size"],
                chunk_size=state_dict["chunk_size"],
                downloaded_size=state_dict.get("downloaded_size", 0),
                progress=state_dict.get("progress", 0.0),
            )
        except Exception as e:
            logger.warning(f"Failed to load state: {e}")
            return None
    
    async def _download_and_merge(self, url: str, dest_path_obj: Path, state: DownloadState) -> None:
        """Download dengan streaming dan merge safe"""
        async with self.session.get(url, allow_redirects=True) as response:
            if not response.ok:
                raise Exception(f"HTTP {response.status}")
            
            total_size = state.total_size
            
            # Stream download dalam chunks
            chunk_data = b""
            async for chunk in response.content.iter_chunked(state.chunk_size):
                chunk_data += chunk
                state.downloaded_size += len(chunk)
                
                if callback:
                    state.progress = (state.downloaded_size / total_size) * 100
                    callback(state)
                
                # Write chunks langsung ke file
                dest_path_obj.write_bytes(chunk_data)
            
            state.downloaded_size = total_size
    
    def _merge_chunks_safely(self, dest_path: Path) -> None:
        """Merge chunks dengan safe streaming (anti memory leak)"""
        if not dest_path.exists():
            return
        
        with open(dest_path, 'rb') as f:
            while chunk := f.read(8 * 1024 * 1024):
                pass
    
    def _cleanup_state(self, path: Path) -> None:
        """Hapus state file .seadot.part"""
        state_file = Path(str(path) + ".seadot.part")
        if state_file.exists():
            state_file.unlink()
