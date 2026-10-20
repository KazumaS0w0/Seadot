"""System tray: hide the window without stopping downloads."""

from __future__ import annotations

import logging
import threading
from typing import Callable, Optional

import pystray

from desktop.icon import create_app_icon

logger = logging.getLogger(__name__)


class TrayController:
    def __init__(self, on_show: Callable[[], None], on_quit: Callable[[], None]):
        self.on_show = on_show
        self.on_quit = on_quit
        self.icon: Optional[pystray.Icon] = None

    def start(self) -> None:
        menu = pystray.Menu(
            pystray.MenuItem("Show Seadot", lambda *_: self.on_show(), default=True),
            pystray.MenuItem("Hide to tray", lambda *_: self._hide()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", lambda *_: self._quit()),
        )
        self.icon = pystray.Icon("Seadot", create_app_icon(), "Seadot", menu)
        thread = threading.Thread(target=self.icon.run, name="seadot-tray", daemon=True)
        thread.start()
        logger.info("System tray started")

    def _hide(self) -> None:
        try:
            import webview

            for window in webview.windows:
                window.hide()
        except Exception as exc:
            logger.warning("Hide window failed: %s", exc)

    def _quit(self) -> None:
        if self.icon:
            self.icon.stop()
        self.on_quit()

    def notify(self, title: str, message: str) -> None:
        if self.icon:
            try:
                self.icon.notify(message, title)
            except Exception:
                pass
