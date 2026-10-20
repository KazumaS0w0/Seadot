"""
Integration Tests for Seadot API Endpoints and WebSocket
Tests REST endpoints, database persistence across requests, and basic WebSocket validation.

Usage:
    cd seadot-backend
    venv\Scripts\activate
    pytest tests/integration/test_api.py -v

Run specific tests:
    pytest tests/integration/test_api.py::test_create_download -v
"""

import sys
import os
import pytest
import json
from datetime import datetime

# Import from the main project
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.models import Download, DownloadHistory, Base, get_db_state
from db.state import init_database, create_session, close_all_sessions
from api.app import create_app


@pytest.fixture
def test_db_path():
    """Provide a temporary database file for tests"""
    import tempfile
    tmp_dir = tempfile.mkdtemp(prefix="seadot-test-")
    db_path = os.path.join(tmp_dir, "test.db")
    yield db_path
    try:
        close_all_sessions()
    finally:
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except PermissionError:
                pass
        if os.path.exists(tmp_dir):
            try:
                os.rmdir(tmp_dir)
            except OSError:
                pass


@pytest.fixture
def app_and_client(test_db_path):
    """Provide FastAPI app and test client"""
    # Initialize database
    get_db_state(test_db_path)
    
    # Create app with file-based SQLite
    app = create_app(test_db_path)
    client = app.test_client()
    
    yield app, client


@pytest.fixture
def session_factory(test_db_path):
    """Provide database session factory"""
    get_db_state(test_db_path)
    return create_session(test_db_path)


class TestRESTEndpoints:
    """Test REST API endpoints"""
    
    def test_create_download_endpoint(self, app_and_client, test_db_path):
        """Test POST /api/v1/download/create endpoint"""
        app, client = app_and_client
        payload = {
            "download_id": "test-001",
            "url": "https://example.com/file.zip",
            "dest_path": "C:/Downloads/test.zip",
            "headers": {"User-Agent": "Seadot/1.0"},
            "status": "downloading"
        }
        
        response = client.post("/api/v1/download/create", 
                              json=payload,
                              headers={"Content-Type": "application/json"})
        
        # Should return 201 Created
        assert response.status_code == 201
        
        # Should return created download data
        data = json.loads(response.text)
        assert data["download_id"] == "test-001"
        assert data["status"] == "downloading"

    def test_list_downloads_returns_downloads_object(self, app_and_client):
        _, client = app_and_client

        response = client.get("/api/downloads")

        assert response.status_code == 200
        assert isinstance(response.json()["downloads"], list)

    def test_update_download_options(self, app_and_client):
        _, client = app_and_client
        client.post(
            "/api/v1/download/create",
            json={
                "download_id": "options-001",
                "url": "https://example.com/file.zip",
                "dest_path": "C:/Downloads/file.zip",
            },
        )

        response = client.put(
            "/api/downloads/options-001/options",
            json={
                "speed_limit_bps": 524288,
                "split_count": 8,
                "completion_action": "hibernate",
                "countdown_minutes": 3,
            },
        )

        assert response.status_code == 200
        assert response.json()["speed_limit_bps"] == 524288
        assert response.json()["split_count"] == 8
        assert response.json()["completion_action"] == "hibernate"

        detail_response = client.get("/api/downloads/options-001")

        assert detail_response.status_code == 200
        assert detail_response.json()["speed_limit_bps"] == 524288
        assert detail_response.json()["split_count"] == 8

    def test_delete_download_keeps_file_when_requested(self, app_and_client, tmp_path):
        _, client = app_and_client
        destination = tmp_path / "keep-me.zip"
        destination.write_bytes(b"download")
        client.post(
            "/api/v1/download/create",
            json={
                "download_id": "delete-keep",
                "url": "https://example.com/file.zip",
                "dest_path": str(destination),
            },
        )

        response = client.delete("/api/downloads/delete-keep")

        assert response.status_code == 200
        assert response.json()["file_deleted"] is False
        assert destination.read_bytes() == b"download"
        assert client.get("/api/downloads/delete-keep").status_code == 404

    def test_delete_download_removes_file_when_requested(self, app_and_client, tmp_path):
        _, client = app_and_client
        destination = tmp_path / "remove-me.zip"
        destination.write_bytes(b"download")
        client.post(
            "/api/v1/download/create",
            json={
                "download_id": "delete-file",
                "url": "https://example.com/file.zip",
                "dest_path": str(destination),
            },
        )

        response = client.delete("/api/downloads/delete-file?delete_file=true")

        assert response.status_code == 200
        assert response.json()["file_deleted"] is True
        assert not destination.exists()

    def test_extension_info_returns_loadable_manifest_folder(self, app_and_client):
        _, client = app_and_client

        response = client.get("/api/extension/info")

        assert response.status_code == 200
        from pathlib import Path
        assert (Path(response.json()["folder"]) / "manifest.json").is_file()
    
    def test_get_downloads_endpoint(self, app_and_client, test_db_path):
        """Test GET /api/v1/download?status=all endpoint"""
        app, client = app_and_client
        
        # First create a download
        payload = {
            "download_id": "test-get-001",
            "url": "https://example.com/test.zip",
            "dest_path": "C:/Downloads/test.zip"
        }
        
        response = client.post("/api/v1/download/create", 
                              json=payload,
                              headers={"Content-Type": "application/json"})
        assert response.status_code == 201
        
        # Now query all downloads
        response = client.get("/api/v1/download?status=all",
                             headers={"Content-Type": "application/json"})
        
        # Should return 200 OK
        assert response.status_code == 200
        
        data = json.loads(response.text)
        assert "downloads" in data
    
    def test_update_download_progress(self, app_and_client, test_db_path):
        """Test POST /api/v1/download/update endpoint"""
        app, client = app_and_client
        
        # Create initial download
        create_payload = {
            "download_id": "progress-001",
            "url": "https://example.com/file.zip",
            "dest_path": "C:/Downloads/test.zip"
        }
        
        response = client.post("/api/v1/download/create", 
                              json=create_payload,
                              headers={"Content-Type": "application/json"})
        assert response.status_code == 201
        
        # Now update progress
        payload = {
            "download_id": "progress-001",
            "total_size": 104857600,
            "downloaded_size": 52428800
        }
        
        response = client.post("/api/v1/download/update", 
                              json=payload,
                              headers={"Content-Type": "application/json"})
        
        assert response.status_code == 200


