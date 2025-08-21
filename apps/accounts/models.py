from django.db import models
from django.contrib.auth import get_user_model
from apps.core.models import TimeStampedModel

User = get_user_model()

class Organization(TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)
    metadata = models.JSONField(default=dict)

    def __str__(self):
        return self.name

class OrganizationUser(TimeStampedModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="org_users"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_orgs"
    )
    is_owner = models.BooleanField(default=False)

    class Meta:
        unique_together = ("organization", "user")

    def __str__(self):
        return f"{self.user_id} @ {self.organization_id}"
