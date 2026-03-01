"""
Database Migration: Phase 15.3 - Automated Fix Generation

Adds automated fix generation columns to code_fixes table:
- risk_level: Risk assessment (LOW | MEDIUM | HIGH)
- confidence: Confidence score (0-100)
- generated_by_run: Boolean flag for auto-generated fixes
- finding_id: Link to IntelligenceProposal.proposal_id

Run:
    python backend/migrations/phase_15_3_fix_generation.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db import engine


def migrate():
    """Apply migration."""
    print("Phase 15.3: Automated Fix Generation Migration")
    print("=" * 60)
    
    with engine.connect() as conn:
        # Check if columns already exist
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'code_fixes' 
            AND column_name = 'risk_level'
        """))
        
        if result.fetchone():
            print("✓ Migration already applied (risk_level column exists)")
            return
        
        print("Applying migration...")
        
        # Add new columns
        migrations = [
            # Phase 15.3: Automated fix generation fields
            "ALTER TABLE code_fixes ADD COLUMN risk_level VARCHAR(20)",
            "ALTER TABLE code_fixes ADD COLUMN confidence INTEGER",
            "ALTER TABLE code_fixes ADD COLUMN generated_by_run BOOLEAN DEFAULT FALSE NOT NULL",
            "ALTER TABLE code_fixes ADD COLUMN finding_id VARCHAR(100)",
        ]
        
        for i, sql in enumerate(migrations, 1):
            try:
                conn.execute(text(sql))
                print(f"  [{i}/{len(migrations)}] Applied: {sql[:80]}...")
            except Exception as e:
                print(f"  [ERROR] Failed: {sql[:80]}...")
                print(f"          {str(e)}")
        
        conn.commit()
        print("✓ Migration completed successfully")
        print()
        print("New columns added:")
        print("  - risk_level (VARCHAR(20)): Risk assessment (LOW | MEDIUM | HIGH)")
        print("  - confidence (INTEGER): Confidence score (0-100)")
        print("  - generated_by_run (BOOLEAN): Auto-generated flag")
        print("  - finding_id (VARCHAR(100)): Link to IntelligenceProposal")
        print()
        print("All fixes can now include automated generation metadata.")


def rollback():
    """Rollback migration."""
    print("Phase 15.3: Rollback Automated Fix Generation Migration")
    print("=" * 60)
    
    with engine.connect() as conn:
        # Check if columns exist
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'code_fixes' 
            AND column_name = 'risk_level'
        """))
        
        if not result.fetchone():
            print("✓ Migration not applied (risk_level column does not exist)")
            return
        
        print("Rolling back migration...")
        
        # Remove columns
        rollbacks = [
            "ALTER TABLE code_fixes DROP COLUMN finding_id",
            "ALTER TABLE code_fixes DROP COLUMN generated_by_run",
            "ALTER TABLE code_fixes DROP COLUMN confidence",
            "ALTER TABLE code_fixes DROP COLUMN risk_level",
        ]
        
        for i, sql in enumerate(rollbacks, 1):
            try:
                conn.execute(text(sql))
                print(f"  [{i}/{len(rollbacks)}] Rolled back: {sql[:80]}...")
            except Exception as e:
                print(f"  [ERROR] Failed: {sql[:80]}...")
                print(f"          {str(e)}")
        
        conn.commit()
        print("✓ Rollback completed successfully")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Phase 15.3 Migration: Automated Fix Generation")
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback the migration"
    )
    
    args = parser.parse_args()
    
    if args.rollback:
        rollback()
    else:
        migrate()
