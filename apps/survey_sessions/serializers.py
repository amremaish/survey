from rest_framework import serializers
from .models import SurveySession

class SessionStartSerializer(serializers.Serializer):
    survey_id = serializers.IntegerField()
    organization_id = serializers.IntegerField(required=False, allow_null=True)
    token = serializers.CharField(required=False, allow_blank=True, allow_null=True)

class SessionReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveySession
        fields = ["id", "survey", "organization", "status", "partial_payload", "invitation_token", "invited_email", "created_at", "updated_at"]

class SessionAutosaveSerializer(serializers.Serializer):
    partial_payload = serializers.JSONField(required=False)
