from rest_framework import serializers
from apps.accounts.models import Organization
from .models import (
    Survey, SurveySection, SurveyQuestion, SurveyQuestionOption,
    SurveyStatus, QuestionType, SurveyInvitation, InvitationStatus
)

class SurveyCreateSerializer(serializers.ModelSerializer):
    organization_id = serializers.IntegerField(write_only=True, required=False)
    class Meta:
        model = Survey
        fields = ["code", "title", "description", "status", "organization_id"]
        extra_kwargs = {
            "code": {"read_only": True},
        }

class SurveyListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Survey
        fields = ["id", "code", "title", "description", "status"]

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
        extra_kwargs = {
            "code": {"read_only": True},
        }

class OptionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyQuestionOption
        fields = ["value", "label", "sort_order", "metadata"]

class OptionBulkCreateSerializer(serializers.Serializer):
    options = OptionCreateSerializer(many=True)
    replace = serializers.BooleanField(required=False, default=False)

# LogicRule removed; constraints JSON on questions is used for logic

# Read serializer for nested detail
class OptionReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyQuestionOption
        fields = ["id", "value", "label", "sort_order"]

class QuestionReadSerializer(serializers.ModelSerializer):
    options = OptionReadSerializer(many=True, read_only=True)
    class Meta:
        model = SurveyQuestion
        fields = [
            "id", "code", "prompt", "type",
            "required", "sensitive", "constraints", "sort_order",
            "options"
        ]

class SectionReadSerializer(serializers.ModelSerializer):
    questions = QuestionReadSerializer(many=True, read_only=True)
    class Meta:
        model = SurveySection
        fields = ["id", "title", "sort_order", "questions"]

class SurveyDetailSerializer(serializers.ModelSerializer):
    sections = SectionReadSerializer(many=True, read_only=True)
    class OrgBriefSerializer(serializers.ModelSerializer):
        class Meta:
            model = Organization
            fields = ["id", "name", "logo"]
    # nested organization info for public runner
    organization = OrgBriefSerializer(read_only=True)
    class Meta:
        model = Survey
        fields = ["id", "title", "sections", "organization"]


class InvitationCreateSerializer(serializers.Serializer):
    survey_id = serializers.IntegerField()
    emails = serializers.ListField(child=serializers.EmailField(), allow_empty=False)
    expires_at = serializers.DateTimeField()


class InvitationReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyInvitation
        fields = ["id", "email", "token", "expires_at", "status", "created_at"]

