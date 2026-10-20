"""Background uvicorn processes for the desktop API and extension bridge."""

from __future__ import annotations

import logging
import socket
import threading
import time
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from desktop.config import APP_HOST, APP_PORT, EXTENSION_PORT
from desktop.paths import FRONTEND_DIST

logger = logging.getLogger(__name__)


def _run_uvicorn(app: FastAPI, host: str, port: int) -> uvicorn.Server:
    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level="info",
        access_log=False,
    )
    server = uvicorn.Server(config)
    server.install_signal_handlers = False
    thread = threading.Thread(target=server.run, name=f"uvicorn-{port}", daemon=True)
    thread.start()
    return server


def wait_for_port(host: str, port: int, timeout: float = 12.0) -> None:
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.4):
                return
        except OSError as exc:
            last_error = exc
            time.sleep(0.15)
    raise TimeoutError(f"Port {host}:{port} did not open ({last_error})")


def port_is_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.3):
            return True
    except OSError:
        return False


def attach_frontend(app: FastAPI) -> Path | None:
    if FRONTEND_DIST.exists():
        app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="ui")
        logger.info("Serving UI from %s", FRONTEND_DIST)
        return FRONTEND_DIST
    return None


def start_app_server(app: FastAPI):
    attach_frontend(app)
    server = _run_uvicorn(app, APP_HOST, APP_PORT)
    wait_for_port(APP_HOST, APP_PORT)
    logger.info("Desktop API listening on http://%s:%s", APP_HOST, APP_PORT)
    return server


def start_extension_server(app: FastAPI):
    server = _run_uvicorn(app, APP_HOST, EXTENSION_PORT)
    wait_for_port(APP_HOST, EXTENSION_PORT)
    logger.info("Extension bridge listening on http://%s:%s", APP_HOST, EXTENSION_PORT)
    return server
