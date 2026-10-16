"""
Seadot Database Models (SQLAlchemy)
Untuk persistence download state & history.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Download(Base):
    """Model untuk menyimpan info download (history & active)"""
    
    __tablename__ = "downloads"
    
    id = Column(Integer, primary_key=True, index=True)
    download_id = Column(String(128), unique=True, nullable=False, index=True)
    url = Column(String(512), nullable=False)
    dest_path = Column(String(512), nullable=False)
    headers_json = Column(Text)  # JSON serialized headers
    
    # Progress state
    total_size = Column(Integer, default=0)
    downloaded_size = Column(Integer, default=0)
    chunk_size = Column(Integer, default=8*1024*1024)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Status
    status = Column(String(20), default="pending")  # pending, downloading, paused, completed, failed
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "download_id": self.download_id,
            "url": self.url,
            "dest_path": self.dest_path,
            "headers_json": self.headers_json,
            "total_size": self.total_size,
            "downloaded_size": self.downloaded_size,
            "chunk_size": self.chunk_size,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status,
        }


class DownloadHistory(Base):
    """Model untuk history download (setelah selesai)"""
    
    __tablename__ = "download_history"
    
    id = Column(Integer, primary_key=True, index=True)
    download_id = Column(String(128), unique=True, nullable=False, index=True)
    url = Column(String(512), nullable=False)
    dest_path = Column(String(512), nullable=False)
    
    # Final state
    total_size = Column(Integer)
    downloaded_size = Column(Integer, nullable=False)
    chunk_size = Column(Integer)
    
    # Performance metrics
    duration_seconds = Column(Float)  # Total download duration
    avg_speed = Column(Float)  # Average speed in B/s
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


# Create tables
def init_db(drop_all: bool = False):
    """Initialize database (SQLITE by default)"""
    from sqlalchemy import create_engine
    import os
    
    db_path = os.getenv("DB_PATH", "../seadot.db")
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    
    if drop_all:
        Base.metadata.drop_all(bind=engine)
        
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully!")

