#!/usr/bin/env sh
set -eu
cd /app
python scripts/create_tables.py

# Gunicorn worker tuning: (2 * CPUs) + 1 is a standard recommendation.
# We'll use a dynamic calculation if WEB_CONCURRENCY is not set.
# Defaulting to 4 if we can't determine CPUs, or using the environment variable.
if [ -z "${WEB_CONCURRENCY:-}" ]; then
    # Busybox/Alpine friendly way to get CPU count
    CPUS=$(nproc 2>/dev/null || echo 1)
    WEB_CONCURRENCY=$((2 * CPUS + 1))
fi

echo "Starting Gunicorn with ${WEB_CONCURRENCY} workers"
exec gunicorn --bind 0.0.0.0:8000 --workers "${WEB_CONCURRENCY}" --timeout 120 wsgi:app
