from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.shortcuts import get_object_or_404

from .serializers import (
    SubmitBySessionSerializer, SubmitDirectSerializer, SurveyResponseReadSerializer
)
from .models import SurveyResponse
from .services import submit_from_session, submit_direct

class SubmitResponseView(APIView):
    """
    Accepts either:
    - { "session_id": X, "answers": {...optional overrides...} }
    - { "survey_id": S, "answers": {...}, "invitation_id": I?, "respondent_key": "..."? }
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # Try session-based first
        if "session_id" in request.data:
            ser = SubmitBySessionSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            try:
                resp = submit_from_session(
                    ser.validated_data["session_id"],
                    extra_answers=ser.validated_data.get("answers")
                )
            except ValueError as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            return Response(SurveyResponseReadSerializer(resp).data, status=status.HTTP_201_CREATED)

        # Otherwise direct submit
        ser = SubmitDirectSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            resp = submit_direct(
                ser.validated_data["survey_id"],
                ser.validated_data["answers"],
                invitation_id=ser.validated_data.get("invitation_id"),
                respondent_key=ser.validated_data.get("respondent_key"),
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(SurveyResponseReadSerializer(resp).data, status=status.HTTP_201_CREATED)

class ResponseDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, response_id: int):
        resp = get_object_or_404(SurveyResponse.objects.prefetch_related("answers"), pk=response_id)
        return Response(SurveyResponseReadSerializer(resp).data)
