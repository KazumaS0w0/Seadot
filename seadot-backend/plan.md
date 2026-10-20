# Seadot Backend Development Plan

## Overview
Modern async download engine with pause/resume, WebSocket streaming, SQLite persistence, and production-ready architecture.

---

## Architecture Highlights

- **Backend**: FastAPI (async) + SQLAlchemy ORM + SQLite
- **Frontend**: React 19 + Vite + TypeScript
- **Core Engine**: Dynamic chunking (8MB default) + pause/resume via `.seadot.part` state file
- **Real-time**: WebSocket for progress streaming to frontend

---

## Phase 1: Setup Environment & Foundation Project ✅ COMPLETED

### ✅ All Tasks Completed

#### 1. Project Structure & Initialization
- [x] Create folder structure (`/seadot-backend`, `/seadot-frontend`, `/seadot-extension`)
- [x] Initialize Python virtualenv at `seadot-backend/venv`
- [x] Install all dependencies from `requirements.txt` (fastapi, uvicorn, aiohttp, websockets, SQLAlchemy)

#### 2. Backend Implementation
- [x] **FastAPI App** (`api/app.py`): CORS middleware, WebSocket support for real-time progress streaming
- [x] **Core Downloader** (`core/downloader.py`): 
  - Dynamic chunk sizing (8MB default with anti-memory spike protection)
  - Pause/resume via `.seadot.part` state file mechanism
  - Safe merge logic to combine downloaded chunks
- [x] **Database Models** (`db/models.py`): SQLAlchemy ORM models for Download & History tracking
- [x] **Database Service** (`db/service.py`): Singleton pattern with SQLite + connection pooling
- [x] **Authentication Middleware** (`middleware/auth_middleware.py`)
- [x] **Dev Runner Script** (`run_dev.py`): Logging-enabled startup script

#### 3. Documentation & Configuration
- [x] README.md (comprehensive project documentation)
- [x] .env.example (environment template)
- [x] .gitignore (Git ignore rules)
- [x] requirements.txt (Python dependencies)
- [x] Frontend scaffolding (React + Vite setup)
- [x] TailwindCSS configuration (`tailwind.config.js`, `postcss.config.js`)

#### 4. Frontend Setup
- [x] React project structure with TypeScript
- [x] Vite configuration (`vite.config.ts` with React plugin)
- [x] TailwindCSS integration
- [x] Package.json with dev scripts

---

## Phase 2: Core Download Engine Implementation ✅ COMPLETED

### ✅ All Tasks Completed

#### 1. Downloader Class Design & Implementation
- [x] **Stream-based download engine**: Dynamic chunk sizing (8MB default, >16MB threshold for larger files)
- [x] **Anti-memory spike protection**: Streaming reads instead of loading entire file into memory
- [x] **State persistence mechanism**: `.seadot.part` file for pause/resume functionality
- [x] **Safe merge logic**: Block-based merging to prevent file corruption

#### 2. WebSocket Real-time Progress Streaming
- [x] WebSocket connection management in `app.py`
- [x] Progress event streaming to frontend (speed, ETA, percentage)
- [x] Download lifecycle state tracking (started, paused, completed, failed)

#### 3. Database Layer Implementation
- [x] **SQLite database**: Lightweight file-based storage with automatic table creation
- [x] **Singleton pattern**: Connection pooling for efficient resource usage
- [x] **Download tracking**: Active downloads table with real-time progress fields
- [x] **History tracking**: Completed downloads history table

---

## Phase 3: Advanced Features (Future) 🚧 PLANNED

### Planned Tasks
- [ ] Multi-threaded parallel download support
- [ ] Resume from interrupted downloads via checkpoint restoration
- [ ] Bandwidth throttling / speed limit controls
- [ ] Concurrent connection pooling optimization
- [ ] Progress visualization in frontend UI
- [ ] Download queue management
- [ ] File integrity verification (hash/checksum)

---

## Phase 4: Frontend Implementation ✅ COMPLETED

### ✅ All Tasks Completed

#### 1. React Component Architecture
- [x] **DownloadList**: Main list component with search, sort, and pagination
- [x] **DownloadItem**: Individual download item with progress bar, buttons (pause, resume, delete)
- [x] **AddDownloadModal**: Modal form for adding new downloads
- [x] **DownloadStats**: Statistics panel with total downloaded, average speed

#### 2. Core Functionality Implementation
- [x] **WebSocket connection** to backend for real-time progress updates
- [x] **Download state management**: Active, paused, completed, failed states
- [x] **API integration**: GET/POST/DELETE endpoints for download CRUD operations
- [x] **Form handling**: File URL input with validation
- [x] **Progress visualization**: Real-time speed, percentage, ETA updates via WebSocket

