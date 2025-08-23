from django.db import models
from apps.core.models import TimeStampedModel
from auditlog.registry import auditlog
from apps.surveys.models import Survey, SurveyQuestion
from apps.survey_sessions.models import SurveySession

class ResponseStatus(models.TextChoices):
    SUBMITTED = "submitted", "Submitted"
    REVISED   = "revised", "Revised"
    DELETED   = "deleted", "Deleted"

class SurveyResponse(TimeStampedModel):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name="responses")
    session = models.ForeignKey(SurveySession, on_delete=models.SET_NULL, null=True, blank=True, related_name="responses")
    respondent_email = models.EmailField(blank=True, null=True)
    status = models.CharField(max_length=16, choices=ResponseStatus.choices, default=ResponseStatus.SUBMITTED)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["survey", "-submitted_at"], name="idx_response_survey_time"),
        ]

    def __str__(self):
        return f"response#{self.id} survey#{self.survey_id}"

class SurveyAnswer(TimeStampedModel):
    response = models.ForeignKey(SurveyResponse, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(SurveyQuestion, on_delete=models.CASCADE, related_name="answers")

    # Typed values (one of these typically)
    value_text = models.TextField(blank=True, null=True)
    value_number = models.DecimalField(max_digits=30, decimal_places=10, blank=True, null=True)
    value_boolean = models.BooleanField(blank=True, null=True)
    value_date = models.DateField(blank=True, null=True)
    value_timestamp = models.DateTimeField(blank=True, null=True)
    encrypted_value = models.BinaryField(blank=True, null=True)

    class Meta:
        unique_together = ("response", "question")
        indexes = [
            models.Index(fields=["question"], name="idx_answer_question"),
        ]

    def __str__(self):
        return f"ans#{self.id} q#{self.question_id}"


# Register audit logging for responses models
auditlog.register(SurveyResponse)
auditlog.register(SurveyAnswer)
