"""Database migration for Phase 18 — Reliability Insights Dashboard.

Creates tables:
- repo_metrics (aggregated repository reliability metrics)
- risk_snapshots (point-in-time risk snapshots for trends)
- reliability_scores (historical score tracking)
- reliability_hotspots (files with recurring issues)

Run this migration before deploying Phase 18.
"""

import os
import sys
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import create_engine, text
from app.config import settings


def run_migration():
    """Create Phase 18 tables."""
    
    print("=" * 60)
    print("Phase 18 Migration: Reliability Insights Dashboard")
    print("=" * 60)
    print()
    
    # Create engine
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        print("Creating repo_metrics table...")
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS repo_metrics (
                id SERIAL PRIMARY KEY,
                repository_id INTEGER NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
                reliability_score FLOAT NOT NULL DEFAULT 100.0,
                score_grade VARCHAR(2) NOT NULL DEFAULT 'A',
                
                -- Risk counts by severity
                critical_risks INTEGER NOT NULL DEFAULT 0,
                high_risks INTEGER NOT NULL DEFAULT 0,
                medium_risks INTEGER NOT NULL DEFAULT 0,
                low_risks INTEGER NOT NULL DEFAULT 0,
                total_risks INTEGER NOT NULL DEFAULT 0,
                
                -- Risk counts by category
                crash_risks INTEGER NOT NULL DEFAULT 0,
                resource_leaks INTEGER NOT NULL DEFAULT 0,
                reliability_antipatterns INTEGER NOT NULL DEFAULT 0,
                scalability_risks INTEGER NOT NULL DEFAULT 0,
                edge_case_vulnerabilities INTEGER NOT NULL DEFAULT 0,
                
                -- Fix metrics
                total_fixes_proposed INTEGER NOT NULL DEFAULT 0,
                total_fixes_approved INTEGER NOT NULL DEFAULT 0,
                total_fixes_applied INTEGER NOT NULL DEFAULT 0,
                total_fixes_failed INTEGER NOT NULL DEFAULT 0,
                fix_adoption_rate FLOAT NOT NULL DEFAULT 0.0,
                fix_success_rate FLOAT NOT NULL DEFAULT 0.0,
                
                -- PR analysis metrics
                total_prs_analyzed INTEGER NOT NULL DEFAULT 0,
                prs_with_critical_risks INTEGER NOT NULL DEFAULT 0,
                prs_with_high_risks INTEGER NOT NULL DEFAULT 0,
                prs_with_no_risks INTEGER NOT NULL DEFAULT 0,
                
                -- Trend indicators
                score_change_7d FLOAT,
                score_change_30d FLOAT,
                risk_trend_7d VARCHAR(20),
                risk_trend_30d VARCHAR(20),
                
                -- Timestamps
                last_analysis_at TIMESTAMP,
                last_fix_applied_at TIMESTAMP,
                last_score_update_at TIMESTAMP,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                
                UNIQUE(repository_id)
            );
        """))
        conn.commit()
        
        print("✓ repo_metrics table created")
        print()
        
        print("Creating risk_snapshots table...")
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS risk_snapshots (
                id SERIAL PRIMARY KEY,
                repo_metrics_id INTEGER NOT NULL REFERENCES repo_metrics(id) ON DELETE CASCADE,
                snapshot_type VARCHAR(50) NOT NULL,
                snapshot_reason TEXT,
                
                -- Risk counts at snapshot time
                critical_risks INTEGER NOT NULL DEFAULT 0,
                high_risks INTEGER NOT NULL DEFAULT 0,
                medium_risks INTEGER NOT NULL DEFAULT 0,
                low_risks INTEGER NOT NULL DEFAULT 0,
                total_risks INTEGER NOT NULL DEFAULT 0,
                reliability_score FLOAT NOT NULL,
                
                -- Context references
                pr_analysis_id INTEGER REFERENCES pr_analyses(id),
                analysis_run_id INTEGER REFERENCES analysis_runs(id),
                code_fix_id INTEGER REFERENCES code_fixes(id),
                ledger_run_id VARCHAR(100),
                
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
        """))
        conn.commit()
        
        print("✓ risk_snapshots table created")
        print()
        
        print("Creating index on risk_snapshots...")
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_risk_snapshots_repo_time
            ON risk_snapshots(repo_metrics_id, created_at DESC);
        """))
        conn.commit()
        
        print("✓ Index created")
        print()
        
        print("Creating reliability_scores table...")
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS reliability_scores (
                id SERIAL PRIMARY KEY,
                repo_metrics_id INTEGER NOT NULL REFERENCES repo_metrics(id) ON DELETE CASCADE,
                reliability_score FLOAT NOT NULL,
                score_grade VARCHAR(2) NOT NULL,
                
                -- Period aggregation
                period_type VARCHAR(20) NOT NULL,
                period_start TIMESTAMP NOT NULL,
                period_end TIMESTAMP NOT NULL,
                score_change FLOAT,
                
                -- Period statistics
                avg_critical_risks FLOAT NOT NULL DEFAULT 0.0,
                avg_high_risks FLOAT NOT NULL DEFAULT 0.0,
                avg_total_risks FLOAT NOT NULL DEFAULT 0.0,
                
                -- Activity counts
                prs_analyzed INTEGER NOT NULL DEFAULT 0,
                fixes_applied INTEGER NOT NULL DEFAULT 0,
                
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
        """))
        conn.commit()
        
        print("✓ reliability_scores table created")
        print()
        
        print("Creating index on reliability_scores...")
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_reliability_scores_repo_period
            ON reliability_scores(repo_metrics_id, period_start DESC);
        """))
        conn.commit()
        
        print("✓ Index created")
        print()
        
        print("Creating reliability_hotspots table...")
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS reliability_hotspots (
                id SERIAL PRIMARY KEY,
                repository_id INTEGER NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
                file_path TEXT NOT NULL,
                
                -- Risk statistics
                total_risks_found INTEGER NOT NULL DEFAULT 0,
                critical_risks INTEGER NOT NULL DEFAULT 0,
                high_risks INTEGER NOT NULL DEFAULT 0,
                primary_risk_category VARCHAR(100),
                
                -- Fix tracking
                fixes_proposed INTEGER NOT NULL DEFAULT 0,
                fixes_applied INTEGER NOT NULL DEFAULT 0,
                still_has_risks BOOLEAN NOT NULL DEFAULT TRUE,
                
                -- Scoring
                hotspot_score FLOAT NOT NULL DEFAULT 0.0,
                
                -- Timestamps
                first_seen_at TIMESTAMP NOT NULL DEFAULT NOW(),
                last_seen_at TIMESTAMP NOT NULL DEFAULT NOW(),
                last_fix_at TIMESTAMP,
                
                UNIQUE(repository_id, file_path)
            );
        """))
        conn.commit()
        
        print("✓ reliability_hotspots table created")
        print()
        
        print("Creating index on reliability_hotspots...")
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_hotspot_repo_file
            ON reliability_hotspots(repository_id, file_path);
        """))
        conn.commit()
        
        print("✓ Index created")
        print()
    
    print("=" * 60)
    print("Phase 18 Migration Complete ✓")
    print("=" * 60)
    print()
    print("Tables created:")
    print("  • repo_metrics")
    print("  • risk_snapshots")
    print("  • reliability_scores")
    print("  • reliability_hotspots")
    print()


def rollback_migration():
    """Drop Phase 18 tables (for testing/development)."""
    
    print("=" * 60)
    print("Phase 18 Rollback: Dropping tables")
    print("=" * 60)
    print()
    
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        print("WARNING: This will delete all reliability insights data!")
        confirm = input("Type 'yes' to confirm: ")
        
        if confirm.lower() != 'yes':
            print("Rollback cancelled")
            return
        
        print()
        print("Dropping reliability_hotspots...")
        conn.execute(text("DROP TABLE IF EXISTS reliability_hotspots CASCADE;"))
        conn.commit()
        
        print("Dropping reliability_scores...")
        conn.execute(text("DROP TABLE IF EXISTS reliability_scores CASCADE;"))
        conn.commit()
        
        print("Dropping risk_snapshots...")
        conn.execute(text("DROP TABLE IF EXISTS risk_snapshots CASCADE;"))
        conn.commit()
        
        print("Dropping repo_metrics...")
        conn.execute(text("DROP TABLE IF EXISTS repo_metrics CASCADE;"))
        conn.commit()
    
    print()
    print("Phase 18 tables dropped ✓")
    print()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_migration()
    else:
        run_migration()
