from __future__ import annotations

from datetime import timedelta
from django.db.models.functions import TruncDate, TruncWeek
from django.db.models import Count
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions

from apps.responses.models import SurveyResponse
from apps.surveys.models import SurveyInvitation, InvitationStatus, SurveyStatus
from apps.core.permissions import HasAllRoles
from apps.core.enums import Roles


class OverallSubmissionsView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasAllRoles]
    required_roles = [Roles.VIEWER]

    def get(self, request):
        """
        Returns time series of submissions grouped by day or ISO week.

        Query params:
          - window: 'day' (default) or 'week'
          - days: lookback window in days (default 30)
        Response:
          { labels: [...], data: [...] }
        """
        window = (request.query_params.get("window") or "day").lower()
        try:
            days = int(request.query_params.get("days", 30))
        except ValueError:
            days = 30
        days = max(1, min(365, days))

        since = timezone.now() - timedelta(days=days)
        qs = SurveyResponse.objects.filter(submitted_at__gte=since)

        if window == "week":
            series = (
                qs.annotate(bucket=TruncWeek("submitted_at"))
                  .values("bucket")
                  .order_by("bucket")
                  .annotate(count=Count("id"))
            )
            labels = [s["bucket"].date().isoformat() for s in series]
            data = [s["count"] for s in series]
        else:
            series = (
                qs.annotate(bucket=TruncDate("submitted_at"))
                  .values("bucket")
                  .order_by("bucket")
                  .annotate(count=Count("id"))
            )
            labels = [s["bucket"].isoformat() for s in series]
            data = [s["count"] for s in series]

        return Response({"labels": labels, "data": data})


class SubmissionsByOrganizationView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasAllRoles]
    required_roles = [Roles.VIEWER]

    def get(self, request):
        """Total responses per organization (top N, default 10)."""
        try:
            top_n = int(request.query_params.get("top", 10))
        except ValueError:
            top_n = 10
        top_n = max(1, min(50, top_n))

        series = (
            SurveyResponse.objects
            .values("survey__organization__name")
            .annotate(count=Count("id"))
            .order_by("-count")[:top_n]
        )
        labels = [s["survey__organization__name"] or "(No org)" for s in series]
        data = [s["count"] for s in series]
        return Response({"labels": labels, "data": data})


class InvitationStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasAllRoles]
    required_roles = [Roles.VIEWER]

    def get(self, request):
        """
        Counts invitations by status.
        Optional filters: org_id, survey_id
        """
        qs = SurveyInvitation.objects.all()
        org_id = request.query_params.get("org_id")
        survey_id = request.query_params.get("survey_id")
        try:
            if org_id:
                qs = qs.filter(organization_id=int(org_id))
        except ValueError:
            pass
        try:
            if survey_id:
                qs = qs.filter(survey_id=int(survey_id))
        except ValueError:
            pass

        statuses = [InvitationStatus.PENDING, InvitationStatus.SUBMITTED, InvitationStatus.EXPIRED]
        counts = {s: qs.filter(status=s).count() for s in statuses}
        labels = ["pending", "submitted", "expired"]
        data = [counts.get(InvitationStatus.PENDING, 0), counts.get(InvitationStatus.SUBMITTED, 0), counts.get(InvitationStatus.EXPIRED, 0)]
        return Response({"labels": labels, "data": data})


class ResponsesBySurveyStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasAllRoles]
    required_roles = [Roles.VIEWER]

    def get(self, request):
        """Counts responses grouped by parent survey status (draft/active/archived)."""
        series = (
            SurveyResponse.objects
            .values("survey__status")
            .annotate(count=Count("id"))
        )
        # Ensure stable order draft/active/archived
        order = [SurveyStatus.DRAFT, SurveyStatus.ACTIVE, SurveyStatus.ARCHIVED]
        map_counts = {row["survey__status"]: row["count"] for row in series}
        labels = ["draft", "active", "archived"]
        data = [map_counts.get(s, 0) for s in order]
        return Response({"labels": labels, "data": data})
