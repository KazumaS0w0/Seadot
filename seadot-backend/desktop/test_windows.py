from urllib.parse import parse_qs, urlsplit
from unittest.mock import Mock

from desktop.window import DesktopWindowApi


def test_download_windows_open_as_separate_native_windows(monkeypatch):
    created = []

    class Event:
        def __iadd__(self, callback):
            self.callback = callback
            return self

    def create_window(title, url, **kwargs):
        window = Mock()
        window.events.closed = Event()
        window.url = url
        created.append((title, kwargs, window))
        return window

    monkeypatch.setattr("desktop.window.webview.create_window", create_window)
    api = DesktopWindowApi("http://127.0.0.1:5173/")

    confirmation_id = api.open_download_confirmation("https://example.test/file.zip")
    details_id = api.open_download_details("download-42")

    assert len(created) == 2
    assert created[0][0] == "Confirm download"
    assert created[1][0] == "Download details"
    assert created[0][1]["js_api"] is api
    assert created[1][1]["js_api"] is api
    confirmation_query = parse_qs(urlsplit(created[0][2].url).query)
    details_query = parse_qs(urlsplit(created[1][2].url).query)
    assert confirmation_query == {
        "url": ["https://example.test/file.zip"],
        "window": ["confirm"],
        "window_id": [confirmation_id],
    }
    assert details_query == {
        "id": ["download-42"],
        "window": ["details"],
        "window_id": [details_id],
    }

    api.close_window(confirmation_id)
    created[0][2].destroy.assert_called_once()


def test_extension_manager_opens_selected_browser(monkeypatch):
    launched = []
    monkeypatch.setattr("desktop.window.shutil.which", lambda executable: f"C:\\Browsers\\{executable}")
    monkeypatch.setattr(
        "desktop.window.subprocess.Popen",
        lambda command: launched.append(command),
    )

    api = DesktopWindowApi("http://127.0.0.1:5173/")

    assert api.open_extension_manager("chrome") is True
    assert api.open_extension_manager("edge") is True
    assert api.open_extension_manager("firefox") is True
    assert api.open_extension_manager("opera") is True
    assert launched == [
        ["C:\\Browsers\\chrome.exe", "chrome://extensions/"],
        ["C:\\Browsers\\msedge.exe", "edge://extensions/"],
        ["C:\\Browsers\\firefox.exe", "about:debugging#/runtime/this-firefox"],
        ["C:\\Browsers\\opera.exe", "opera://extensions/"],
    ]
