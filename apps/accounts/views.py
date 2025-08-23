from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from apps.core.permissions import HasAllRoles
from apps.core.enums import Roles
from django.contrib.auth.models import User
from django.db.models import Q
from apps.core.utility import parse_int as _parse_int, page_bounds as _page_bounds
from django.core.paginator import Paginator
from apps.core.serializer import PaginationQuerySerializer
from .models import Organization, OrganizationMember
from .serializers import (
    OrganizationSerializer,
    OrganizationCreateSerializer,
    OrgMemberSerializer,
)

class OrganizationListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasAllRoles]
    required_roles_by_method = {"GET": [Roles.VIEWER.value], "POST": [Roles.EDITOR.value]}

    def get(self, request):
        qs = Organization.objects.all().order_by("id")
        search = (request.query_params.get("search") or "").strip()
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(industry__icontains=search)
                | Q(contact_email__icontains=search)
                | Q(phone__icontains=search)
            )

        pager_ser = PaginationQuerySerializer(data=request.query_params)
        pager_ser.is_valid(raise_exception=False)
        page = pager_ser.validated_data.get("page", 1)
        page_size = pager_ser.validated_data.get("page_size", 10)

        paginator = Paginator(qs, page_size)
        page_obj = paginator.get_page(page)
        data = OrganizationSerializer(page_obj.object_list, many=True).data
        return Response({"count": paginator.count, "results": data})

    def post(self, request):
        serializer = OrganizationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        org = serializer.save()
        return Response(OrganizationSerializer(org).data, status=status.HTTP_201_CREATED)

class OrganizationDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasAllRoles]
    required_roles_by_method = {"GET": [Roles.VIEWER.value], "PATCH": [Roles.EDITOR.value], "DELETE": [Roles.EDITOR.value]}

    def get(self, request, org_id: int):
        org = get_object_or_404(Organization, pk=org_id)
        return Response(OrganizationSerializer(org).data)

    def patch(self, request, org_id: int):
        org = get_object_or_404(Organization, pk=org_id)
        # Allow partial updates of non-unique fields without requiring name change
        serializer = OrganizationCreateSerializer(org, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        org = serializer.save()
        return Response(OrganizationSerializer(org).data)

    def delete(self, request, org_id: int):
        org = get_object_or_404(Organization, pk=org_id)
        org.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class OrgMembersView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasAllRoles]
    required_roles = [Roles.VIEWER.value]

    def get(self, request, org_id: int):
        org = get_object_or_404(Organization, pk=org_id)
        qs = OrganizationMember.objects.filter(organization=org).select_related("user").order_by("id")

        search = (request.query_params.get("search") or "").strip()
        if search:
            qs = qs.filter(Q(user__username__icontains=search) | Q(user__email__icontains=search))

        page = _parse_int(request.query_params.get("page", 1), 1)
        page_size = _parse_int(request.query_params.get("page_size", 10), 10)
        start, end = _page_bounds(page, page_size)

        count = qs.count()
        items = qs[start:end]
        data = OrgMemberSerializer(items, many=True).data
        return Response({"count": count, "results": data})

    def post(self, request, org_id: int):
        org = get_object_or_404(Organization, pk=org_id)
        # create user if username/email/password provided; else expect user_id
        user_id = request.data.get("user_id")
        username = (request.data.get("username") or "").strip()
        email = (request.data.get("email") or "").strip()
        password = request.data.get("password")
        if user_id:
            user = get_object_or_404(User, pk=int(user_id))
        else:
            if not username or not password:
                return Response({"detail": "username and password are required"}, status=status.HTTP_400_BAD_REQUEST)
            if User.objects.filter(username=username).exists():
                return Response({"detail": "username already exists"}, status=status.HTTP_400_BAD_REQUEST)
            user = User.objects.create_user(username=username, email=email or None, password=password)
        # link
        OrganizationMember.objects.get_or_create(organization=org, user=user)
        members = OrganizationMember.objects.filter(organization=org).select_related("user").order_by("id")
        return Response(OrgMemberSerializer(members, many=True).data, status=status.HTTP_201_CREATED)

class OrgMemberDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasAllRoles]
    required_roles = [Roles.EDITOR.value]

    def delete(self, request, org_id: int, member_id: int):
        org = get_object_or_404(Organization, pk=org_id)
        m = get_object_or_404(OrganizationMember, pk=member_id, organization=org)
        m.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyOrganizationsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        org_ids = (
            OrganizationMember.objects
            .filter(user=request.user)
            .values_list("organization_id", flat=True)
        )
        qs = Organization.objects.filter(id__in=list(org_ids)).order_by("id")
        data = OrganizationSerializer(qs, many=True).data
        return Response({"count": len(data), "results": data})


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        u = request.user
        try:
            roles = list(getattr(u, 'custom_roles', None).values_list('name', flat=True)) if hasattr(u, 'custom_roles') else []
        except Exception:
            roles = []
        return Response({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "roles": roles,
        })
