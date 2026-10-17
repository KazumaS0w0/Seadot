"""
Seadot Backend Dev Server Runner
Script untuk menjalankan FastAPI backend dengan proper logging & initialization.
"""

import sys
import os
import logging
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.middleware.cors import CORSMiddleware
from uvicorn import Config, Server


def setup_logging():
    """Setup console logging"""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )
    
    return logging.getLogger(__name__)


def main():
    """Run the backend server"""
    logger = setup_logging()
    logger.info("="*60)
    logger.info("  Seadot Download Manager - Backend Server")
    logger.info("="*60)
    
    try:
        # Import with absolute path
        from seadot_backend.api.app import app
        
        host = os.getenv("HOST", "127.0.0.1")
        port = int(os.getenv("PORT", 8000))
        
        logger.info(f"\n🚀 Starting server at http://{host}:{port}")
        logger.info(f"   📂 Backend folder: {Path(__file__).parent.absolute()}")
        logger.info(f"   🐍 Python version: {sys.version}")
        logger.info("="*60 + "\n")
        
        # Create uvicorn config
        config = Config(
            app=app,
            host=host,
            port=port,
            log_level="info",
            reload=True if os.getenv("RELOAD", "false").lower() == "true" else False,
            access_log=True,
            workers=int(os.getenv("WORKERS", 1))
        )
        
        # Run server
        logger.info(f"📡 Listening on http://{host}:{port}")
        logger.info("Press Ctrl+C to stop\n")
        config.run()
        
    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down gracefully...")
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
