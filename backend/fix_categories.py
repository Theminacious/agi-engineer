#!/usr/bin/env python3
"""
Fix categories for existing analysis results using RuleClassifier
Run this to update old records with correct categories
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.analysis_result import AnalysisResult, IssueCategory
from agent.rule_classifier import RuleClassifier, RuleCategory
from app.config import settings

def fix_categories():
    """Update categories for all Python analysis results"""
    
    # Create database session
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    classifier = RuleClassifier()
    
    try:
        # Get all Python results
        results = db.query(AnalysisResult).filter(
            AnalysisResult.issue_code.isnot(None)
        ).all()
        
        updated_count = 0
        fixed_count = 0
        
        for result in results:
            # Classify the issue
            classification = classifier.classify(result.issue_code)
            old_category = result.category
            
            # Map RuleCategory to IssueCategory
            if classification.get('category') == RuleCategory.SAFE:
                new_category = IssueCategory.SAFE
                should_fix = 1
            elif classification.get('category') == RuleCategory.RISKY:
                new_category = IssueCategory.REVIEW
                should_fix = 0
            else:
                new_category = IssueCategory.SUGGESTION
                should_fix = 0
            
            # Update if changed
            if result.category != new_category:
                result.category = new_category
                result.is_fixed = should_fix
                updated_count += 1
                
                if should_fix:
                    fixed_count += 1
                
                print(f"Updated {result.issue_code} ({result.file_path}:{result.line_number})")
                print(f"  {old_category.value} → {new_category.value} (fixed: {bool(should_fix)})")
        
        # Commit changes
        db.commit()
        
        print(f"\n✅ Updated {updated_count} records")
        print(f"✅ Marked {fixed_count} as fixed")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("Fixing categories for existing analysis results...")
    print("=" * 60)
    fix_categories()
