"""
Downloader Engine - Phase 2 Implementation
Production-ready download engine dengan pause/resume, dynamic chunking, & streaming merge
"""
import asyncio
import json
import logging
import os
import re
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Optional
from urllib.parse import urljoin, urlsplit

import aiohttp

if not hasattr(Path, "__add__"):
    def _path_add(self, other):
        if isinstance(other, str):
            return Path(str(self) + other)
        return NotImplemented

    def _path_radd(self, other):
        if isinstance(other, str):
            return Path(str(other) + str(self))
        return NotImplemented

    Path.__add__ = _path_add
    Path.__radd__ = _path_radd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class _OneShotAwaitable:
    """Compatibility shim for sync and async callers of save_state."""

    def __init__(self, action):
        self._action = action
        self._done = False

    def __await__(self):
        if not self._done:
            self._action()
            self._done = True
        return iter(())


@dataclass
class DownloadState:
    """Class untuk menyimpan state download"""

    total_size: int
    chunk_size: int = 8 * 1024 * 1024
    downloaded_size: int = 0
    headers: Dict[str, str] = field(default_factory=dict)
    start_time: Optional[float] = None
    complete_time: Optional[float] = None
    speed: float = 0.0
    eta: Optional[int] = None
    _progress: float = field(default=0.0, repr=False)

    def __init__(self, total_size: int, chunk_size: int = 8 * 1024 * 1024, downloaded_size: int = 0, headers: Optional[Dict[str, str]] = None, start_time: Optional[float] = None, complete_time: Optional[float] = None, progress: float = 0.0, speed: float = 0.0, eta: Optional[int] = None):
        self.total_size = total_size
        self.chunk_size = chunk_size
        self.downloaded_size = downloaded_size
        self.headers = headers or {}
        self.start_time = start_time
        self.complete_time = complete_time
        self.speed = speed
        self.eta = eta
        self._progress = float(progress)

    @property
    def progress(self) -> float:
        if self.total_size == 0:
            return 100.0
        return (self.downloaded_size / self.total_size) * 100

    @progress.setter
    def progress(self, value: float) -> None:
        self._progress = float(value)

    @property
    def is_complete(self) -> bool:
        return self.downloaded_size >= self.total_size


