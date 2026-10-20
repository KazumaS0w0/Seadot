"""Integration tests for starting, pausing, resuming, and removing downloads."""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from desktop.paths import ensure_backend_imports

ensure_backend_imports()

from seadot_backend.api.app import DownloadState, download_manager
from seadot_backend.api import app as api_module
from seadot_backend.db.models import Download, DownloadStatus
from seadot_backend.db.state import close_all_sessions, get_db_session
from desktop import system_actions
from desktop.system_actions import PowerActionManager


@pytest.fixture(autouse=True)
def dispose_test_engines(temp_db_file):
    yield
    close_all_sessions()


@pytest.fixture
def lifecycle_client(temp_db_file):
    from fastapi.testclient import TestClient

    from seadot_backend.api.app import create_app

    test_app = create_app(temp_db_file)
    with TestClient(test_app) as test_client:
        yield test_client
    close_all_sessions()


class ControlledDownloader:
    async def download_streamed(
        self,
        url,
        dest_path,
        headers=None,
        callback=None,
        pause_event=None,
    ):
        if pause_event is not None:
            await pause_event.wait()
        await asyncio.sleep(0.05)
        state = DownloadState(
            download_id="",
            url=url,
            dest_path=dest_path,
            total_size=4,
            downloaded_size=4,
            progress=100,
            status="completed",
        )
        if callback:
            callback(state)
        return state


