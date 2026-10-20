"""Native desktop window via pywebview."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import uuid
from typing import Optional
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import webbrowser

import webview

from desktop.config import WINDOW_HEIGHT, WINDOW_TITLE, WINDOW_WIDTH

logger = logging.getLogger(__name__)
_main_window: Optional[webview.Window] = None


class DesktopWindowApi:
    """Open and close auxiliary native windows from the frontend."""

    def __init__(self, ui_url: str) -> None:
        self.ui_url = ui_url
        self.windows: dict[str, webview.Window] = {}

    def open_download_confirmation(self, initial_url: str = "") -> str:
        return self._open_auxiliary_window(
            "confirm",
            "Confirm download",
            {"url": initial_url},
        )

    def open_download_details(self, download_id: str) -> str:
        return self._open_auxiliary_window(
            "details",
            "Download details",
            {"id": download_id},
        )

    def close_window(self, window_id: str) -> None:
        window = self.windows.pop(window_id, None)
        if window is not None:
            window.destroy()

    def open_extension_manager(self, browser: str) -> bool:
        browser_config = {
            "chrome": (
                "chrome.exe",
                "Google\\Chrome\\Application\\chrome.exe",
                "chrome://extensions/",
            ),
            "edge": (
                "msedge.exe",
                "Microsoft\\Edge\\Application\\msedge.exe",
                "edge://extensions/",
            ),
            "firefox": (
                "firefox.exe",
                "Mozilla Firefox\\firefox.exe",
                "about:debugging#/runtime/this-firefox",
            ),
            "opera": (
                "opera.exe",
                "Opera\\launcher.exe",
                "opera://extensions/",
            ),
        }
        if browser not in browser_config:
            raise ValueError("Browser must be chrome, edge, firefox, or opera")

        executable_name, relative_path, manager_url = browser_config[browser]
        executable = shutil.which(executable_name)
        if executable is None and sys.platform == "win32":
            candidates = [
                Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / relative_path,
                Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")) / relative_path,
                Path(os.environ.get("LOCALAPPDATA", Path.home()))
                / "Programs"
                / (
                    "Opera\\launcher.exe"
                    if browser == "opera"
                    else relative_path
                ),
            ]
            executable = next((str(path) for path in candidates if path.is_file()), None)

        if executable:
            subprocess.Popen([executable, manager_url])
            return True
        if not webbrowser.open(manager_url):
            raise FileNotFoundError(f"Could not open {browser} extension settings")
        return True

    def _open_auxiliary_window(
        self,
        window_type: str,
        title: str,
        params: dict[str, str],
    ) -> str:
        window_id = uuid.uuid4().hex
        parsed = urlsplit(self.ui_url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query.update(params)
        query.update({"window": window_type, "window_id": window_id})
        url = urlunsplit(parsed._replace(query=urlencode(query)))
        window = webview.create_window(
            title,
            url,
            width=720 if window_type == "confirm" else 640,
            height=650 if window_type == "confirm" else 560,
            min_size=(520, 420),
            background_color="#0F0F11",
            js_api=self,
        )
        self.windows[window_id] = window
        window.events.closed += lambda: self.windows.pop(window_id, None)
        return window_id


def create_window(ui_url: str, desktop_api: Optional[DesktopWindowApi] = None) -> webview.Window:
    global _main_window
    api = desktop_api or DesktopWindowApi(ui_url)
    window = webview.create_window(
        WINDOW_TITLE,
        ui_url,
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        min_size=(960, 600),
        background_color="#0F0F11",
        confirm_close=False,
        js_api=api,
    )
    _main_window = window

    def on_closing():
        # Keep FastAPI + downloads alive; only hide the native window.
        window.hide()
        logger.info("Window hidden to tray; downloads keep running")
        return False

    window.events.closing += on_closing
    return window


def start_gui(ui_url: str) -> None:
    create_window(ui_url)
    gui = "edgechromium" if sys.platform == "win32" else None
    debug = os.getenv("SEADOT_DEBUG", "false").lower() == "true"
    logger.info("Opening native window: %s", ui_url)
    webview.start(gui=gui, debug=debug)


def show_existing_window() -> None:
    if _main_window is None:
        return
    try:
        _main_window.show()
        _main_window.restore()
    except Exception:
        _main_window.show()
