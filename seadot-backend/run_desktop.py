"""
Seadot Desktop (Phase 5)
Native window + system tray + local extension port.

  python run_desktop.py
  python run_desktop.py --headless
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from desktop.config import APP_HOST, APP_PORT, EXTENSION_PORT, UI_URL
from desktop.paths import FRONTEND_DIST, FRONTEND_ROOT, ensure_backend_imports
from desktop.servers import port_is_open, start_app_server, start_extension_server

ensure_backend_imports()


def setup_logging() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("seadot.desktop")


def resolve_ui_url() -> str:
    if UI_URL:
        return UI_URL
    if FRONTEND_DIST.exists():
        return f"http://{APP_HOST}:{APP_PORT}/"
    if port_is_open("127.0.0.1", 5173):
        return "http://127.0.0.1:5173/"
    return f"http://{APP_HOST}:{APP_PORT}/"


def start_services(logger: logging.Logger):
    from desktop.system_actions import initialize_default_settings
    from desktop.download_folders import ensure_download_folders

    initialize_default_settings()
    ensure_download_folders()

    from seadot_backend.api.app import app
    from desktop.extension_bridge import bridge_app

    start_app_server(app)
    start_extension_server(bridge_app)
    ui_url = resolve_ui_url()
    logger.info("UI url: %s", ui_url)
    logger.info("App API: http://%s:%s", APP_HOST, APP_PORT)
    logger.info("Extension port: http://%s:%s", APP_HOST, EXTENSION_PORT)
    logger.info("Frontend dist: %s", FRONTEND_DIST if FRONTEND_DIST.exists() else "not built")
    logger.info("Frontend source: %s", FRONTEND_ROOT)
    return ui_url


def run_headless(logger: logging.Logger) -> int:
    start_services(logger)
    logger.info("Headless mode: servers are up. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping headless desktop servers")
        return 0


def run_gui(logger: logging.Logger) -> int:
    import webview

    ui_url = start_services(logger)
    from desktop.tray import TrayController
    from desktop.window import DesktopWindowApi, create_window, show_existing_window

    stopping = {"done": False}

    def quit_app():
        if stopping["done"]:
            return
        stopping["done"] = True
        logger.info("Quit requested from tray")
        try:
            webview.stop()
        except Exception:
            pass
        os._exit(0)

    tray = TrayController(on_show=show_existing_window, on_quit=quit_app)
    tray.start()
    desktop_api = DesktopWindowApi(ui_url)
    create_window(ui_url, desktop_api)

    gui = "edgechromium" if sys.platform == "win32" else None
    debug = os.getenv("SEADOT_DEBUG", "false").lower() == "true"

    def handle_sigint(signum, frame):
        quit_app()

    try:
        signal.signal(signal.SIGINT, handle_sigint)
    except Exception:
        pass

    logger.info("Native window starting (close hides to tray)")
    webview.start(gui=gui, debug=debug)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Seadot desktop shell")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Start local ports without a native window (for tests)",
    )
    args = parser.parse_args()
    logger = setup_logging()
    logger.info("Seadot Desktop Phase 5")
    if args.headless:
        return run_headless(logger)
    return run_gui(logger)


if __name__ == "__main__":
    raise SystemExit(main())
