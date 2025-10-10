#!/usr/bin/env python3
"""
Apply database migration safely (idempotent)

Usage:
    python3 apply_migration.py <path_to_db> <migration_file>

Example:
    python3 apply_migration.py data/db/skylapse.db migrations/001_add_hdr_columns.sql
"""

import sys
import sqlite3
from pathlib import Path


def column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def index_exists(cursor, index_name):
    """Check if an index exists"""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name=?", (index_name,))
    return cursor.fetchone() is not None


def apply_migration_safe(db_path, migration_file):
    """Apply migration only if columns don't already exist"""

    print(f"📋 Applying migration: {migration_file}")
    print(f"📁 Database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Define columns to add
        columns_to_add = [
            ("is_bracket", "BOOLEAN DEFAULT FALSE"),
            ("bracket_index", "INTEGER"),
            ("bracket_ev_offset", "REAL"),
            ("is_hdr_result", "BOOLEAN DEFAULT FALSE"),
            ("hdr_result_id", "INTEGER REFERENCES captures(id)"),
            ("source_bracket_ids", "TEXT"),
        ]

        # Add columns if they don't exist
        for col_name, col_def in columns_to_add:
            if column_exists(cursor, "captures", col_name):
                print(f"  ⏭️  Column '{col_name}' already exists, skipping")
            else:
                cursor.execute(f"ALTER TABLE captures ADD COLUMN {col_name} {col_def}")
                print(f"  ✅ Added column '{col_name}'")

        # Create indexes if they don't exist
        indexes = [
            ("idx_is_bracket", "CREATE INDEX idx_is_bracket ON captures(is_bracket) WHERE is_bracket = TRUE"),
            ("idx_is_hdr_result", "CREATE INDEX idx_is_hdr_result ON captures(is_hdr_result) WHERE is_hdr_result = TRUE"),
            ("idx_hdr_result_id", "CREATE INDEX idx_hdr_result_id ON captures(hdr_result_id)"),
        ]

        for idx_name, idx_sql in indexes:
            if index_exists(cursor, idx_name):
                print(f"  ⏭️  Index '{idx_name}' already exists, skipping")
            else:
                cursor.execute(idx_sql)
                print(f"  ✅ Created index '{idx_name}'")

        conn.commit()
        print("\n✅ Migration applied successfully!")
        return True

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        return False

    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    db_path = Path(sys.argv[1])
    migration_file = Path(sys.argv[2])

    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        sys.exit(1)

    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        sys.exit(1)

    success = apply_migration_safe(db_path, migration_file.name)
    sys.exit(0 if success else 1)
