from django.contrib import admin
from .models import Organization, OrganizationUser

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at")
    search_fields = ("name",)

@admin.register(OrganizationUser)
class OrganizationUserAdmin(admin.ModelAdmin):
    list_display = ("id", "organization", "user", "is_owner", "created_at")
    list_filter = ("is_owner", "organization")