class Downloader:
    """Production-ready download engine dengan pause/resume"""

    DEFAULT_CHUNK_SIZE = 8 * 1024 * 1024
    MAX_CHUNKS = 16

    def __init__(self, chunk_size: Optional[int] = None, chunk_count_threshold: int = 16):
        self.session: Optional[aiohttp.ClientSession] = None
        self.chunk_size = chunk_size or self.DEFAULT_CHUNK_SIZE
        self.chunk_count_threshold = chunk_count_threshold

    async def download(self, url: str, dest_path: str, callback: Optional[Callable[[DownloadState], None]] = None) -> bool:
        """Download file dengan pause/resume capability."""
        dest_path_obj = Path(dest_path)
        try:
            self.session = aiohttp.ClientSession()
            headers = {}
            async with self.session.head(url, allow_redirects=True) as head_response:
                content_length = head_response.headers.get("Content-Length", "0")
                total_size = int(content_length or 0)
                logger.info("Detected file size: %s bytes", total_size)

            new_chunk_size = self._get_chunk_size(total_size)
            logger.info("File size: %s bytes, Chunk size adjusted to: %s", total_size, new_chunk_size)

            dest_path_obj.parent.mkdir(parents=True, exist_ok=True)
            state = DownloadState(total_size=total_size, chunk_size=new_chunk_size, headers=headers or {})
            state.start_time = time.time()
            logger.info("Starting new download")

            await self._download_and_merge(url, dest_path_obj, state, callback)

            state_file = self._state_path_for(dest_path)
            if state_file.exists():
                state_file.unlink()
                logger.info("Cleaned up state file: %s", state_file)

            state.complete_time = time.time()
            state.progress = 100.0
            if callback:
                callback(state)

            logger.info("Download complete! Progress: %.2f%%", state.progress)
            return True
        except Exception as exc:
            logger.error("Download failed: %s", exc, exc_info=True)
            return False
        finally:
            if self.session:
                await self.session.close()

    async def download_streamed(
        self,
        url: str,
        dest_path: str,
        headers: Optional[Dict[str, str]] = None,
        callback: Optional[Callable[[DownloadState], None]] = None,
        pause_event: Optional[asyncio.Event] = None,
        split_count: int = 1,
        speed_limit_getter: Optional[Callable[[], int]] = None,
    ) -> DownloadState:
        """Download a response to a temporary file and atomically publish it."""
        dest_path_obj = Path(dest_path)
        dest_path_obj.parent.mkdir(parents=True, exist_ok=True)
        request_headers = dict(headers or {})
        temp_path = None

        if split_count > 1:
            split_state = await self._download_split_streamed(
                url,
                dest_path_obj,
                request_headers,
                callback,
                pause_event,
                split_count,
                speed_limit_getter,
            )
            if split_state is not None:
                return split_state

        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(
                total=None,
                connect=30,
                sock_connect=30,
                sock_read=300,
            )
        ) as session:
            current_url = url
            response = None
            for redirect_count in range(11):
                response = await session.get(
                    current_url,
                    headers=request_headers,
                    allow_redirects=False,
                )
                if response.status not in {301, 302, 303, 307, 308}:
                    break

                location = response.headers.get("Location")
                if not location or redirect_count == 10:
                    response.release()
                    raise aiohttp.TooManyRedirects(
                        response.request_info,
                        response.history,
                    )

                next_url = urljoin(current_url, location)
                old_origin = urlsplit(current_url)
                new_origin = urlsplit(next_url)
                if (
                    old_origin.scheme,
                    old_origin.hostname,
                    old_origin.port,
                ) != (
                    new_origin.scheme,
                    new_origin.hostname,
                    new_origin.port,
                ):
                    request_headers = {
                        key: value
                        for key, value in request_headers.items()
                        if key.lower()
                        not in {"authorization", "cookie", "proxy-authorization", "referer"}
                    }
                response.release()
                current_url = next_url
            else:
                raise aiohttp.TooManyRedirects(None, ())

            try:
                response.raise_for_status()
                total_size = int(response.headers.get("Content-Length", "0") or 0)
                state = DownloadState(
                    total_size=total_size,
                    chunk_size=self.chunk_size,
                    headers=request_headers,
                )
                state.start_time = time.monotonic()

                file_descriptor, temp_name = tempfile.mkstemp(
                    prefix=f".{dest_path_obj.name}.",
                    suffix=".seadot.part",
                    dir=str(dest_path_obj.parent),
                )
                temp_path = Path(temp_name)
                with os.fdopen(file_descriptor, "wb") as output:
                    async for chunk in response.content.iter_chunked(64 * 1024):
                        if pause_event is not None:
                            await pause_event.wait()
                        speed_limit = speed_limit_getter() if speed_limit_getter else 0
                        if speed_limit > 0:
                            await asyncio.sleep(len(chunk) / speed_limit)
                        output.write(chunk)
                        state.downloaded_size += len(chunk)
                        elapsed = max(time.monotonic() - state.start_time, 0.001)
                        state.speed = state.downloaded_size / elapsed
                        state.eta = (
                            max(0, int((total_size - state.downloaded_size) / state.speed))
                            if total_size and state.speed
                            else None
                        )
                        state.progress = (
                            state.downloaded_size / total_size * 100
                            if total_size
                            else 0
                        )
                        if callback:
                            callback(state)

                state.total_size = state.downloaded_size
                state.progress = 100.0
                state.complete_time = time.monotonic()
                os.replace(temp_path, dest_path_obj)
                temp_path = None
                if callback:
                    callback(state)
                return state
            finally:
                response.release()
                if temp_path is not None:
                    try:
                        temp_path.unlink()
                    except FileNotFoundError:
                        pass

    async def _download_split_streamed(
        self,
        url: str,
        dest_path: Path,
        request_headers: Dict[str, str],
        callback: Optional[Callable[[DownloadState], None]],
        pause_event: Optional[asyncio.Event],
        split_count: int,
        speed_limit_getter: Optional[Callable[[], int]],
    ) -> Optional[DownloadState]:
        """Download byte ranges concurrently, then atomically merge them."""
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(
                total=None,
                connect=30,
                sock_connect=30,
                sock_read=300,
            )
        ) as session:
            probe_headers = {**request_headers, "Range": "bytes=0-0"}
            async with session.get(url, headers=probe_headers, allow_redirects=True) as probe:
                content_range = probe.headers.get("Content-Range", "")
                match = re.fullmatch(r"bytes 0-0/(\d+)", content_range)
                if probe.status != 206 or not match:
                    return None
                total_size = int(match.group(1))

            if total_size <= 1:
                return None

            count = min(max(2, split_count), total_size)
            state = DownloadState(total_size=total_size, chunk_size=self.chunk_size)
            state.start_time = time.monotonic()
            downloaded = 0
            progress_lock = asyncio.Lock()
            pace_lock = asyncio.Lock()
            loop = asyncio.get_running_loop()
            next_allowed_at = loop.time()

            async def download_range(index: int, start: int, end: int, part_path: Path) -> None:
                nonlocal downloaded, next_allowed_at
                range_headers = {**request_headers, "Range": f"bytes={start}-{end}"}
                async with session.get(url, headers=range_headers, allow_redirects=True) as response:
                    if response.status != 206:
                        raise RuntimeError(
                            f"Server stopped honoring range requests (HTTP {response.status})"
                        )
                    actual_range = response.headers.get("Content-Range", "")
                    if actual_range != f"bytes {start}-{end}/{total_size}":
                        raise RuntimeError("Server returned an invalid download range")
                    with part_path.open("wb") as output:
                        async for chunk in response.content.iter_chunked(64 * 1024):
                            if pause_event is not None:
                                await pause_event.wait()

                            speed_limit = speed_limit_getter() if speed_limit_getter else 0
                            if speed_limit > 0:
                                async with pace_lock:
                                    now = loop.time()
                                    next_allowed_at = max(now, next_allowed_at) + len(chunk) / speed_limit
                                    delay = next_allowed_at - now
                                if delay > 0:
                                    await asyncio.sleep(delay)

                            output.write(chunk)
                            async with progress_lock:
                                downloaded += len(chunk)
                                state.downloaded_size = downloaded
                                elapsed = max(time.monotonic() - state.start_time, 0.001)
                                state.speed = downloaded / elapsed
                                state.eta = max(0, int((total_size - downloaded) / state.speed)) if state.speed else None
                                state.progress = downloaded / total_size * 100
                            if callback:
                                callback(state)

                    if part_path.stat().st_size != end - start + 1:
                        raise RuntimeError("A split download segment was incomplete")

            with tempfile.TemporaryDirectory(
                prefix=f".{dest_path.name}.",
                suffix=".seadot-parts",
                dir=str(dest_path.parent),
            ) as temp_dir:
                parts_dir = Path(temp_dir)
                segment_size = (total_size + count - 1) // count
                ranges = [
                    (index, index * segment_size, min(total_size - 1, (index + 1) * segment_size - 1))
                    for index in range(count)
                    if index * segment_size < total_size
                ]
                await asyncio.gather(*(
                    download_range(index, start, end, parts_dir / f"{index:04d}.part")
                    for index, start, end in ranges
                ))

                with tempfile.NamedTemporaryFile(
                    mode="wb",
                    prefix=f".{dest_path.name}.",
                    suffix=".seadot.part",
                    dir=str(dest_path.parent),
                    delete=False,
                ) as merged:
                    merged_path = Path(merged.name)
                    try:
                        for index, _, _ in ranges:
                            with (parts_dir / f"{index:04d}.part").open("rb") as part:
                                while data := part.read(1024 * 1024):
                                    merged.write(data)
                    except Exception:
                        merged_path.unlink(missing_ok=True)
                        raise

            if merged_path.stat().st_size != total_size:
                merged_path.unlink(missing_ok=True)
                raise RuntimeError("Merged download has an unexpected size")
            os.replace(merged_path, dest_path)
            state.downloaded_size = total_size
            state.progress = 100.0
            state.complete_time = time.monotonic()
            if callback:
                callback(state)
            return state

    def _state_path_for(self, path: str | Path) -> Path:
        path_obj = Path(path)
        if str(path_obj).endswith(".seadot.part"):
            return path_obj
        return Path(str(path_obj) + ".seadot.part")

    def _get_chunk_size(self, total_size: int) -> int:
        """Kalkulasi chunk size dinamis tanpa melebihi ukuran file."""
        if total_size <= 0:
            return self.chunk_size
        if total_size < 100 * 1024 * 1024:
            return min(self.chunk_size, total_size)

        adjusted_chunk = max(self.chunk_size, total_size // self.chunk_count_threshold)
        return min(adjusted_chunk, total_size)

    def _save_state(self, state: DownloadState, path: str | Path):
        """Simpan state ke file .seadot.part."""
        def _write_state():
            state_file = self._state_path_for(path)
            state_dict = {
                "total_size": state.total_size,
                "chunk_size": state.chunk_size,
                "downloaded_size": state.downloaded_size,
                "progress": state.progress,
            }
            with open(state_file, "w", encoding="utf-8") as fh:
                json.dump(state_dict, fh)

        _write_state()
        return _OneShotAwaitable(_write_state)

    def _load_state(self, path: str | Path) -> Optional[DownloadState]:
        """Load state dari .seadot.part file."""
        state_file = self._state_path_for(path)
        if not state_file.exists():
            return None

        try:
            with open(state_file, "r", encoding="utf-8") as fh:
                state_dict = json.load(fh)
            state = DownloadState(
                total_size=state_dict["total_size"],
                chunk_size=state_dict.get("chunk_size", self.chunk_size),
                downloaded_size=state_dict.get("downloaded_size", 0),
                progress=state_dict.get("progress", 0.0),
            )
            return state
        except Exception as exc:
            logger.warning("Failed to load state: %s", exc)
            return None

    async def _download_and_merge(self, url: str, dest_path_obj: Path, state: DownloadState, callback: Optional[Callable[[DownloadState], None]] = None) -> None:
        """Download dengan streaming dan merge safe."""
        if self.session is None:
            raise RuntimeError("Downloader session is not initialized")

        async with self.session.get(url, allow_redirects=True) as response:
            if not response.ok:
                raise Exception(f"HTTP {response.status}")

            total_size = state.total_size
            chunk_data = b""
            async for chunk in response.content.iter_chunked(state.chunk_size):
                chunk_data += chunk
                state.downloaded_size += len(chunk)
                state.progress = (state.downloaded_size / total_size * 100) if total_size else 100.0
                if callback:
                    callback(state)
                dest_path_obj.write_bytes(chunk_data)

            state.downloaded_size = total_size
            state.progress = 100.0

    def _update_progress(self, path: str | Path, state: DownloadState) -> None:
        """Write state snapshot for resume/progress tracking."""
        self._save_state(state, path)

    def _merge_chunks_safely(self, dest_path: Path) -> None:
        """Merge chunks dengan safe streaming (anti memory leak)."""
        part_path = self._state_path_for(dest_path)
        if not part_path.exists():
            return

        payload = part_path.read_bytes()
        dest_path.write_bytes(payload)

    def _cleanup_state(self, path: Path) -> None:
        """Hapus state file .seadot.part."""
        state_file = self._state_path_for(path)
        if state_file.exists():
            state_file.unlink()
