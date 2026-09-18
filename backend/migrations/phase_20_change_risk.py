"""Phase 20 migration: change-risk columns on pr_analyses.

Runs on SQLite and PostgreSQL. Startup's Base.metadata.create_all creates
missing tables but never adds columns to an existing one, so installations
created before Phase 20 need this.

    python backend/migrations/phase_20_change_risk.py
    python backend/migrations/phase_20_change_risk.py rollback
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import create_engine, inspect, text

from app.config import settings

TABLE = "pr_analyses"
INDEX = "idx_pr_analyses_change_risk_level"

COLUMNS = [
    ("change_risk_level", {"sqlite": "VARCHAR(20)", "default": "VARCHAR(20)"}),
    ("change_risk_recommendation", {"sqlite": "VARCHAR(50)", "default": "VARCHAR(50)"}),
    ("change_risk_base_revision", {"sqlite": "VARCHAR(255)", "default": "VARCHAR(255)"}),
    ("change_risk_hash", {"sqlite": "VARCHAR(64)", "default": "VARCHAR(64)"}),
    ("change_risk_report", {"sqlite": "TEXT", "default": "JSON"}),
    ("change_risk_error", {"sqlite": "TEXT", "default": "TEXT"}),
]


def _column_type(dialect: str, spec: dict) -> str:
    return spec.get(dialect, spec["default"])


def _existing_columns(engine) -> set:
    inspector = inspect(engine)
    if TABLE not in inspector.get_table_names():
        raise SystemExit(
            f"Table '{TABLE}' does not exist. Start the application once so "
            f"Base.metadata.create_all creates it, then re-run this migration."
        )
    return {column["name"] for column in inspector.get_columns(TABLE)}


def run_migration() -> None:
    engine = create_engine(settings.database_url)
    dialect = engine.dialect.name
    present = _existing_columns(engine)

    print(f"Phase 20 migration on {dialect}: {TABLE}")

    added = []
    with engine.begin() as conn:
        for name, spec in COLUMNS:
            if name in present:
                print(f"  = {name} already present")
                continue
            column_type = _column_type(dialect, spec)
            conn.execute(text(f"ALTER TABLE {TABLE} ADD COLUMN {name} {column_type}"))
            added.append(name)
            print(f"  + {name} {column_type}")

        conn.execute(
            text(f"CREATE INDEX IF NOT EXISTS {INDEX} ON {TABLE} (change_risk_level)")
        )

    remaining = {name for name, _ in COLUMNS} - _existing_columns(engine)
    if remaining:
        raise SystemExit(f"Migration incomplete, still missing: {sorted(remaining)}")

    print(f"Done. {len(added)} column(s) added, index {INDEX} present.")


def rollback_migration() -> None:
    engine = create_engine(settings.database_url)
    dialect = engine.dialect.name
    present = _existing_columns(engine)

    if dialect == "sqlite":
        sqlite_version = tuple(
            int(part) for part in engine.dialect.server_version_info or (0,)
        )
        if sqlite_version and sqlite_version < (3, 35):
            raise SystemExit(
                "SQLite < 3.35 cannot DROP COLUMN. Restore from a backup instead."
            )

    print(f"Phase 20 rollback on {dialect}: {TABLE}")

    with engine.begin() as conn:
        conn.execute(text(f"DROP INDEX IF EXISTS {INDEX}"))
        for name, _ in COLUMNS:
            if name not in present:
                print(f"  = {name} already absent")
                continue
            conn.execute(text(f"ALTER TABLE {TABLE} DROP COLUMN {name}"))
            print(f"  - {name}")

    print("Rollback complete.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_migration()
    else:
        run_migration()
