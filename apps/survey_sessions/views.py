from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from apps.surveys.models import Survey
from .models import SurveyInvitation, SurveySession, InvitationStatus, SessionStatus
from .serializers import (
    InvitationCreateSerializer, InvitationReadSerializer,
    SessionStartSerializer, SessionReadSerializer,
    SessionAutosaveSerializer, SessionCompleteSerializer
)

class InvitationCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, survey_id: int):
        survey = get_object_or_404(Survey, pk=survey_id)
        ser = InvitationCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        inv = ser.save(survey=survey)
        return Response(InvitationReadSerializer(inv).data, status=status.HTTP_201_CREATED)

class SessionStartView(APIView):
    """
    Start or resume a session.
    If invitation_id provided and existing session found -> return it.
    Else create new session in IN_PROGRESS.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        payload = SessionStartSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        survey = get_object_or_404(Survey, pk=payload.validated_data["survey_id"])
        invitation = None
        inv_id = payload.validated_data.get("invitation_id")
        if inv_id:
            invitation = get_object_or_404(SurveyInvitation, pk=inv_id, survey=survey)

        # resume existing?
        if invitation:
            existing = SurveySession.objects.filter(survey=survey, invitation=invitation).first()
            if existing:
                return Response(SessionReadSerializer(existing).data, status=status.HTTP_200_OK)

        sess = SurveySession.objects.create(
            survey=survey,
            invitation=invitation,
            last_step=payload.validated_data.get("last_step")
        )
        return Response(SessionReadSerializer(sess).data, status=status.HTTP_201_CREATED)

class SessionAutosaveView(APIView):
    """
    Update last_step and/or partial_payload while keeping status IN_PROGRESS.
    """
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, session_id: int):
        sess = get_object_or_404(SurveySession, pk=session_id)
        ser = SessionAutosaveSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        last_step = ser.validated_data.get("last_step", None)
        if last_step is not None:
            sess.last_step = last_step

        if "partial_payload" in ser.validated_data:
            # shallow merge (simple strategy); replace entirely if you prefer
            payload = ser.validated_data["partial_payload"] or {}
            merged = {**(sess.partial_payload or {}), **payload}
            sess.partial_payload = merged

        # ensure still in progress
        if sess.status != SessionStatus.IN_PROGRESS:
            sess.status = SessionStatus.IN_PROGRESS

        sess.save()
        return Response(SessionReadSerializer(sess).data, status=status.HTTP_200_OK)

class SessionCompleteView(APIView):
    """
    Mark session as completed (submission will be created in the next step).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, session_id: int):
        sess = get_object_or_404(SurveySession, pk=session_id)
        _ = SessionCompleteSerializer(data=request.data)
        _.is_valid(raise_exception=True)

        sess.status = SessionStatus.COMPLETED
        sess.save()
        # (Next step will create SurveyResponse + SurveyAnswers based on submitted payload)
        return Response(SessionReadSerializer(sess).data, status=status.HTTP_200_OK)
