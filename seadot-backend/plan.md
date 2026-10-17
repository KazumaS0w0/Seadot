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

## Phase 1: Setup Environment & Foundation Project

### ✅ Completed Tasks

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

## Phase 2: Core Download Engine Implementation

### ✅ Completed Tasks

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

## Phase 3: Advanced Features (Future)

### Planned Tasks
- [ ] Multi-threaded parallel download support
- [ ] Resume from interrupted downloads via checkpoint restoration
- [ ] Bandwidth throttling / speed limit controls
- [ ] Concurrent connection pooling optimization
- [ ] Progress visualization in frontend UI
- [ ] Download queue management
- [ ] File integrity verification (hash/checksum)

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

---

## Important Files Reference

| Path | Purpose | Status |
|------|---------|--------|
| `seadot-backend/api/app.py` | FastAPI entry point with CORS, WebSocket support | ✅ Complete |
| `seadot-backend/core/downloader.py` | Core download engine (stream-based) | ✅ Complete |
| `seadot-backend/db/models.py` | SQLAlchemy ORM models for downloads & history | ✅ Complete |
| `seadot-backend/db/service.py` | Database service layer with SQLite + singleton | ✅ Complete |
| `seadot-backend/middleware/auth_middleware.py` | Authentication middleware | ✅ Complete |
| `seadot-backend/run_dev.py` | Dev server runner with comprehensive logging | ✅ Complete |
| `seadot-backend/requirements.txt` | Python dependencies list | ✅ Complete |
| `seadot-backend/venv/` | Python virtual environment | ✅ Created |
| `seadot-frontend/package.json` | Frontend dependencies (React, Vite) | ✅ Complete |
| `seadot-frontend/tailwind.config.js` | Tailwind configuration | ✅ Complete |
| `seadot-frontend/vite.config.ts` | Vite configuration with React plugin | ✅ Complete |

---

## Status: Phase 1 Completed ✅

All environment setup and foundation project tasks are complete. Ready to proceed to Phase 3 (Advanced Features) or deploy for testing.
