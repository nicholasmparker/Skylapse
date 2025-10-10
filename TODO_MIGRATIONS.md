# TODO: Migrate to Alembic for Database Migrations

## Current State (Tech Debt)

We're using a custom migration system with:
- Individual SQL files in `backend/migrations/`
- Python script `apply_migration.py` that checks for existing columns/indexes
- Migrations run on backend startup via `entrypoint.sh`

**Problems:**
- No migration versioning/tracking
- No rollback capability
- Manual migration file creation
- Hard to manage multiple migrations
- No migration history in database
- Idempotency checks are manual (column_exists, index_exists)

## Recommended Solution: Alembic

[Alembic](https://alembic.sqlalchemy.org/) is the industry-standard migration tool for Python/SQLAlchemy.

**Benefits:**
- ✅ Automatic version tracking
- ✅ Up/down migrations (rollback support)
- ✅ Auto-generate migrations from SQLAlchemy models
- ✅ Migration history stored in database
- ✅ Branching and merging for team development
- ✅ Battle-tested and widely used

## Migration Plan

### Phase 1: Install Alembic
```bash
# Add to backend/requirements.txt
alembic==1.13.0
```

### Phase 2: Initialize Alembic
```bash
cd backend
alembic init alembic
```

### Phase 3: Configure
- Update `alembic.ini` with database URL
- Create SQLAlchemy models for existing tables
- Generate initial migration

### Phase 4: Convert Existing Migrations
- Create Alembic migration for HDR columns (replace 001_add_hdr_columns.sql)
- Test on dev environment
- Deploy to production

### Phase 5: Update Entrypoint
```bash
# Replace current migration runner with:
alembic upgrade head
```

## Priority

**Medium** - Current system works but will become painful as we add more migrations.

**Trigger:** When we have 3+ migration files, switch to Alembic.

## References

- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [FastAPI + Alembic Guide](https://fastapi.tiangolo.com/tutorial/sql-databases/#alembic-note)
- [SQLite with Alembic](https://alembic.sqlalchemy.org/en/latest/batch.html)

## Notes

- Current system is idempotent and safe
- No urgent need to migrate immediately
- Good to do before next major feature that needs schema changes
