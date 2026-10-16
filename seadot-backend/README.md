# Seadot Backend

Modern Download Manager - Python Core Engine (FastAPI + Async)

## Struktur Folder
```
seadot-backend/
├── api/              # FastAPI routes & endpoints
├── db/               # Database models & sessions
├── core/             # Core download engine logic
├── middleware/       # Custom middleware
├── .env.example      # Environment template
├── requirements.txt  # Python dependencies
└── run_dev.py        # Development server runner
```

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Create environment file (optional)
cp .env.example .env

# Run development server
python run_dev.py
```

## API Endpoints (Fase 3)
- `POST /start` - Mulai unduhan
- `POST /pause` - Pause unduhan
- `POST /resume` - Resume unduhan
- `DELETE /remove` - Hapus dari antrean

## WebSockets
Connected to `/ws/{download_id}` untuk real-time progress updates.