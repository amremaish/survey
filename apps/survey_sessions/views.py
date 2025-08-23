from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.surveys.models import Survey, SurveyInvitation, InvitationStatus
from apps.accounts.models import Organization
from .models import SurveySession, SessionStatus
from .serializers import (
    SessionStartSerializer, SessionReadSerializer,
    SessionAutosaveSerializer
)

# Invitation endpoints removed

class SessionStartView(APIView):
    """
    Start or resume a session.
    If invitation_id provided and existing session found -> return it.
    Else create new session in IN_PROGRESS.
    """
    # Public to allow anonymous runners
    permission_classes = []

    def post(self, request):
        payload = SessionStartSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        survey = get_object_or_404(Survey, pk=payload.validated_data["survey_id"])
        org = None
        org_id = payload.validated_data.get("organization_id")
        if org_id:
            org = get_object_or_404(Organization, pk=org_id)

        if org:
            existing = SurveySession.objects.filter(survey=survey, organization=org, status=SessionStatus.IN_PROGRESS).first()
            if existing:
                return Response(SessionReadSerializer(existing).data, status=status.HTTP_200_OK)

        token = (payload.validated_data.get("token") or "").strip()
        invited_email = None
        if token:
            inv = SurveyInvitation.objects.filter(token=token, survey=survey).first()
            if not inv:
                return Response({"detail": "Invalid invitation"}, status=status.HTTP_400_BAD_REQUEST)
            if inv.status == InvitationStatus.SUBMITTED:
                return Response({"detail": "Invitation already used"}, status=status.HTTP_400_BAD_REQUEST)
            from django.utils import timezone
            if inv.expires_at and inv.expires_at < timezone.now():
                return Response({"detail": "Invitation expired"}, status=status.HTTP_400_BAD_REQUEST)
            invited_email = inv.email

        sess = SurveySession.objects.create(
            survey=survey,
            organization=org,
            invitation_token=(token or None),
            invited_email=invited_email,
        )
        return Response(SessionReadSerializer(sess).data, status=status.HTTP_201_CREATED)

class SessionAutosaveView(APIView):
    """
    Update last_step and/or partial_payload while keeping status IN_PROGRESS.
    """
    permission_classes = []

    def patch(self, request, session_id: int):
        sess = get_object_or_404(SurveySession, pk=session_id)
        ser = SessionAutosaveSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        if "partial_payload" in ser.validated_data:
            payload = ser.validated_data["partial_payload"] or {}
            merged = {**(sess.partial_payload or {}), **payload}
            sess.partial_payload = merged

        if sess.status != SessionStatus.IN_PROGRESS:
            sess.status = SessionStatus.IN_PROGRESS

        sess.save()
        return Response(SessionReadSerializer(sess).data, status=status.HTTP_200_OK)

    def get(self, request, session_id: int):
        sess = get_object_or_404(SurveySession, pk=session_id)
        return Response(SessionReadSerializer(sess).data, status=status.HTTP_200_OK)

class SessionDetailView(APIView):
    permission_classes = []

    def get(self, request, session_id: int):
        sess = get_object_or_404(SurveySession, pk=session_id)
        return Response(SessionReadSerializer(sess).data, status=status.HTTP_200_OK)

class SessionCompleteView(APIView):
    """
    Mark session as completed (submission will be created in the next step).
    """
    permission_classes = []

    def post(self, request, session_id: int):
        sess = get_object_or_404(SurveySession, pk=session_id)
        sess.status = SessionStatus.COMPLETED
        sess.save()
        # (Next step will create SurveyResponse + SurveyAnswers based on submitted payload)
        return Response(SessionReadSerializer(sess).data, status=status.HTTP_200_OK)
