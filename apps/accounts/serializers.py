from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Organization, OrganizationUser

User = get_user_model()

class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "metadata", "created_at", "updated_at"]

class OrganizationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["name", "metadata"]

class OrganizationUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationUser
        fields = ["id", "organization", "user", "is_owner", "created_at", "updated_at"]

class AddUserToOrgSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    is_owner = serializers.BooleanField(required=False, default=False)
    group_names = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
