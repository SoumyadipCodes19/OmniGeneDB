#!/bin/sh
set -e

# Ensure persistent mount directory exists
mkdir -p /app/data

# If /app/data is empty, copy seed data from /app/seed
if [ -z "$(ls -A /app/data 2>/dev/null)" ]; then
    echo "[docker-entrypoint] /app/data is empty. Initializing from /app/seed..."
    if [ -d "/app/seed" ] && [ -n "$(ls -A /app/seed 2>/dev/null)" ]; then
        cp -r /app/seed/* /app/data/
        echo "[docker-entrypoint] Seed data successfully copied to /app/data."
    fi
else
    echo "[docker-entrypoint] /app/data already contains data; skipping seeding."
fi

# Ensure runs directory exists within /app/data
mkdir -p /app/data/runs

# If custom command line arguments were passed, execute them
if [ "$#" -gt 0 ]; then
    exec "$@"
fi

# Default: start Uvicorn ASGI server
echo "[docker-entrypoint] Starting OmniGeneDB API server on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
