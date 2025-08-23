from django.db import models
from apps.core.models import TimeStampedModel
from apps.accounts.models import Organization
from auditlog.registry import auditlog

class SurveyStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    ARCHIVED = "archived", "Archived"

class Survey(TimeStampedModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="surveys")
    code = models.SlugField(max_length=128, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=16, choices=SurveyStatus.choices, default=SurveyStatus.DRAFT)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.code}"

class SurveySection(TimeStampedModel):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name="sections")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    sort_order = models.IntegerField()

    class Meta:
        unique_together = ("survey", "sort_order")
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.survey_id}:{self.title}"

class QuestionType(models.TextChoices):
    TEXT = "text", "Text"
    NUMBER = "number", "Number"
    DATE = "date", "Date"
    DROPDOWN = "dropdown", "Dropdown"
    CHECKBOX = "checkbox", "Checkbox"
    RADIO = "radio", "Radio"

class SurveyQuestion(TimeStampedModel):
    section = models.ForeignKey(SurveySection, on_delete=models.CASCADE, related_name="questions")
    code = models.CharField(max_length=128)              # stable code used in answers/logic
    input_title = models.TextField()
    type = models.CharField(max_length=24, choices=QuestionType.choices)
    required = models.BooleanField(default=False)
    sensitive = models.BooleanField(default=False)       # if true, answer will be encrypted
    constraints = models.JSONField(default=dict)         # min/max/regex
    sort_order = models.IntegerField()
    metadata = models.JSONField(default=dict)

    class Meta:
        unique_together = (("section", "sort_order"), ("section", "code"))
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.section_id}:{self.code}"

class SurveyQuestionOption(TimeStampedModel):
    question = models.ForeignKey(SurveyQuestion, on_delete=models.CASCADE, related_name="options")
    value = models.CharField(max_length=255)
    label = models.CharField(max_length=255)
    sort_order = models.IntegerField()
    metadata = models.JSONField(default=dict)

    class Meta:
        unique_together = ("question", "sort_order")
        ordering = ["sort_order"]


class InvitationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SUBMITTED = "submitted", "Submitted"
    EXPIRED = "expired", "Expired"


class SurveyInvitation(TimeStampedModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="invitations")
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name="invitations")
    email = models.EmailField()
    token = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    status = models.CharField(max_length=16, choices=InvitationStatus.choices, default=InvitationStatus.PENDING)
    response_id = models.IntegerField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["survey", "status"], name="idx_inv_survey_status"),
            models.Index(fields=["token"], name="idx_inv_token"),
        ]

    def __str__(self):
        return f"inv:{self.email} -> {self.survey_id} ({self.status})"


# Register audit logging for survey models
auditlog.register(Survey)
auditlog.register(SurveySection)
auditlog.register(SurveyQuestion)
auditlog.register(SurveyQuestionOption)
auditlog.register(SurveyInvitation)
