"""Phase 21 migration: finding-context columns on analysis_results.

    python backend/migrations/phase_21_finding_context.py
    python backend/migrations/phase_21_finding_context.py rollback
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import create_engine, inspect, text

from app.config import settings

TABLE = "analysis_results"
INDEX = "idx_analysis_results_relevance"

COLUMNS = [
    ("file_class", {"sqlite": "VARCHAR(30)", "default": "VARCHAR(30)"}),
    ("relevance", {"sqlite": "VARCHAR(20)", "default": "VARCHAR(20)"}),
    ("confidence", {"sqlite": "INTEGER", "default": "INTEGER"}),
    ("recommendation", {"sqlite": "VARCHAR(30)", "default": "VARCHAR(30)"}),
    ("finding_context", {"sqlite": "TEXT", "default": "JSON"}),
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

    print(f"Phase 21 migration on {dialect}: {TABLE}")

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
            text(f"CREATE INDEX IF NOT EXISTS {INDEX} ON {TABLE} (relevance)")
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

    print(f"Phase 21 rollback on {dialect}: {TABLE}")

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
