#!/bin/sh
set -e

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput 2>/dev/null || true

echo "Loading knowledge base into ChromaDB..."
python manage.py load_knowledge 2>&1 || echo "Warning: knowledge base loading failed (non-fatal)"

echo "Starting gunicorn on port ${PORT:-8000}..."
exec gunicorn project.wsgi:application \
  --bind 0.0.0.0:${PORT:-8000} \
  --workers 3 \
  --timeout 120
