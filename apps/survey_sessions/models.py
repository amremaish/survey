from django.db import models
from apps.core.models import TimeStampedModel
from auditlog.registry import auditlog
from apps.surveys.models import Survey
from apps.accounts.models import Organization

class SessionStatus(models.TextChoices):
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETED = "completed", "Completed"
    ABANDONED = "abandoned", "Abandoned"

class SurveySession(TimeStampedModel):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name="sessions")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="sessions", null=True, blank=True)
    status = models.CharField(max_length=16, choices=SessionStatus.choices, default=SessionStatus.IN_PROGRESS)
    partial_payload = models.JSONField(default=dict)
    invitation_token = models.CharField(max_length=64, blank=True, null=True)
    invited_email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return f"session#{self.id} survey#{self.survey_id}"


# Register for audit logging
auditlog.register(SurveySession)
