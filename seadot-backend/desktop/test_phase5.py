"""Smoke-test dedicated local ports used by the desktop shell."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import requests

from desktop.config import APP_HOST, APP_PORT, EXTENSION_PORT
from desktop.paths import ensure_backend_imports
from desktop.servers import start_app_server, start_extension_server

ensure_backend_imports()


def main() -> int:
    from seadot_backend.api.app import app
    from desktop.extension_bridge import bridge_app

    start_app_server(app)
    start_extension_server(bridge_app)

    health = requests.get(f"http://{APP_HOST}:{APP_PORT}/api/health", timeout=5)
    ping = requests.get(f"http://{APP_HOST}:{EXTENSION_PORT}/ping", timeout=5)
    capture = requests.post(
        f"http://{APP_HOST}:{EXTENSION_PORT}/capture",
        json={"url": "https://example.com/phase5-test.bin"},
        timeout=5,
    )

    print("health", health.status_code, health.text)
    print("ping", ping.status_code, ping.text)
    print("capture", capture.status_code, capture.text)

    health.raise_for_status()
    ping.raise_for_status()
    capture.raise_for_status()
    ping_data = ping.json()
    assert ping_data["ok"] is True
    assert ping_data["port"] == EXTENSION_PORT
    assert capture.json()["accepted"] is True
    print("PHASE 5 PORT TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
