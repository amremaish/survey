from django.db import models
from apps.core.models import TimeStampedModel
from apps.surveys.models import Survey

class InvitationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SENT = "sent", "Sent"
    BOUNCED = "bounced", "Bounced"
    COMPLETED = "completed", "Completed"
    EXPIRED = "expired", "Expired"

class SurveyInvitation(TimeStampedModel):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name="invitations")
    external_id = models.CharField(max_length=255, blank=True, null=True)  # email hash/customer id
    channel = models.CharField(max_length=32, blank=True, null=True)       # email|sms|link|embedded
    token = models.CharField(max_length=255, unique=True, blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=16, choices=InvitationStatus.choices, default=InvitationStatus.PENDING)
    metadata = models.JSONField(default=dict)

    def __str__(self):
        return f"inv#{self.id} -> survey#{self.survey_id}"

class SessionStatus(models.TextChoices):
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETED = "completed", "Completed"
    ABANDONED = "abandoned", "Abandoned"

class SurveySession(TimeStampedModel):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name="sessions")
    invitation = models.ForeignKey(SurveyInvitation, on_delete=models.SET_NULL, null=True, blank=True, related_name="sessions")
    # if you later attach auth.User, add a FK here; for now keep anonymous-capable
    status = models.CharField(max_length=16, choices=SessionStatus.choices, default=SessionStatus.IN_PROGRESS)
    last_step = models.IntegerField(blank=True, null=True)
    partial_payload = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["survey", "invitation"], name="uq_session_survey_invitation")
        ]

    def __str__(self):
        return f"session#{self.id} survey#{self.survey_id}"