#### 3. Styling & UX
- [x] TailwindCSS-based styling for all components
- [x] Responsive design (mobile-friendly)
- [x] Status indicators (green for completed, yellow for paused, etc.)
- [x] Loading states and error handling

---

## Phase 5: Desktop Packaging & System Tray Integration ✅ COMPLETED

### ✅ All Tasks Completed

#### 1. Native Desktop Window (PyWebView)
- [x] **Native Windows wrapper**: PyWebView with EdgeChromium backend
- [x] **Auto-fallback chain**: Frontend dist → dev server → API fallback
- [x] **Window lifecycle management**: Minimize to tray, quit on exit
- [x] **File entry point**: `run_desktop.py` with CLI arguments

#### 2. System Tray Integration
- [x] **TrayController**: Context menu with "Show Window" and "Quit Seadot" options
- [x] **Lifecycle management**: Single exit point via `quit_app()` callback
- [x] **Background operation**: App can be minimized to system tray

#### 3. Port Architecture (Three-Tier System)
- [x] **APP_PORT (default: 17890)**: Seadot Backend API server
- [x] **EXTENSION_PORT (default: 47831)**: Local extension bridge server
- [x] **Port forwarding**: Extension bridge receives browser extension POST requests
- [x] **Health check endpoints**: `/api/health` and `/ping` for validation

#### 4. Extension Bridge Implementation
- [x] **Local server setup**: Separate port for Chrome/Edge extension `/capture` endpoint
- [x] **Request forwarding**: Browser extension → extension bridge → backend API
- [x] **Port management utilities**: Check availability and start servers safely

#### 5. Configuration & Utilities
- [x] **config.py**: Port/host configuration constants
- [x] **icon.py**: Icon handling for tray/window
- [x] **paths.py**: Backend import paths and utilities
- [x] **servers.py**: Server startup with port checks and lifecycle management
- [x] **test_phase5.py**: Smoke test for dedicated local ports

### Architecture Overview
```
┌─────────────────────────────────────────────────┐
│  APP_PORT (default: 17890)                       │
│  ├─> Seadot Backend API (FastAPI)               │
│  └─> Serves frontend from /dist or fallback     │
├─────────────────────────────────────────────────┤
│  EXTENSION_PORT (default: 47831)                │
│  ├─> Local extension bridge server               │
│  └─> Receives browser extension POST requests   │
└─────────────────────────────────────────────────┘

Desktop Layer:
┌─────────────────────────────────────────────────┐
│  PyWebView (Windows EdgeChromium)                │
│  ├─> System Tray Integration                     │
│  │     └─> Close → Hide to tray, Exit → Quit    │
│  ├─> Native window with UI_URL                   │
│  └─> Port forwarding for extension bridge        │
└─────────────────────────────────────────────────┘
```

### CLI Usage
```bash
python run_desktop.py           # Full desktop with window + tray
python run_desktop.py --headless# API servers only (for tests)
```

---

## Phase 6: Browser Extension (Manifest V3) 🚧 IN PROGRESS

### Completed in this iteration
- [x] Chrome/Edge Manifest V3 extension structure and local bridge permissions
- [x] Background service worker forwards HTTP/HTTPS download URLs and filenames to the Phase 5 bridge
- [x] Popup UI for opt-in auto-capture, bridge connection status, and configurable localhost port
- [x] Cookies and request headers are not read or forwarded; the extension does not request those sensitive permissions

### Remaining
- [ ] Decide and implement user-consented header/cookie forwarding for authenticated downloads
- [ ] Hand off/cancel browser downloads so Seadot's download engine owns the transfer
- [ ] Verify end-to-end download completion and desktop UI synchronization

---

## Key Architectural Decisions

1. **Downloader Implementation** - Stream-based with dynamic chunking:
   - Default 8MB chunks with automatic resize for large files (>16MB threshold)
   - Anti-memory spike protection via streaming reads
   - State persistence in `.seadot.part` file for pause/resume
   - Safe merge logic to combine downloaded chunks

2. **Database Choice** - SQLite:
   - Lightweight, file-based (no external DB server needed)
   - Automatic table creation via SQLAlchemy migrations
   - Singleton pattern with connection pooling

3. **Real-time Communication** - WebSocket:
   - Streaming progress updates to frontend
   - Download lifecycle state tracking

4. **Desktop Architecture** - Three-tier port isolation:
   - Separate APP_PORT for backend API from EXTENSION_PORT
   - UI_URL fallback chain for graceful degradation
   - Single tray lifecycle management point

---

## Important Files Reference

