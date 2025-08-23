from rest_framework import serializers
from .models import SurveyResponse, SurveyAnswer
from .services import _decrypt_value

class SurveyAnswerReadSerializer(serializers.ModelSerializer):
    value = serializers.SerializerMethodField()

    class Meta:
        model = SurveyAnswer
        fields = ["id", "question", "value"]

    def get_value(self, obj: SurveyAnswer):
        # Decrypt if encrypted_value is present
        if getattr(obj, 'encrypted_value', None) is not None:
            return _decrypt_value(obj.encrypted_value, None)
        # Prefer explicit typed columns in a stable order
        if obj.value_text is not None:
            return obj.value_text
        if obj.value_number is not None:
            try:
                # Emit as JSON number; fall back to float for simplicity
                return float(obj.value_number)
            except Exception:
                # As a last resort, stringify
                return str(obj.value_number)
        if obj.value_boolean is not None:
            return bool(obj.value_boolean)
        if obj.value_date is not None:
            # DRF will render date objects as YYYY-MM-DD
            return obj.value_date
        if obj.value_timestamp is not None:
            # DRF will render datetimes as ISO 8601 strings
            return obj.value_timestamp
        return None

class SurveyResponseReadSerializer(serializers.ModelSerializer):
    answers = SurveyAnswerReadSerializer(many=True, read_only=True)
    class Meta:
        model = SurveyResponse
        fields = ["id", "survey", "session", "status", "submitted_at", "answers"]


class SurveyBriefSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    code = serializers.CharField()


class ResponseDashboardSerializer(serializers.ModelSerializer):
    survey = serializers.SerializerMethodField()
    respondent_email = serializers.EmailField()

    class Meta:
        model = SurveyResponse
        fields = ["id", "survey", "status", "submitted_at", "respondent_email"]

    def get_survey(self, obj: SurveyResponse):
        s = obj.survey
        return {"id": s.id, "title": s.title, "code": s.code}


class SurveyAnswerDetailSerializer(serializers.ModelSerializer):
    value = serializers.SerializerMethodField()
    question_code = serializers.SerializerMethodField()
    question_prompt = serializers.SerializerMethodField()
    section_title = serializers.SerializerMethodField()

    class Meta:
        model = SurveyAnswer
        fields = [
            "id", "question", "question_code", "question_prompt", "section_title", "value"
        ]

    def get_value(self, obj: SurveyAnswer):
        if getattr(obj, 'encrypted_value', None) is not None:
            return _decrypt_value(obj.encrypted_value, None)
        if obj.value_text is not None:
            return obj.value_text
        if obj.value_number is not None:
            try:
                return float(obj.value_number)
            except Exception:
                return str(obj.value_number)
        if obj.value_boolean is not None:
            return bool(obj.value_boolean)
        if obj.value_date is not None:
            return obj.value_date
        if obj.value_timestamp is not None:
            return obj.value_timestamp
        return None

    def get_question_code(self, obj: SurveyAnswer):
        try:
            return obj.question.code
        except Exception:
            return None

    def get_question_prompt(self, obj: SurveyAnswer):
        try:
            return obj.question.prompt
        except Exception:
            return None

    def get_section_title(self, obj: SurveyAnswer):
        try:
            return obj.question.section.title
        except Exception:
            return None


class ResponseDetailForOrgSerializer(serializers.ModelSerializer):
    survey = serializers.SerializerMethodField()
    answers = SurveyAnswerDetailSerializer(many=True, read_only=True)

    class Meta:
        model = SurveyResponse
        fields = ["id", "survey", "status", "submitted_at", "answers"]

    def get_survey(self, obj: SurveyResponse):
        s = obj.survey
        org = s.organization
        return {
            "id": s.id,
            "title": s.title,
            "code": s.code,
            "organization": {
                "id": (org.id if org else None),
                "name": (org.name if org else None),
                "logo": (getattr(org.logo, 'url', None) if (org and getattr(org, 'logo', None)) else None),
            },
        }

# Submission payloads
class SubmitBySessionSerializer(serializers.Serializer):
    session_id = serializers.IntegerField()
    # Optional extra/overrides to merge with session draft
    answers = serializers.DictField(child=serializers.JSONField(allow_null=True), required=False)

class SubmitDirectSerializer(serializers.Serializer):
    survey_id = serializers.IntegerField()
    answers = serializers.DictField(child=serializers.JSONField(allow_null=True))