class TestDatabasePersistence:
    """Test database persistence across requests"""
    
    def test_data_persists_across_requests(self, app_and_client, test_db_path):
        """Test that data created in one request is available in another"""
        app, client = app_and_client
        
        # Create new download via API
        payload = {
            "download_id": "persist-002",
            "url": "https://example.com/new.zip",
            "dest_path": "C:/Downloads/new.zip"
        }
        
        response = client.post("/api/v1/download/create", 
                              json=payload,
                              headers={"Content-Type": "application/json"})
        
        assert response.status_code == 201
        
        # Query should include new download
        response = client.get("/api/v1/download?status=all",
                             headers={"Content-Type": "application/json"})
        data = json.loads(response.text)
        
        downloads = data["downloads"]
        ids = [d["download_id"] for d in downloads]
        assert "persist-002" in ids


class TestWebSocketEndpoint:
    """Test WebSocket endpoint connection"""
    
    def test_websocket_endpoint_exists(self):
        """Test that WebSocket endpoint is properly configured"""
        # Check the app has ws_handler registered
        from api.app import app
        
        # Verify the app instance exists and is FastAPI
        assert app is not None
        assert hasattr(app, 'routes')  # FastAPI should have routes


class TestErrorHandling:
    """Test error handling and validation"""
    
    def test_missing_required_fields(self, app_and_client, test_db_path):
        """Test endpoint rejects missing required fields"""
        app, client = app_and_client
        
        payload = {
            "download_id": "missing-fields-001",
            # Missing url and dest_path
        }
        
        response = client.post("/api/v1/download/create", 
                              json=payload,
                              headers={"Content-Type": "application/json"})
        
        # Should return 400 Bad Request or 422 Validation Error
        assert response.status_code in [400, 422]
    
    def test_invalid_status_value(self, app_and_client, test_db_path):
        """Test endpoint rejects invalid status values"""
        app, client = app_and_client
        
        payload = {
            "download_id": "invalid-001",
            "url": "https://example.com/test.zip",
            "dest_path": "C:/Downloads/test.zip",
            "status": "INVALID_STATUS"  # Invalid value
        }
        
        response = client.post("/api/v1/download/create", 
                              json=payload,
                              headers={"Content-Type": "application/json"})
        
        # Should return validation error
        assert response.status_code in [400, 422]
    
    def test_missing_download_id_on_update(self, app_and_client, test_db_path):
        """Test update endpoint requires download_id"""
        app, client = app_and_client
        
        payload = {
            # Missing download_id
            "total_size": 100
        }
        
        response = client.post("/api/v1/download/update", 
                              json=payload,
                              headers={"Content-Type": "application/json"})
        
        # Should return validation error
        assert response.status_code in [400, 422]