| Path | Purpose | Status | Phase |
|------|---------|--------|-------|
| `seadot-backend/api/app.py` | FastAPI entry point with CORS, WebSocket support | ✅ Complete | Phase 1 |
| `seadot-backend/core/downloader.py` | Core download engine (stream-based) | ✅ Complete | Phase 2 |
| `seadot-backend/db/models.py` | SQLAlchemy ORM models for downloads & history | ✅ Complete | Phase 1 |
| `seadot-backend/db/service.py` | Database service layer with SQLite + singleton | ✅ Complete | Phase 1 |
| `seadot-backend/middleware/auth_middleware.py` | Authentication middleware | ✅ Complete | Phase 1 |
| `seadot-backend/run_dev.py` | Dev server runner with comprehensive logging | ✅ Complete | Phase 1 |
| `seadot-backend/requirements.txt` | Python dependencies list | ✅ Complete | Phase 1 |
| `seadot-backend/venv/` | Python virtual environment | ✅ Created | Phase 1 |
| `seadot-frontend/package.json` | Frontend dependencies (React, Vite) | ✅ Complete | Phase 1 |
| `seadot-frontend/tailwind.config.js` | Tailwind configuration | ✅ Complete | Phase 1 |
| `seadot-frontend/vite.config.ts` | Vite configuration with React plugin | ✅ Complete | Phase 1 |
| `seadot-frontend/src/components/DownloadList.jsx` | Main list component | ✅ Complete | Phase 4 |
| `seadot-frontend/src/components/DownloadItem.jsx` | Individual download item | ✅ Complete | Phase 4 |
| `seadot-frontend/src/components/AddDownloadModal.jsx` | Add download modal | ✅ Complete | Phase 4 |
| `seadot-frontend/src/components/DownloadStats.jsx` | Statistics panel | ✅ Complete | Phase 4 |
| `seadot-backend/desktop/run_desktop.py` | Desktop entry point with CLI args | ✅ Complete | Phase 5 |
| `seadot-backend/desktop/window.py` | PyWebView window creation | ✅ Complete | Phase 5 |
| `seadot-backend/desktop/tray.py` | System tray controller | ✅ Complete | Phase 5 |
| `seadot-backend/desktop/servers.py` | Server startup & port checks | ✅ Complete | Phase 5 |
| `seadot-backend/desktop/extension_bridge.py` | Extension API router | ✅ Complete | Phase 5 |
| `seadot-backend/desktop/config.py` | Port/host configuration | ✅ Complete | Phase 5 |
| `seadot-backend/desktop/test_phase5.py` | Smoke test for dedicated ports | ✅ Complete | Phase 5 |
| `seadot-extension/manifest.json` | Chrome/Edge Manifest V3 permissions and entry points | ✅ Complete | Phase 6 |
| `seadot-extension/service-worker.js` | Opt-in download URL forwarding to the local bridge | ✅ Complete | Phase 6 |
| `seadot-extension/popup.html` | Browser extension popup interface | ✅ Complete | Phase 6 |
| `seadot-extension/popup.js` | Auto-capture toggle and bridge status | ✅ Complete | Phase 6 |
| `seadot-extension/popup.css` | Popup styling | ✅ Complete | Phase 6 |
| `seadot-extension/tests/service-worker.test.cjs` | Service-worker forwarding and permissions tests | ✅ Complete | Phase 6 |

---

## Status: PHASE 1-2 & PHASE 4-5 COMPLETED ✅; PHASE 6 IN PROGRESS 🚧

### Completed Phases
- ✅ **Phase 1**: Setup Environment & Foundation Project
- ✅ **Phase 2**: Core Download Engine Implementation
- ✅ **Phase 4**: Frontend Implementation
- ✅ **Phase 5**: Desktop Packaging & System Tray Integration
- 🚧 **Phase 6**: Browser Extension (Manifest V3) - basic capture and popup implemented; secure credential handoff and full download takeover remain

### Pending Work
- ⏳ **Phase 3**: Advanced Features (future enhancements)
- ⏳ **Phase 6**: Browser Extension (Manifest V3) - Remaining work listed above

### Next Steps
1. 📄 Review `PHASE_5_COMPLETION_REPORT.md` for detailed Phase 5 summary
2. 🧪 Run smoke tests: `python seadot-backend/desktop/test_phase5.py`
3. 🔐 Git commit all completed work
4. 📦 Prepare release notes and documentation
5. ⏭️ Proceed to Phase 6: Browser Extension development

---

## Completion Report Files

- `seadot-backend/final_report_phase1_2.md` - Comprehensive Phase 1&2 report
- `HANDOFF.md` - Cross-phase handoff document
- `phase1_report.md` - Phase 1 completion report
- `PHASE_5_COMPLETION_REPORT.md` - Phase 5 completion report (new)
