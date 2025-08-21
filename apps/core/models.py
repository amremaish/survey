from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """Abstract: created/updated timestamps with int PK via DEFAULT_AUTO_FIELD."""
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        return super().save(*args, **kwargs)
