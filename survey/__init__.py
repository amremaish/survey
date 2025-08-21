from __future__ import annotations
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'survey.settings')

# Make Celery optional during Django startup (e.g., for makemigrations without deps installed)
try:
    from celery import Celery  # type: ignore

    celery_app = Celery('survey')
    celery_app.config_from_object('django.conf:settings', namespace='CELERY')
    celery_app.autodiscover_tasks()
    __all__ = ('celery_app',)
except Exception:  # pragma: no cover - ignore missing Celery during setup
    celery_app = None
    __all__ = ()

