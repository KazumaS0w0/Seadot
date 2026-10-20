"""Optional Windows startup registration and post-download power actions."""

from __future__ import annotations

import asyncio
import ctypes
import json
import logging
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_SETTINGS = {
    "auto_start": True,
    "completion_action": "none",
    "countdown_minutes": 2,
    "split_count": 4,
}
ALLOWED_ACTIONS = {"none", "shutdown", "sleep", "hibernate", "restart"}
STARTUP_REGISTRY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_VALUE_NAME = "Seadot"


def settings_path() -> Path:
    base = os.getenv("LOCALAPPDATA")
    if base:
        return Path(base) / "Seadot" / "settings.json"
    return Path.home() / ".config" / "Seadot" / "settings.json"


def load_settings() -> dict[str, Any]:
    path = settings_path()
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return DEFAULT_SETTINGS.copy()
    except (OSError, json.JSONDecodeError) as exc:
        logger.exception("Could not read Seadot settings from %s", path)
        raise RuntimeError(f"Could not read settings file: {path}") from exc

    settings = DEFAULT_SETTINGS.copy()
    settings.update(stored)
    return settings


def save_settings(settings: dict[str, Any]) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=".settings-",
            suffix=".tmp",
            delete=False,
        ) as settings_file:
            json.dump(settings, settings_file, indent=2)
            settings_file.flush()
            os.fsync(settings_file.fileno())
            temp_path = Path(settings_file.name)
        os.replace(temp_path, path)
    except OSError as exc:
        logger.exception("Could not save Seadot settings to %s", path)
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise RuntimeError(f"Could not save settings file: {path}") from exc


def initialize_default_settings() -> dict[str, Any]:
    path = settings_path()
    if path.exists():
        return load_settings()

    settings = DEFAULT_SETTINGS.copy()
    startup_registered = False
    if sys.platform == "win32":
        set_startup_enabled(True)
        startup_registered = True
    try:
        save_settings(settings)
    except RuntimeError:
        if startup_registered:
            try:
                set_startup_enabled(False)
            except OSError:
                logger.exception("Could not roll back default startup registration")
        raise
    return settings


def set_startup_enabled(enabled: bool) -> None:
    if sys.platform != "win32":
        if enabled:
            raise OSError("Automatic startup registration is supported on Windows only.")
        return

    import winreg

    key_path = STARTUP_REGISTRY_PATH
    if enabled:
        backend_dir = Path(__file__).resolve().parent.parent
        script_path = backend_dir / "run_desktop.py"
        executable = Path(sys.executable)
        if executable.name.lower() == "python.exe":
            windowless_executable = executable.with_name("pythonw.exe")
            if windowless_executable.exists():
                executable = windowless_executable
        command = f'"{executable}" "{script_path}"'
        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,
            key_path,
            0,
            winreg.KEY_SET_VALUE,
        ) as startup_key:
            winreg.SetValueEx(
                startup_key,
                STARTUP_VALUE_NAME,
                0,
                winreg.REG_SZ,
                command,
            )
        return

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            key_path,
            0,
            winreg.KEY_SET_VALUE,
        ) as startup_key:
            winreg.DeleteValue(startup_key, STARTUP_VALUE_NAME)
    except FileNotFoundError:
        return


def execute_power_action(action: str) -> None:
    if action == "shutdown":
        subprocess.run(["shutdown.exe", "/s", "/t", "0"], check=True)
        return
    if action == "restart":
        subprocess.run(["shutdown.exe", "/r", "/t", "0"], check=True)
        return
    if action == "sleep":
        if sys.platform != "win32":
            raise OSError("Sleep is supported on Windows only.")
        result = ctypes.windll.powrprof.SetSuspendState(False, False, False)
        if result == 0:
            raise OSError("Windows failed to enter sleep mode.")
        return
    if action == "hibernate":
        if sys.platform != "win32":
            raise OSError("Hibernate is supported on Windows only.")
        subprocess.run(["shutdown.exe", "/h"], check=True)
        return
    raise ValueError(f"Unsupported completion action: {action}")


class PowerActionManager:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._action: str | None = None
        self._deadline: float | None = None

    def status(self) -> dict[str, Any]:
        if self._task is None or self._task.done() or self._deadline is None:
            return {"pending": False}
        return {
            "pending": True,
            "action": self._action,
            "seconds_remaining": max(0, int(self._deadline - time.monotonic())),
        }

    def cancel_pending(self) -> bool:
        task = self._task
        if task is None or task.done():
            self._clear()
            return False
        task.cancel()
        self._clear()
        return True

    async def cancel(self) -> bool:
        task = self._task
        if task is None or task.done():
            self._clear()
            return False
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        self._clear()
        return True

    async def schedule(self, action: str, countdown_minutes: int) -> None:
        if action not in ALLOWED_ACTIONS:
            raise ValueError(f"Unsupported completion action: {action}")
        await self.cancel()
        if action == "none":
            return
        self._action = action
        self._deadline = time.monotonic() + countdown_minutes * 60
        self._task = asyncio.create_task(self._countdown(action, countdown_minutes * 60))

    async def _countdown(self, action: str, seconds: int) -> None:
        try:
            logger.info(
                "System action %s scheduled in %s minutes",
                action,
                seconds // 60,
            )
            await asyncio.sleep(seconds)
            await asyncio.to_thread(execute_power_action, action)
        except asyncio.CancelledError:
            logger.info("Scheduled system action %s was cancelled", action)
            raise
        except (OSError, subprocess.SubprocessError, ValueError):
            logger.exception("System action %s failed", action)
        finally:
            if self._task is asyncio.current_task():
                self._clear()

    def _clear(self) -> None:
        self._task = None
        self._action = None
        self._deadline = None
