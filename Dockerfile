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

# Collect static (drf-spectacular-sidecar, etc.)
RUN python manage.py collectstatic --noinput || true

# Default envs (can be overridden by compose)
ENV DJANGO_SETTINGS_MODULE=survey.settings \
    PORT=8000

EXPOSE 8000

# Run with gunicorn
CMD ["gunicorn", "survey.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
