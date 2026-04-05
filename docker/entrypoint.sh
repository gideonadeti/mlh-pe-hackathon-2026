#!/usr/bin/env sh
set -eu
cd /app
python scripts/create_tables.py
exec gunicorn --bind 0.0.0.0:8000 --workers 8 --timeout 120 wsgi:app
