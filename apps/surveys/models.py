from django.db import models
from apps.core.models import TimeStampedModel

class SurveyStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    ARCHIVED = "archived", "Archived"

class Survey(TimeStampedModel):
    # int PK via DEFAULT_AUTO_FIELD
    code = models.SlugField(max_length=128)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=16, choices=SurveyStatus.choices, default=SurveyStatus.DRAFT)
    version = models.IntegerField(default=1)
    settings = models.JSONField(default=dict)

    class Meta:
        unique_together = ("code", "version")
        indexes = [
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.code}@v{self.version}"

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
    prompt = models.TextField()
    help_text = models.TextField(blank=True, null=True)
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

class QuestionDependency(TimeStampedModel):
    """Q_dep depends on Q_src. 'rule' holds JSON describing allowed options/visibility/filtering."""
    question = models.ForeignKey(SurveyQuestion, on_delete=models.CASCADE, related_name="dependencies")  # dependent
    depends_on = models.ForeignKey(SurveyQuestion, on_delete=models.CASCADE, related_name="dependents")   # source
    rule = models.JSONField()  # e.g. {"if": {"Q1": "eg"}, "options": ["Cairo","Alex"]}

class LogicScope(models.TextChoices):
    SECTION = "section", "Section"
    QUESTION = "question", "Question"

class LogicEffect(models.TextChoices):
    SHOW = "show", "Show"
    HIDE = "hide", "Hide"
    ENABLE = "enable", "Enable"
    DISABLE = "disable", "Disable"
    REQUIRE = "require", "Require"

class LogicRule(TimeStampedModel):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name="logic_rules")
    scope = models.CharField(max_length=16, choices=LogicScope.choices)
    target_id = models.IntegerField()           # id of SurveySection or SurveyQuestion (int PKs)
    effect = models.CharField(max_length=16, choices=LogicEffect.choices)
    condition = models.JSONField()              # JSON logic object
