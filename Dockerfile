# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
 && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Project files
COPY . .

# Collect static (if any) - safe even if none
RUN python manage.py collectstatic --noinput || true

# Default envs (can be overridden by compose)
ENV DJANGO_SETTINGS_MODULE=survey.settings \
    PORT=8000

# Healthcheck: basic HTTP check
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
 CMD curl -fsS http://127.0.0.1:${PORT}/ || exit 1

EXPOSE 8000

# Run with gunicorn
CMD ["gunicorn", "survey.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
