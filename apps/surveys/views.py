from __future__ import annotations
from typing import List
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from .tasks import create_invitations_task
from rest_framework import status, permissions
from apps.core.permissions import HasAllRoles
from django.core.paginator import Paginator
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.models import OrganizationMember
from .models import (
    Survey, SurveySection, SurveyQuestion, SurveyQuestionOption, SurveyStatus,
    SurveyInvitation, InvitationStatus
)
from .serializers import (
    SurveyCreateSerializer, SurveyListSerializer, SurveyDetailSerializer,
    SectionCreateSerializer, QuestionCreateSerializer,
    OptionCreateSerializer, OptionBulkCreateSerializer,
    QuestionReadSerializer, InvitationCreateSerializer, InvitationReadSerializer
)

from apps.core.utility import (
    parse_int as _parse_int,
    page_bounds as _page_bounds,
    unique_slug_for_code as _unique_slug_for_code,
    sort_order_conflict_exists as _sort_order_conflict_exists,
)
from apps.core.serializer import PaginationQuerySerializer
from apps.core.enums import Roles


class SurveyListCreateView(APIView):
    """
    GET: Paginated list with optional filters:
         - organization_id
         - status (must be a valid SurveyStatus)
         - search (case-insensitive match on title)
         Query params: page (default 1), page_size (default 10, max 100)

    POST: Create a new Survey.
          Requires `title` (and any fields in SurveyCreateSerializer).
          Organization can be provided as serializer field or request.data["organization_id"].
          Auto-generates a unique `code` from the title.
    """
    permission_classes = [permissions.IsAuthenticated, HasAllRoles]
    required_roles_by_method = {"GET": [Roles.VIEWER.value], "POST": [Roles.EDITOR.value]}

    def get(self, request):
        qs = (
            Survey.objects
            .select_related("organization")  # helpful if list serializer needs org info
            .order_by("id")
        )

        # Filter by organization_id (optional)
        org_id = request.query_params.get("organization_id")
        if org_id:
            oid = _parse_int(org_id, 0)
            if oid > 0:
                qs = qs.filter(organization_id=oid)

        # Filter by status (optional + validated)
        status_param = (request.query_params.get("status") or "").strip()
        if status_param in dict(SurveyStatus.choices):
            qs = qs.filter(status=status_param)

        # Simple search on title (optional)
        search = (request.query_params.get("search") or "").strip()
        if search:
            qs = qs.filter(title__icontains=search)

        # Pagination (standardized)
        pager_ser = PaginationQuerySerializer(data=request.query_params)
        pager_ser.is_valid(raise_exception=False)
        page = pager_ser.validated_data.get("page", 1)
        page_size = pager_ser.validated_data.get("page_size", 10)

        paginator = Paginator(qs, page_size)
        page_obj = paginator.get_page(page)
        return Response({
            "count": paginator.count,
            "results": SurveyListSerializer(page_obj.object_list, many=True).data,
        })

    @transaction.atomic
    def post(self, request):
        ser = SurveyCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        # Accept org from serializer or raw request to keep backward-compat
        org_id = data.get("organization_id") or request.data.get("organization_id")
        if not org_id:
            return Response(
                {"organization_id": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Resolve organization explicitly for clearer errors
        from apps.accounts.models import Organization  # local import to avoid circulars
        org = Organization.objects.filter(pk=_parse_int(org_id, 0)).first()
        if not org:
            return Response(
                {"organization_id": ["Invalid organization."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Collision-safe code generation from title
        base = (data.get("title") or "").strip()
        code = _unique_slug_for_code(Survey, base)

        survey = ser.save(organization=org, code=code)
        return Response(SurveyDetailSerializer(survey).data, status=status.HTTP_201_CREATED)


class SurveyDetailView(APIView):
    """
    GET: Return a survey with sections/questions/options.
    PATCH: Partial update; organization cannot be cleared to null.
    DELETE: Remove survey.
    """
    permission_classes = [permissions.IsAuthenticated, HasAllRoles]
    required_roles_by_method = {"GET": [Roles.VIEWER.value], "PATCH": [Roles.EDITOR.value], "DELETE": [Roles.EDITOR.value]}

    def get(self, request, survey_id: int):
        survey = get_object_or_404(
            Survey.objects.prefetch_related("sections__questions__options"),
            pk=survey_id,
        )
        return Response(SurveyDetailSerializer(survey).data)

    @transaction.atomic
    def patch(self, request, survey_id: int):
        survey = get_object_or_404(Survey, pk=survey_id)
        ser = SurveyCreateSerializer(survey, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)

        # Prevent clearing organization
        if "organization_id" in request.data and request.data.get("organization_id") in (None, "", "null"):
            return Response(
                {"organization_id": ["Cannot be null."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ser.save()
        return Response({"ok": True})

    @transaction.atomic
    def delete(self, request, survey_id: int):
        survey = get_object_or_404(Survey, pk=survey_id)
        survey.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SurveyDetailByCodeView(APIView):
    """
    Public endpoint to fetch a survey by its code.
    """
    permission_classes = []  # AllowAny

    def get(self, request, survey_code: str):
        survey = get_object_or_404(
            Survey.objects.prefetch_related("sections__questions__options"),
            code=survey_code,
        )
        return Response(SurveyDetailSerializer(survey).data)


class SectionCreateView(APIView):
    """
    POST: Create a section under a specific survey.
    """
    permission_classes = [permissions.IsAuthenticated, HasAllRoles]
    required_roles = [Roles.EDITOR.value]

    @transaction.atomic
    def post(self, request, survey_id: int):
        survey = get_object_or_404(Survey, pk=survey_id)
        ser = SectionCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        section = ser.save(survey=survey)
        return Response({"id": section.id}, status=status.HTTP_201_CREATED)


class QuestionCreateView(APIView):
    """
    POST: Create a question under a section.
         - Enforces unique sort_order within the section (friendly error before DB).
         - Auto-generates a fallback code (e.g., q-<id>) when not provided.
    """
    permission_classes = [permissions.IsAuthenticated, HasAllRoles]
    required_roles = [Roles.EDITOR.value]

    @transaction.atomic
    def post(self, request, section_id: int):
        section = get_object_or_404(SurveySection, pk=section_id)
        ser = QuestionCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        new_order = ser.validated_data.get("sort_order")
        if _sort_order_conflict_exists(section, new_order):
            return Response(
                {"detail": "Sort order must be unique within the section.", "field": "sort_order"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            question = ser.save(section=section)
        except IntegrityError:
            # In case the DB uniqueness rule also fires (race)
            return Response(
                {"detail": "Sort order must be unique within the section.", "field": "sort_order"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Auto-generate code if empty, based on ID (stable & readable)
        if not question.code:
            question.code = f"q-{question.id}"
            question.save(update_fields=["code"])

        return Response({"id": question.id}, status=status.HTTP_201_CREATED)


class OptionCreateView(APIView):
    """
    POST: Create options for a question.
         - Accepts either a single option payload (OptionCreateSerializer)
           OR a bulk payload (OptionBulkCreateSerializer) with:
             {
               "replace": <bool>,      # optional; if true, wipe existing options first
               "options": [ {...}, ... ]
             }
         - Bulk create uses `bulk_create` for efficiency.
    """
    permission_classes = [permissions.IsAuthenticated, HasAllRoles]
    required_roles = [Roles.EDITOR.value]

    @transaction.atomic
    def post(self, request, question_id: int):
        question = get_object_or_404(SurveyQuestion, pk=question_id)

        # Bulk mode: { "options": [...], "replace": true|false }
        if isinstance(request.data, dict) and "options" in request.data:
            bulk_ser = OptionBulkCreateSerializer(data=request.data)
            bulk_ser.is_valid(raise_exception=True)

            opts: List[dict] = bulk_ser.validated_data["options"]
            replace = bool(bulk_ser.validated_data.get("replace"))

            if replace:
                question.options.all().delete()

            # Use bulk_create for fewer round trips
            objs = [SurveyQuestionOption(question=question, **item) for item in opts]
            created = SurveyQuestionOption.objects.bulk_create(objs)
            return Response({"created_ids": [o.id for o in created]}, status=status.HTTP_201_CREATED)

        # Single option mode
        ser = OptionCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        opt = ser.save(question=question)
        return Response({"id": opt.id}, status=status.HTTP_201_CREATED)


class QuestionUpdateView(APIView):
    """
    PATCH: Update question attributes.
          - Enforces unique sort_order inside the section (friendly error).
    """
    permission_classes = [permissions.IsAuthenticated, HasAllRoles]
    required_roles = [Roles.EDITOR.value]

    @transaction.atomic
    def patch(self, request, question_id: int):
        q = get_object_or_404(SurveyQuestion, pk=question_id)
        ser = QuestionCreateSerializer(q, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)

        new_order = ser.validated_data.get("sort_order")
        if _sort_order_conflict_exists(q.section, new_order, exclude_pk=q.pk):
            return Response(
                {"detail": "Sort order must be unique within the section.", "field": "sort_order"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            ser.save()
        except IntegrityError:
            return Response(
                {"detail": "Sort order must be unique within the section.", "field": "sort_order"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"id": q.id})


class QuestionDetailView(APIView):
    """
    GET: Return a single question with its options.
    """
    permission_classes = [permissions.IsAuthenticated, HasAllRoles]
    required_roles = [Roles.VIEWER.value]

    def get(self, request, question_id: int):
        q = get_object_or_404(
            SurveyQuestion.objects.select_related("section").prefetch_related("options"),
            pk=question_id,
        )
        return Response(QuestionReadSerializer(q).data)


class InvitationListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasAllRoles]
    required_roles = []

    def get(self, request, survey_id: int):
        survey = get_object_or_404(Survey, pk=survey_id)

        status_filter = (request.query_params.get('status') or '').strip()

        qs = (
            SurveyInvitation.objects
            .filter(survey=survey)
            .order_by('-created_at', '-id')
        )
        if status_filter in dict(InvitationStatus.choices):
            qs = qs.filter(status=status_filter)

        pager_ser = PaginationQuerySerializer(data=request.query_params)
        pager_ser.is_valid(raise_exception=False)
        page = pager_ser.validated_data.get('page', 1)
        page_size = pager_ser.validated_data.get('page_size', 10)

        paginator = Paginator(qs, page_size)
        page_obj = paginator.get_page(page)

        return Response({
            'count': paginator.count,
            'results': InvitationReadSerializer(page_obj.object_list, many=True).data,
        })

    def post(self, request, survey_id: int):
        survey = get_object_or_404(Survey, pk=survey_id)
        try:
            is_member = OrganizationMember.objects.filter(organization=survey.organization, user=request.user).exists()
            if not is_member:
                return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        except Exception:
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        if survey.status != SurveyStatus.ACTIVE:
            return Response({"detail": "Survey is not active"}, status=status.HTTP_400_BAD_REQUEST)
        ser = InvitationCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        emails = list(ser.validated_data['emails'])
        expires_at = ser.validated_data['expires_at']
        create_invitations_task.delay(survey.id, emails, expires_at.isoformat())
        return Response({ 'queued': True, 'count': len(emails) }, status=status.HTTP_202_ACCEPTED)