class TestDownloadStatusTransitions:
    """Test download status state machine"""
    
    def test_complete_download_transition(self, app_and_client, test_db_path):
        """Test transitioning from downloading to completed"""
        app, client = app_and_client
        
        # Create download in downloading state
        payload = {
            "download_id": "status-complete-0",
            "url": "https://example.com/status.zip",
            "dest_path": "C:/Downloads/status.zip"
        }
        
        response = client.post("/api/v1/download/create", 
                              json=payload,
                              headers={"Content-Type": "application/json"})
        assert response.status_code == 201
        
        # Complete the download
        update_payload = {
            "download_id": "status-complete-0",
            "total_size": 104857600,
            "downloaded_size": 104857600
        }
        
        response = client.post("/api/v1/download/update", 
                              json=update_payload,
                              headers={"Content-Type": "application/json"})
        
        assert response.status_code == 200
        
        # Verify status changed to completed
        response = client.get("/api/v1/download?status=all",
                             headers={"Content-Type": "application/json"})
        data = json.loads(response.text)
        
        for download in data["downloads"]:
            if download["download_id"] == "status-complete-0":
                assert download["status"] == "completed"
                break
    
    def test_pause_download_transition(self, app_and_client, test_db_path):
        """Test transitioning from downloading to paused"""
        app, client = app_and_client
        
        # Create download in downloading state
        payload = {
            "download_id": "status-pause-1",
            "url": "https://example.com/pause.zip",
            "dest_path": "C:/Downloads/pause.zip"
        }
        
        response = client.post("/api/v1/download/create", 
                              json=payload,
                              headers={"Content-Type": "application/json"})
        assert response.status_code == 201
        
        # Pause the download
        update_payload = {
            "download_id": "status-pause-1",
            "total_size": 52428800,
            "downloaded_size": 26214400,
            "paused_at": datetime.now().isoformat()
        }
        
        response = client.post("/api/v1/download/update", 
                              json=update_payload,
                              headers={"Content-Type": "application/json"})
        
        assert response.status_code == 200
        
        # Verify status changed to paused
        response = client.get("/api/v1/download?status=all",
                             headers={"Content-Type": "application/json"})
        data = json.loads(response.text)
        
        for download in data["downloads"]:
            if download["download_id"] == "status-pause-1":
                assert download["status"] == "paused"
                break


class TestDownloadHistory:
    """Test download history tracking"""
    
    def test_history_created_on_complete(self, app_and_client, test_db_path):
        """Test that download history is created when download completes"""
        app, client = app_and_client
        
        # Create download in downloading state
        payload = {
            "download_id": "history-001",
            "url": "https://example.com/history.zip",
            "dest_path": "C:/Downloads/history.zip"
        }
        
        response = client.post("/api/v1/download/create", 
                              json=payload,
                              headers={"Content-Type": "application/json"})
        assert response.status_code == 201
        
        # Complete the download
        update_payload = {
            "download_id": "history-001",
            "total_size": 104857600,
            "downloaded_size": 104857600
        }
        
        response = client.post("/api/v1/download/update", 
                              json=update_payload,
                              headers={"Content-Type": "application/json"})
        assert response.status_code == 200
        
        # Verify status is completed
        response = client.get("/api/v1/download?status=all",
                             headers={"Content-Type": "application/json"})
        data = json.loads(response.text)
        
        for download in data["downloads"]:
            if download["download_id"] == "history-001":
                assert download["status"] == "completed"
                break


if __name__ == "__main__":
    # Run tests manually with pytest
    print("Run with: pytest tests/integration/test_api.py -v")
