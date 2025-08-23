from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.shortcuts import get_object_or_404
from django.db.models import Q

from .serializers import (
    SubmitBySessionSerializer, SubmitDirectSerializer, SurveyResponseReadSerializer,
    ResponseDashboardSerializer, ResponseDetailForOrgSerializer,
)
from .models import SurveyResponse
from .services import submit_from_session, submit_direct
from apps.accounts.models import Organization, OrganizationMember

class SubmitResponseView(APIView):
    """
    Accepts either:
    - { "session_id": X, "answers": {...optional overrides...} }
    - { "survey_id": S, "answers": {...} }
    """
    # Public submission allowed
    permission_classes = []

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
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(SurveyResponseReadSerializer(resp).data, status=status.HTTP_201_CREATED)

class ResponseDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, response_id: int):
        resp = get_object_or_404(SurveyResponse.objects.select_related("survey").prefetch_related("answers"), pk=response_id)
        # Enforce organization membership
        org = resp.survey.organization
        if not OrganizationMember.objects.filter(organization=org, user=request.user).exists():
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        return Response(ResponseDetailForOrgSerializer(resp).data)


class OrgResponsesDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, org_id: int):
        # Ensure requesting user is a member of the organization
        org = get_object_or_404(Organization, pk=org_id)
        is_member = OrganizationMember.objects.filter(organization=org, user=request.user).exists()
        if not is_member:
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        qs = (
            SurveyResponse.objects
            .select_related("survey")
            .filter(survey__organization=org)
            .order_by("-submitted_at")
        )

        # Optional search by survey title or code
        search = (request.query_params.get("search") or "").strip()
        if search:
            qs = qs.filter(Q(survey__title__icontains=search) | Q(survey__code__icontains=search))

        # Basic pagination
        try:
            page = max(1, int(request.query_params.get("page", 1)))
        except ValueError:
            page = 1
        try:
            page_size = max(1, min(100, int(request.query_params.get("page_size", 10))))
        except ValueError:
            page_size = 10
        count = qs.count()
        start = (page - 1) * page_size
        end = start + page_size
        items = qs[start:end]
        data = ResponseDashboardSerializer(items, many=True).data
        return Response({"count": count, "results": data})
