"""
Deterministic ID generation for proposals and strategies.

Instead of uuid.uuid4(), we generate deterministic IDs based on content hash.
This ensures:
- Same proposal content → Same proposal ID
- Determinism for ledger replay
- Reproducibility for debugging
- Content-addressed identity

Strategy:
- Hash proposal content (problem_statement, bug_class, etc.)
- Use first 16 hex digits as proposal_id (same length as UUID hex)
- Same for strategies: hash strategy content
"""

import hashlib
import json
from typing import Any, Dict


def generate_proposal_id(
    bug_class: str,
    problem_statement: str,
    affected_files: list,
    severity: str,
) -> str:
    """
    Generate deterministic proposal ID from content.
    
    Args:
        bug_class: BugClass enum value
        problem_statement: Problem description
        affected_files: List of affected file paths
        severity: Severity enum value
    
    Returns:
        Deterministic ID (formatted like UUID for compatibility)
    
    Properties:
        - Deterministic (same input → same output)
        - Fast (SHA256 hash)
        - Collision-free for practical purposes
    """
    # Create content hash input
    content = {
        "bug_class": bug_class,
        "problem_statement": problem_statement,
        "affected_files": sorted([f.get("path", f) if isinstance(f, dict) else str(f) for f in affected_files]),
        "severity": severity,
    }
    
    # Hash content
    content_json = json.dumps(content, sort_keys=True)
    content_hash = hashlib.sha256(content_json.encode()).hexdigest()
    
    # Format as UUID-like string for compatibility
    # UUID format: 8-4-4-4-12 hex digits
    # We'll use hash[0:8]-hash[8:12]-hash[12:16]-hash[16:20]-hash[20:32]
    proposal_id = f"{content_hash[0:8]}-{content_hash[8:12]}-{content_hash[12:16]}-{content_hash[16:20]}-{content_hash[20:32]}"
    
    return proposal_id


def generate_strategy_id(
    name: str,
    description: str,
    effort_estimate: str,
) -> str:
    """
    Generate deterministic strategy ID from content.
    
    Args:
        name: Strategy name
        description: Strategy description
        effort_estimate: Effort level
    
    Returns:
        Deterministic ID (formatted like UUID for compatibility)
    
    Properties:
        - Deterministic
        - Unique per strategy (different strategies → different IDs)
    """
    content = {
        "name": name,
        "description": description,
        "effort_estimate": effort_estimate,
    }
    
    content_json = json.dumps(content, sort_keys=True)
    content_hash = hashlib.sha256(content_json.encode()).hexdigest()
    
    strategy_id = f"{content_hash[0:8]}-{content_hash[8:12]}-{content_hash[12:16]}-{content_hash[16:20]}-{content_hash[20:32]}"
    
    return strategy_id


def generate_ledger_entry_id(
    analyzer_name: str,
    proposal_id: str,
    timestamp_ms: int,
) -> str:
    """
    Generate deterministic ledger entry ID.
    
    This is used for ledger_event() to ensure deterministic recording.
    
    Args:
        analyzer_name: Name of analyzer that created proposal
        proposal_id: The proposal ID
        timestamp_ms: Unix timestamp in milliseconds
    
    Returns:
        Deterministic ledger entry ID
    """
    content = {
        "analyzer": analyzer_name,
        "proposal": proposal_id,
        "timestamp_ms": timestamp_ms,
    }
    
    content_json = json.dumps(content, sort_keys=True)
    content_hash = hashlib.sha256(content_json.encode()).hexdigest()
    
    entry_id = content_hash[0:16]
    
    return entry_id
