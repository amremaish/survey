from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Organization, OrganizationMember

class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "industry", "contact_email", "phone", "logo", "created_at", "updated_at"]

class OrganizationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["name", "industry", "contact_email", "phone", "logo"]

# Members serialization removed


class UserBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]


class OrgMemberSerializer(serializers.ModelSerializer):
    user = UserBriefSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True, required=True)

    class Meta:
        model = OrganizationMember
        fields = ["id", "organization", "user", "user_id", "created_at"]
        read_only_fields = ["id", "organization", "user", "created_at"]
