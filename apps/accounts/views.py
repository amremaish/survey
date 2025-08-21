from django.contrib.auth.models import Group
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import get_user_model

from .models import Organization, OrganizationUser
from .serializers import (
    OrganizationSerializer,
    OrganizationCreateSerializer,
    OrganizationUserSerializer,
    AddUserToOrgSerializer,
)

User = get_user_model()

class OrganizationListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = Organization.objects.all().order_by("id")
        return Response(OrganizationSerializer(qs, many=True).data)

    def post(self, request):
        serializer = OrganizationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        org = serializer.save()
        return Response(OrganizationSerializer(org).data, status=status.HTTP_201_CREATED)

class OrganizationAddUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, org_id: int):
        org = get_object_or_404(Organization, pk=org_id)
        payload = AddUserToOrgSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        user = get_object_or_404(User, pk=payload.validated_data["user_id"])
        is_owner = payload.validated_data.get("is_owner", False)
        group_names = payload.validated_data.get("group_names", [])

        link, _ = OrganizationUser.objects.get_or_create(
            organization=org, user=user, defaults={"is_owner": is_owner}
        )
        if not _:
            # existing link: allow toggling owner flag
            if link.is_owner != is_owner:
                link.is_owner = is_owner
                link.save()

        # optional: attach built-in Group(s) by name
        if group_names:
            for gname in group_names:
                grp, _ = Group.objects.get_or_create(name=gname)
                user.groups.add(grp)

        return Response(OrganizationUserSerializer(link).data, status=status.HTTP_201_CREATED)