def test_start_pause_resume_controls_scheduled_transfer(lifecycle_client, temp_db_file, monkeypatch):
    monkeypatch.setattr(download_manager, "_downloader", ControlledDownloader())
    download_id = "lifecycle-start"
    response = lifecycle_client.post(
        "/api/v1/download/create",
        json={
            "download_id": download_id,
            "url": "https://example.test/file.bin",
            "dest_path": "C:/Downloads/file.bin",
            "status": "pending",
        },
    )
    assert response.status_code == 201

    response = lifecycle_client.post(
        "/api/downloads/start",
        params={"download_id": download_id},
    )
    assert response.status_code == 200, response.text
    assert download_id in download_manager.download_tasks

    response = lifecycle_client.post(
        "/api/downloads/pause",
        params={"download_id": download_id},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "paused"
    assert download_manager.pause_events[download_id].is_set() is False

    response = lifecycle_client.post(
        "/api/downloads/resume",
        params={"download_id": download_id},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "downloading"

    deadline = time.monotonic() + 3
    status = None
    while time.monotonic() < deadline:
        session = get_db_session(temp_db_file)
        try:
            record = session.query(Download).filter_by(download_id=download_id).one()
            status = record.status
        finally:
            session.close()
        if status == DownloadStatus.COMPLETED:
            break
        time.sleep(0.02)

    assert status == DownloadStatus.COMPLETED
    while time.monotonic() < deadline and download_id in download_manager.download_tasks:
        time.sleep(0.02)
    assert download_id not in download_manager.download_tasks
    download_manager.active_downloads.pop(download_id, None)


def test_start_existing_pending_download_uses_saved_metadata(lifecycle_client, monkeypatch):
    monkeypatch.setattr(download_manager, "_downloader", ControlledDownloader())
    download_id = "lifecycle-saved-metadata"
    response = lifecycle_client.post(
        "/api/v1/download/create",
        json={
            "download_id": download_id,
            "url": "https://example.test/saved.bin",
            "dest_path": "C:/Downloads/saved.bin",
            "status": "pending",
        },
    )
    assert response.status_code == 201

    response = lifecycle_client.post(
        "/api/downloads/start",
        params={"download_id": download_id},
    )
    assert response.status_code == 200, response.text
    task = download_manager.download_tasks[download_id]
    assert task is not None

    deadline = time.monotonic() + 3
    while time.monotonic() < deadline and not task.done():
        time.sleep(0.02)
    assert task.done()
    download_manager.active_downloads.pop(download_id, None)


def test_download_detail_returns_live_progress_for_active_download(lifecycle_client):
    download_id = "lifecycle-live-progress"
    response = lifecycle_client.post(
        "/api/v1/download/create",
        json={
            "download_id": download_id,
            "url": "https://example.test/live.bin",
            "dest_path": "C:/Downloads/live.bin",
            "status": "pending",
        },
    )
    assert response.status_code == 201

    download_manager.active_downloads[download_id] = DownloadState(
        download_id=download_id,
        url="https://example.test/live.bin",
        dest_path="C:/Downloads/live.bin",
        progress=37.5,
        speed=1024,
        total_size=1000,
        downloaded_size=375,
        eta=12,
        status="downloading",
    )
    try:
        response = lifecycle_client.get(f"/api/downloads/{download_id}")
        assert response.status_code == 200
        assert response.json()["progress"] == 37.5
        assert response.json()["downloaded_size"] == 375
        assert response.json()["speed"] == 1024
    finally:
        download_manager.active_downloads.pop(download_id, None)


def test_remove_cancels_scheduled_transfer_and_marks_failed(lifecycle_client, temp_db_file, monkeypatch):
    class WaitingDownloader:
        async def download_streamed(
            self,
            url,
            dest_path,
            headers=None,
            callback=None,
            pause_event=None,
        ):
            await asyncio.Event().wait()

    monkeypatch.setattr(download_manager, "_downloader", WaitingDownloader())
    download_id = "lifecycle-remove"
    response = lifecycle_client.post(
        "/api/v1/download/create",
        json={
            "download_id": download_id,
            "url": "https://example.test/remove.bin",
            "dest_path": "C:/Downloads/remove.bin",
            "status": "pending",
        },
    )
    assert response.status_code == 201
    response = lifecycle_client.post(
        "/api/downloads/start",
        params={"download_id": download_id},
    )
    assert response.status_code == 200, response.text

    response = lifecycle_client.delete(f"/api/downloads/remove/{download_id}")
    assert response.status_code == 200, response.text

    session = get_db_session(temp_db_file)
    try:
        record = session.query(Download).filter_by(download_id=download_id).one()
        assert record.status == DownloadStatus.FAILED
    finally:
        session.close()
    assert download_id not in download_manager.download_tasks
    assert download_id not in download_manager.pause_events


def test_download_categories_create_directories_under_downloads_and_start_in_selected_folder(
    lifecycle_client,
    temp_db_file,
    tmp_path,
    monkeypatch,
):
    from desktop.download_folders import CATEGORIES

    downloads_root = tmp_path / "Downloads"
    monkeypatch.setenv("SEADOT_DOWNLOAD_ROOT", str(downloads_root))
    scheduled = []
    monkeypatch.setattr(
        download_manager,
        "schedule_download",
        lambda *args, **kwargs: scheduled.append((args, kwargs)),
    )

    response = lifecycle_client.get("/api/downloads/categories")
    assert response.status_code == 200
    folders = response.json()["categories"]
    assert [folder["id"] for folder in folders] == [category["id"] for category in CATEGORIES]
    assert all(Path(folder["folder"]).is_dir() for folder in folders)
    assert Path(folders[0]["folder"]).parent == downloads_root

    response = lifecycle_client.post(
        "/api/downloads/create",
        json={
            "url": "https://example.test/setup.exe",
            "filename": "setup.exe",
            "category": "applications",
            "destination_folder": folders[0]["folder"],
        },
    )
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["category"] == "applications"
    assert result["dest_path"] == str(Path(folders[0]["folder"]) / "setup.exe")
    assert scheduled[0][0][0] == result["download_id"]
    assert scheduled[0][0][2] == result["dest_path"]

    session = get_db_session(temp_db_file)
    try:
        record = session.query(Download).filter_by(download_id=result["download_id"]).one()
        assert record.dest_path == result["dest_path"]
        assert record.status == DownloadStatus.DOWNLOADING
    finally:
        session.close()


def test_download_creation_rejects_unknown_category_and_non_http_urls(lifecycle_client):
    invalid_url = lifecycle_client.post(
        "/api/downloads/create",
        json={"url": "file:///setup.exe", "filename": "setup.exe"},
    )
    assert invalid_url.status_code == 422

    invalid_category = lifecycle_client.post(
        "/api/downloads/create",
        json={
            "url": "https://example.test/setup.exe",
            "filename": "setup.exe",
            "category": "unknown",
        },
    )
    assert invalid_category.status_code == 422


def test_download_category_is_detected_from_file_extension(lifecycle_client, tmp_path, monkeypatch):
    monkeypatch.setenv("SEADOT_DOWNLOAD_ROOT", str(tmp_path / "Downloads"))
    monkeypatch.setattr(download_manager, "schedule_download", lambda *args, **kwargs: None)

    response = lifecycle_client.post(
        "/api/downloads/create",
        json={"url": "https://example.test/song.mp3"},
    )

    assert response.status_code == 201, response.text
    result = response.json()
    assert result["filename"] == "song.mp3"
    assert result["category"] == "music"
    assert Path(result["dest_path"]).parent.name == "Music"


def test_system_settings_are_optional_persisted_and_startup_registration_is_updated(
    lifecycle_client,
    tmp_path,
    monkeypatch,
):
    settings_file = tmp_path / "settings.json"
    startup_changes = []
    monkeypatch.setattr(system_actions, "settings_path", lambda: settings_file)
    monkeypatch.setattr(system_actions.sys, "platform", "win32")
    monkeypatch.setattr(
        system_actions,
        "set_startup_enabled",
        startup_changes.append,
    )

    response = lifecycle_client.get("/api/system/settings")
    assert response.status_code == 200
    assert response.json() == {
        "auto_start": True,
        "completion_action": "none",
        "countdown_minutes": 2,
        "split_count": 4,
    }
    assert startup_changes == [True]

    response = lifecycle_client.put(
        "/api/system/settings",
        json={
            "auto_start": True,
            "completion_action": "shutdown",
            "countdown_minutes": 2,
            "split_count": 8,
        },
    )
    assert response.status_code == 200, response.text
    assert startup_changes == [True]
    assert startup_changes == [True]
    assert system_actions.load_settings()["completion_action"] == "shutdown"
    assert system_actions.load_settings()["split_count"] == 8

    response = lifecycle_client.put(
        "/api/system/settings",
        json={
            "auto_start": True,
            "completion_action": "none",
            "countdown_minutes": 2,
            "split_count": 8,
        },
    )
    assert response.status_code == 200
    assert startup_changes == [True]

    invalid = lifecycle_client.put(
        "/api/system/settings",
        json={
            "auto_start": True,
            "completion_action": "hibernate",
            "countdown_minutes": 2,
            "split_count": 3,
        },
    )
    assert invalid.status_code == 422


def test_existing_startup_preference_is_not_overwritten(tmp_path, monkeypatch):
    settings_file = tmp_path / "settings.json"
    monkeypatch.setattr(system_actions, "settings_path", lambda: settings_file)
    system_actions.save_settings({
        "auto_start": False,
        "completion_action": "none",
        "countdown_minutes": 2,
        "split_count": 4,
    })
    startup_changes = []
    monkeypatch.setattr(system_actions.sys, "platform", "win32")
    monkeypatch.setattr(system_actions, "set_startup_enabled", startup_changes.append)

    settings = system_actions.initialize_default_settings()

    assert settings["auto_start"] is False
    assert startup_changes == []


def test_power_action_countdown_can_be_cancelled(monkeypatch):
    async def verify():
        manager = PowerActionManager()
        await manager.schedule("shutdown", 2)
        assert manager.status()["pending"] is True
        assert manager.status()["action"] == "shutdown"
        assert await manager.cancel() is True
        assert manager.status() == {"pending": False}

    asyncio.run(verify())


def test_completion_action_is_only_scheduled_when_queue_is_terminal(
    lifecycle_client,
    temp_db_file,
    monkeypatch,
):
    monkeypatch.setattr(
        api_module,
        "load_settings",
        lambda: {
            "auto_start": False,
            "completion_action": "shutdown",
            "countdown_minutes": 2,
        },
    )
    session = get_db_session(temp_db_file)
    try:
        session.add(
            Download(
                download_id="finished-queue",
                url="https://example.test/done",
                dest_path="C:/Downloads/done",
                status=DownloadStatus.COMPLETED,
            )
        )
        session.commit()
    finally:
        session.close()

    async def verify():
        await download_manager._schedule_completion_action_if_idle()
        assert power_action_manager.status()["pending"] is True
        await power_action_manager.cancel()

    from seadot_backend.api.app import power_action_manager

    asyncio.run(verify())
