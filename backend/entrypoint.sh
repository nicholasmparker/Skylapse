#!/bin/bash
set -e

echo "🚀 Starting Skylapse Backend..."

# Run database migrations
echo "📊 Running database migrations..."
python3 /app/migrations/apply_migration.py /data/db/skylapse.db /app/migrations/001_add_hdr_columns.sql

echo "✅ Migrations complete"
echo ""

# Start the FastAPI application
echo "🌐 Starting FastAPI server..."
exec uvicorn main:app --host 0.0.0.0 --port 8082
