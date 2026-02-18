FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=project.settings.prod

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/nawwar.txt \
    && pip install --no-cache-dir gunicorn whitenoise sentry-sdk redis

# Copy project
COPY . .

# Create necessary directories
RUN mkdir -p logs staticfiles media

# Collect static files
RUN python manage.py collectstatic --noinput 2>/dev/null || true

# Make start script executable
RUN chmod +x start.sh

# Default port
ENV PORT=8000
EXPOSE 8000

# Start via shell script (handles migrations + gunicorn)
CMD ["/bin/sh", "start.sh"]
