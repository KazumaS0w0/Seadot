"""Dedicated localhost port for Chrome/Edge extension capture (Phase 6)."""

from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from desktop.config import APP_HOST, APP_PORT, EXTENSION_PORT
from desktop.paths import ensure_backend_imports

ensure_backend_imports()

from seadot_backend.api.app import download_manager
from seadot_backend.db.service import save_download_state
from seadot_backend.db.state import get_db_session

logger = logging.getLogger(__name__)
_capture_tasks: set[asyncio.Task] = set()

bridge_app = FastAPI(
    title="Seadot Extension Bridge",
    version="0.5.0",
    docs_url=None,
    redoc_url=None,
)

bridge_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=r"chrome-extension://.*|edge-extension://.*|moz-extension://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CaptureRequest(BaseModel):
    url: str
    filename: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    cookies: Optional[str] = None
    dest_path: Optional[str] = None


class CaptureResponse(BaseModel):
    accepted: bool
    download_id: str
    url: str
    dest_path: str
    port: int = Field(default=EXTENSION_PORT)


def _filename_from_url(url: str) -> str:
    path = urlparse(url).path
    name = Path(path).name
    return name or "download.bin"


@bridge_app.get("/ping")
async def ping():
    return {
        "ok": True,
        "service": "seadot-extension-bridge",
        "host": APP_HOST,
        "port": EXTENSION_PORT,
        "app_port": APP_PORT,
    }


@bridge_app.get("/status")
async def status():
    return {
        "running": True,
        "downloads_continue_in_background": True,
        "app": f"http://{APP_HOST}:{APP_PORT}",
        "extension": f"http://{APP_HOST}:{EXTENSION_PORT}",
    }


@bridge_app.post("/capture", response_model=CaptureResponse)
async def capture(payload: CaptureRequest):
    url = (payload.url or "").strip()
    parsed_url = urlparse(url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.hostname:
        raise HTTPException(status_code=400, detail="url must be http or https")

    raw_filename = payload.filename or _filename_from_url(url)
    filename = Path(raw_filename.replace("\\", "/")).name or "download.bin"
    dest_path = payload.dest_path or str(Path.home() / "Downloads" / filename)
    headers = dict(payload.headers or {})
    if payload.cookies:
        headers["Cookie"] = payload.cookies

    download_id = str(uuid.uuid4())[:8]
    session = None
    try:
        session = get_db_session()
        save_download_state(session, download_id, url, dest_path)
    except Exception as exc:
        logger.exception("Could not queue extension download")
        raise HTTPException(status_code=500, detail="Could not queue download") from exc
    finally:
        if session is not None:
            session.close()

    task = download_manager.schedule_download(
        download_id,
        url,
        dest_path,
        headers=headers or None,
        persist_headers=False,
    )
    _capture_tasks.add(task)
    task.add_done_callback(_capture_tasks.discard)
    task.add_done_callback(_log_download_result)

    return CaptureResponse(
        accepted=True,
        download_id=download_id,
        url=url,
        dest_path=dest_path,
    )


def _log_download_result(task: asyncio.Task) -> None:
    if task.cancelled():
        logger.warning("Extension download task was cancelled")
        return
    error = task.exception()
    if error:
        logger.error("Extension download task failed: %s", error)
        return
    result = task.result()
    if not result.get("success"):
        logger.error(
            "Extension download %s failed: %s",
            result.get("download_id"),
            result.get("error", "unknown error"),
        )
