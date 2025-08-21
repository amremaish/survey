from rest_framework import serializers
from .models import SurveyResponse, SurveyAnswer

class SurveyAnswerReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyAnswer
        fields = [
            "id", "question", "value_text", "value_number", "value_boolean",
            "value_date", "value_timestamp", "value_json"
        ]

class SurveyResponseReadSerializer(serializers.ModelSerializer):
    answers = SurveyAnswerReadSerializer(many=True, read_only=True)
    class Meta:
        model = SurveyResponse
        fields = ["id", "survey", "session", "invitation", "status", "submitted_at", "answers"]

# Submission payloads
class SubmitBySessionSerializer(serializers.Serializer):
    session_id = serializers.IntegerField()
    # Optional extra/overrides to merge with session draft
    answers = serializers.DictField(child=serializers.JSONField(), required=False)

class SubmitDirectSerializer(serializers.Serializer):
    survey_id = serializers.IntegerField()
    answers = serializers.DictField(child=serializers.JSONField())
    invitation_id = serializers.IntegerField(required=False)
    respondent_key = serializers.CharField(required=False, allow_blank=True, allow_null=True)
