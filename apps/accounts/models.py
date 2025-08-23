from django.db import models
from apps.core.models import TimeStampedModel
from auditlog.registry import auditlog
from uuid import uuid4
import os
from django.contrib.auth.models import User, Permission

class Organization(TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)
    industry = models.CharField(max_length=255, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=64, blank=True, null=True)
    def _logo_upload_path(instance, filename):
        base, ext = os.path.splitext(filename or "")
        ext = ext or ".png"
        return f"org_logos/{uuid4().hex}{ext}"

    logo = models.ImageField(upload_to=_logo_upload_path, blank=True, null=True)

    def __str__(self):
        return self.name


class Role(TimeStampedModel):
    name = models.CharField(max_length=128, unique=True)
    description = models.TextField(blank=True, null=True)
    permissions = models.ManyToManyField(Permission, related_name="custom_roles", blank=True)
    users = models.ManyToManyField(User, related_name="custom_roles", blank=True)

    def __str__(self):
        return self.name


class OrganizationMember(TimeStampedModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="org_memberships")

    class Meta:
        unique_together = ("organization", "user")

    def __str__(self):
        return f"org#{self.organization_id}:user#{self.user_id}"


# Register models for automatic audit logging
auditlog.register(Organization)
auditlog.register(Role)
auditlog.register(OrganizationMember)
