"""Default download categories and first-run folder initialization."""

from __future__ import annotations

import os
from pathlib import Path

CATEGORIES = (
    {
        "id": "applications",
        "label": "Applications",
        "folder_name": "Applications",
        "extensions": (".exe", ".msi", ".msix", ".appx", ".apk", ".dmg", ".pkg", ".deb", ".rpm"),
    },
    {
        "id": "videos",
        "label": "Videos",
        "folder_name": "Videos",
        "extensions": (".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv", ".m4v"),
    },
    {
        "id": "music",
        "label": "Music",
        "folder_name": "Music",
        "extensions": (".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"),
    },
    {
        "id": "documents",
        "label": "Documents",
        "folder_name": "Documents",
        "extensions": (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".md", ".csv"),
    },
    {
        "id": "archives",
        "label": "Archives",
        "folder_name": "Archives",
        "extensions": (".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso"),
    },
    {
        "id": "images",
        "label": "Images",
        "folder_name": "Images",
        "extensions": (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".tif", ".tiff"),
    },
    {
        "id": "other",
        "label": "Other",
        "folder_name": "Other",
        "extensions": (),
    },
)


def download_root() -> Path:
    configured_root = os.getenv("SEADOT_DOWNLOAD_ROOT")
    if configured_root:
        return Path(configured_root).expanduser()
    return Path.home() / "Downloads"


def category_for_filename(filename: str) -> dict:
    suffix = Path(filename).suffix.lower()
    for category in CATEGORIES:
        if suffix and suffix in category["extensions"]:
            return category
    return CATEGORIES[-1]


def ensure_download_folders() -> list[dict[str, str]]:
    root = download_root()
    root.mkdir(parents=True, exist_ok=True)
    result = []
    for category in CATEGORIES:
        folder = root / category["folder_name"]
        folder.mkdir(parents=True, exist_ok=True)
        result.append({
            "id": category["id"],
            "label": category["label"],
            "folder": str(folder),
        })
    return result
