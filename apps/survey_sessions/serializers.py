from rest_framework import serializers
from .models import SurveyInvitation, SurveySession

class InvitationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyInvitation
        fields = ["external_id", "channel", "token", "expires_at", "status", "metadata"]

class InvitationReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyInvitation
        fields = ["id", "survey", "external_id", "channel", "token", "expires_at", "status", "metadata", "created_at", "updated_at"]

class SessionStartSerializer(serializers.Serializer):
    survey_id = serializers.IntegerField()
    invitation_id = serializers.IntegerField(required=False, allow_null=True)
    last_step = serializers.IntegerField(required=False, allow_null=True)

class SessionReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveySession
        fields = ["id", "survey", "invitation", "status", "last_step", "partial_payload", "created_at", "updated_at"]

class SessionAutosaveSerializer(serializers.Serializer):
    last_step = serializers.IntegerField(required=False, allow_null=True)
    partial_payload = serializers.JSONField(required=False)

class SessionCompleteSerializer(serializers.Serializer):
    pass  # no fields needed now; used to mark as completed
