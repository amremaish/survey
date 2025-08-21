from rest_framework import serializers
from .models import (
    Survey, SurveySection, SurveyQuestion, SurveyQuestionOption,
    LogicRule, QuestionDependency, SurveyStatus, QuestionType, LogicScope, LogicEffect
)

class SurveyCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Survey
        fields = ["code", "title", "description", "status", "version", "settings"]

class SurveyListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Survey
        fields = ["id", "code", "title", "status", "version"]

class SectionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveySection
        fields = ["title", "description", "sort_order"]

class QuestionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyQuestion
        fields = [
            "code", "prompt", "help_text", "type",
            "required", "sensitive", "constraints", "sort_order", "metadata"
        ]

class OptionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyQuestionOption
        fields = ["value", "label", "sort_order", "metadata"]

class OptionBulkCreateSerializer(serializers.Serializer):
    options = OptionCreateSerializer(many=True)

class LogicRuleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LogicRule
        fields = ["scope", "target_id", "effect", "condition"]

# Read serializer for nested detail
class OptionReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyQuestionOption
        fields = ["id", "value", "label", "sort_order", "metadata"]

class QuestionReadSerializer(serializers.ModelSerializer):
    options = OptionReadSerializer(many=True, read_only=True)
    class Meta:
        model = SurveyQuestion
        fields = [
            "id", "code", "prompt", "help_text", "type",
            "required", "sensitive", "constraints", "sort_order", "metadata",
            "options"
        ]

class SectionReadSerializer(serializers.ModelSerializer):
    questions = QuestionReadSerializer(many=True, read_only=True)
    class Meta:
        model = SurveySection
        fields = ["id", "title", "description", "sort_order", "questions"]

class SurveyDetailSerializer(serializers.ModelSerializer):
    sections = SectionReadSerializer(many=True, read_only=True)
    class Meta:
        model = Survey
        fields = ["id", "code", "title", "description", "status", "version", "settings", "sections"]
