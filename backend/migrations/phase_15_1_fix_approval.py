"""
Database Migration: Phase 15.1 - Governed Fix Approval
  
Adds governance columns to code_fixes table:
- Approval tracking (approved_by, approved_at, approval_plan)
- Application tracking (applied_by, applied_at, application_plan)
- Rejection tracking (rejected_by, rejected_at, rejection_reason)
- Ledger integration (ledger_run_id, approval_ledger_event_id, application_ledger_event_id)
- Application metadata (application_error, application_metadata, patch, file_path)

Run:
    python backend/migrations/phase_15_1_fix_approval.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db import engine

def migrate():
    """Apply migration."""
    print("Phase 15.1: Governed Fix Approval Migration")
    print("=" * 60)
    
    with engine.connect() as conn:
        # Check if columns already exist
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'code_fixes' 
            AND column_name = 'approved_by'
        """))
        
        if result.fetchone():
            print("✓ Migration already applied (approved_by column exists)")
            return
        
        print("Applying migration...")
        
        # Add new columns
        migrations = [
            # File path
            "ALTER TABLE code_fixes ADD COLUMN file_path VARCHAR(500)",
            "ALTER TABLE code_fixes ADD COLUMN patch TEXT",
            
            # Update status enum (add PROPOSED and APPROVED)
            """
            ALTER TABLE code_fixes 
            MODIFY COLUMN status ENUM(
                'pending', 'generated', 'proposed', 'approved', 
                'applied', 'rejected', 'failed'
            ) DEFAULT 'proposed'
            """,
            
            # Approval tracking
            "ALTER TABLE code_fixes ADD COLUMN approved_by VARCHAR(255)",
            "ALTER TABLE code_fixes ADD COLUMN approved_at DATETIME",
            "ALTER TABLE code_fixes ADD COLUMN approval_plan VARCHAR(50)",
            
            # Application tracking
            "ALTER TABLE code_fixes ADD COLUMN applied_by VARCHAR(255)",
            "ALTER TABLE code_fixes ADD COLUMN applied_at DATETIME",
            "ALTER TABLE code_fixes ADD COLUMN application_plan VARCHAR(50)",
            
            # Rejection tracking
            "ALTER TABLE code_fixes ADD COLUMN rejected_by VARCHAR(255)",
            "ALTER TABLE code_fixes ADD COLUMN rejected_at DATETIME",
            "ALTER TABLE code_fixes ADD COLUMN rejection_reason TEXT",
            
            # Ledger integration
            "ALTER TABLE code_fixes ADD COLUMN ledger_run_id VARCHAR(100)",
            "ALTER TABLE code_fixes ADD COLUMN approval_ledger_event_id VARCHAR(100)",
            "ALTER TABLE code_fixes ADD COLUMN application_ledger_event_id VARCHAR(100)",
            
            # Application outcome
            "ALTER TABLE code_fixes ADD COLUMN application_error TEXT",
            "ALTER TABLE code_fixes ADD COLUMN application_metadata JSON",
        ]
        
        for i, sql in enumerate(migrations, 1):
            try:
                conn.execute(text(sql))
                print(f"  [{i}/{len(migrations)}] Applied: {sql[:60]}...")
            except Exception as e:
                print(f"  [ERROR] Failed: {sql[:60]}...")
                print(f"          {str(e)}")
        
        conn.commit()
        print("✓ Migration completed successfully")
        print()
        print("New columns added:")
        print("  - file_path, patch")
        print("  - approved_by, approved_at, approval_plan")
        print("  - applied_by, applied_at, application_plan")
        print("  - rejected_by, rejected_at, rejection_reason")
        print("  - ledger_run_id, approval_ledger_event_id, application_ledger_event_id")
        print("  - application_error, application_metadata")

if __name__ == "__main__":
    migrate()
