"""Database migration for Phase 17 — GitHub Intelligence Integration.

Creates tables:
- github_webhook_events (webhook processing)
- pr_analyses (PR analysis tracking)
- github_integration_configs (per-repo settings)

Run this migration before deploying Phase 17.
"""

import os
import sys
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import create_engine, text
from app.config import settings


def run_migration():
    """Create Phase 17 tables."""
    
    print("=" * 60)
    print("Phase 17 Migration: GitHub Integration")
    print("=" * 60)
    print()
    
    # Create engine
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        print("Creating github_webhook_events table...")
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS github_webhook_events (
                id SERIAL PRIMARY KEY,
                delivery_id VARCHAR(100) UNIQUE NOT NULL,
                event_type VARCHAR(50) NOT NULL,
                signature_verified BOOLEAN NOT NULL DEFAULT FALSE,
                installation_id INTEGER NOT NULL REFERENCES installations(id),
                repository_full_name VARCHAR(255) NOT NULL,
                repository_id INTEGER,
                pr_number INTEGER,
                pr_head_sha VARCHAR(40),
                pr_base_branch VARCHAR(255),
                pr_head_branch VARCHAR(255),
                push_ref VARCHAR(255),
                push_before_sha VARCHAR(40),
                push_after_sha VARCHAR(40),
                raw_payload JSONB NOT NULL,
                processed_at TIMESTAMP,
                processing_error TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_webhook_delivery 
            ON github_webhook_events(delivery_id)
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_webhook_repo 
            ON github_webhook_events(repository_full_name)
        """))
        
        print("✓ github_webhook_events table created")
        print()
        
        print("Creating pr_analyses table...")
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS pr_analyses (
                id SERIAL PRIMARY KEY,
                repository_full_name VARCHAR(255) NOT NULL,
                pr_number INTEGER NOT NULL,
                head_sha VARCHAR(40) NOT NULL,
                base_branch VARCHAR(255) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                analysis_run_id INTEGER REFERENCES analysis_runs(id),
                ledger_run_id VARCHAR(100),
                reliability_score VARCHAR(20),
                critical_risks_count INTEGER NOT NULL DEFAULT 0,
                high_risks_count INTEGER NOT NULL DEFAULT 0,
                medium_risks_count INTEGER NOT NULL DEFAULT 0,
                fix_candidates_count INTEGER NOT NULL DEFAULT 0,
                auto_fixable_count INTEGER NOT NULL DEFAULT 0,
                comment_posted BOOLEAN NOT NULL DEFAULT FALSE,
                comment_id INTEGER,
                comment_posted_at TIMESTAMP,
                status_check_posted BOOLEAN NOT NULL DEFAULT FALSE,
                status_check_id INTEGER,
                status_check_conclusion VARCHAR(50),
                report_url VARCHAR(500),
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                analysis_error TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                webhook_event_id INTEGER REFERENCES github_webhook_events(id)
            )
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_pr_analyses_repo_pr 
            ON pr_analyses(repository_full_name, pr_number)
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_pr_analyses_sha 
            ON pr_analyses(head_sha)
        """))
        
        print("✓ pr_analyses table created")
        print()
        
        print("Creating github_integration_configs table...")
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS github_integration_configs (
                id SERIAL PRIMARY KEY,
                repository_id INTEGER UNIQUE NOT NULL REFERENCES repositories(id),
                auto_analysis_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                post_comments BOOLEAN NOT NULL DEFAULT TRUE,
                post_status_checks BOOLEAN NOT NULL DEFAULT TRUE,
                min_severity VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
                analyzer_categories JSONB,
                comment_template VARCHAR(50) NOT NULL DEFAULT 'standard',
                include_fix_snippets BOOLEAN NOT NULL DEFAULT TRUE,
                max_comments_per_pr INTEGER NOT NULL DEFAULT 10,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        
        print("✓ github_integration_configs table created")
        print()
        
        conn.commit()
    
    print("=" * 60)
    print("✅ Phase 17 Migration Complete")
    print("=" * 60)
    print()
    print("Tables created:")
    print("  - github_webhook_events")
    print("  - pr_analyses")
    print("  - github_integration_configs")
    print()
    print("Indexes created:")
    print("  - idx_webhook_delivery")
    print("  - idx_webhook_repo")
    print("  - idx_pr_analyses_repo_pr")
    print("  - idx_pr_analyses_sha")
    print()
    print("Ready to deploy Phase 17! 🚀")


def rollback_migration():
    """Drop Phase 17 tables (rollback)."""
    
    print("=" * 60)
    print("Phase 17 Rollback: Dropping GitHub Integration Tables")
    print("=" * 60)
    print()
    
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        print("Dropping github_integration_configs table...")
        conn.execute(text("DROP TABLE IF EXISTS github_integration_configs CASCADE"))
        print("✓ Dropped")
        
        print("Dropping pr_analyses table...")
        conn.execute(text("DROP TABLE IF EXISTS pr_analyses CASCADE"))
        print("✓ Dropped")
        
        print("Dropping github_webhook_events table...")
        conn.execute(text("DROP TABLE IF EXISTS github_webhook_events CASCADE"))
        print("✓ Dropped")
        
        conn.commit()
    
    print()
    print("=" * 60)
    print("✅ Phase 17 Rollback Complete")
    print("=" * 60)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_migration()
    else:
        run_migration()
