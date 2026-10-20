"""Make the hyphenated seadot-backend folder importable as seadot_backend."""

from __future__ import annotations

import sys
import types
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_ROOT.parent
FRONTEND_ROOT = REPO_ROOT / "seadot-frontend"
FRONTEND_DIST = FRONTEND_ROOT / "dist"


def ensure_backend_imports() -> Path:
    if str(BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT))

    pkg = sys.modules.get("seadot_backend")
    if pkg is None:
        pkg = types.ModuleType("seadot_backend")
        pkg.__path__ = [str(BACKEND_ROOT)]
        pkg.__file__ = str(BACKEND_ROOT / "__init__.py")
        sys.modules["seadot_backend"] = pkg
    return BACKEND_ROOT
