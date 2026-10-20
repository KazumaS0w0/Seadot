"""Phase 6 extension handoff and download-engine integration tests."""

from __future__ import annotations

import asyncio
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import AsyncMock, Mock

from sqlalchemy import text

from desktop import extension_bridge
from desktop.extension_bridge import CaptureRequest, capture
from seadot_backend.api import app as api_module
from seadot_backend.api.app import download_manager
from seadot_backend.core.downloader import Downloader
from seadot_backend.db.models import Download, DownloadHistory, DownloadStatus
from seadot_backend.db.state import close_all_sessions, get_db_session, init_database


class DownloadHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header(
                "Location",
                f"http://localhost:{self.server.server_port}/file",
            )
            self.end_headers()
            return

        self.server.received_cookie = self.headers.get("Cookie")
        payload = b"Seadot engine transfer"
        self.send_response(200)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        pass


def start_test_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), DownloadHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def test_capture_schedules_engine_transfer_without_persisting_credentials(monkeypatch, tmp_path):
    start_download = AsyncMock(return_value={"success": True, "download_id": "test-id"})
    session = Mock()
    save_state = Mock()
    monkeypatch.setattr(download_manager, "start_download", start_download)
    monkeypatch.setattr(
        download_manager,
        "schedule_download",
        lambda *args, **kwargs: asyncio.create_task(start_download(*args, **kwargs)),
    )
    monkeypatch.setattr(extension_bridge, "get_db_session", lambda: session)
    monkeypatch.setattr(extension_bridge, "save_download_state", save_state)
    destination = tmp_path / "private.zip"

    async def submit_capture():
        result = await capture(
            CaptureRequest(
                url="https://example.test/private.zip",
                filename="../../private.zip",
                headers={"Cookie": "session=secret"},
                dest_path=str(destination),
            )
        )
        await asyncio.sleep(0)
        return result

    result = asyncio.run(submit_capture())

    assert result.accepted is True
    assert result.dest_path == str(destination)
    start_download.assert_awaited_once()
    args, kwargs = start_download.await_args
    assert args[1:3] == ("https://example.test/private.zip", str(destination))
    assert kwargs["headers"] == {"Cookie": "session=secret"}
    assert kwargs["persist_headers"] is False
    save_state.assert_called_once_with(
        session,
        result.download_id,
        "https://example.test/private.zip",
        str(destination),
    )
    session.close.assert_called_once()


def test_engine_streams_download_and_strips_credentials_on_cross_origin_redirect(tmp_path):
    server, thread = start_test_server()
    destination = tmp_path / "download.bin"
    try:
        async def download():
            return await Downloader().download_streamed(
                f"http://127.0.0.1:{server.server_port}/redirect",
                str(destination),
                headers={
                    "Cookie": "session=secret",
                    "Referer": "http://127.0.0.1/private",
                },
            )

        state = asyncio.run(download())

        assert destination.read_bytes() == b"Seadot engine transfer"
        assert server.received_cookie is None
        assert state.downloaded_size == len(b"Seadot engine transfer")
        assert state.progress == 100
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_bridge_downloads_file_through_engine_without_storing_cookie_headers(monkeypatch, tmp_path):
    server, thread = start_test_server()
    database_path = tmp_path / "phase6.db"
    destination = tmp_path / "captured.bin"
    init_database(str(database_path))
    monkeypatch.setattr(
        api_module,
        "get_db_session",
        lambda db_path="seadot.db": get_db_session(str(database_path)),
    )
    try:
        async def submit_capture():
            result = await capture(
                CaptureRequest(
                    url=f"http://127.0.0.1:{server.server_port}/file",
                    filename="captured.bin",
                    headers={"Cookie": "session=consented"},
                    dest_path=str(destination),
                )
            )
            task = next(iter(extension_bridge._capture_tasks))
            return result, await task

        result, download_result = asyncio.run(submit_capture())

        assert result.accepted is True
        assert download_result["success"] is True
        assert destination.read_bytes() == b"Seadot engine transfer"
        assert server.received_cookie == "session=consented"

        session = get_db_session(str(database_path))
        try:
            download = session.query(Download).filter_by(download_id=result.download_id).one()
            history = session.query(DownloadHistory).filter_by(download_id=result.download_id).one()
            assert download.status.value == "completed"
            assert download.headers_json is None
            assert history.headers_json is None
        finally:
            session.close()
    finally:
        close_all_sessions()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_database_startup_migrates_legacy_enum_names(tmp_path):
    database_path = tmp_path / "legacy-status.db"
    init_database(str(database_path))
    session = get_db_session(str(database_path))
    try:
        session.add(
            Download(
                download_id="legacy-id",
                url="https://example.test/file",
                dest_path=str(tmp_path / "file"),
                status=DownloadStatus.DOWNLOADING,
            )
        )
        session.add(
            DownloadHistory(
                download_id="legacy-id",
                url="https://example.test/file",
                dest_path=str(tmp_path / "file"),
                total_size=1,
                downloaded_size=1,
                status=DownloadStatus.COMPLETED,
            )
        )
        session.commit()
        session.execute(
            text("UPDATE downloads SET status = 'DOWNLOADING' WHERE download_id = 'legacy-id'")
        )
        session.execute(
            text("UPDATE download_history SET status = 'COMPLETED' WHERE download_id = 'legacy-id'")
        )
        session.commit()
    finally:
        session.close()

    init_database(str(database_path))
    session = get_db_session(str(database_path))
    try:
        assert session.query(Download).one().status is DownloadStatus.DOWNLOADING
        assert session.query(DownloadHistory).one().status is DownloadStatus.COMPLETED
    finally:
        session.close()
        close_all_sessions()
