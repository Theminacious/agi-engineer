"""Initialize database tables."""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from app.db import engine
from app.db.base import Base
from app.models.installation import Installation
from app.models.repository import Repository
from app.models.analysis_run import AnalysisRun
from app.models.analysis_result import AnalysisResult

def init_db():
    """Create all database tables."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created successfully!")

if __name__ == "__main__":
    init_db()
