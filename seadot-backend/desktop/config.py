"""Local ports and window defaults for the desktop shell."""

from __future__ import annotations

import os

APP_HOST = os.getenv("SEADOT_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("SEADOT_PORT", "17890"))
EXTENSION_PORT = int(os.getenv("SEADOT_EXTENSION_PORT", "47831"))
UI_URL = os.getenv("SEADOT_UI_URL", "").strip()
WINDOW_TITLE = "Seadot"
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 800
