from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User, Group
from .models import Organization, Role

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at")
    search_fields = ("name",)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "description", "created_at")
    search_fields = ("name",)
    filter_horizontal = ("permissions", "users")


# Unregister Groups from admin
try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass


# Unregister default User admin to re-register with Roles inline
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


# Extend User admin to show Roles inline (read-write via M2M)
class RoleInline(admin.TabularInline):
    model = Role.users.through
    extra = 1


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    inlines = [RoleInline]
    # Hide Groups field by removing from fieldsets if present
    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        # Remove 'Groups' from permissions fieldset if present
        cleaned = []
        for name, opts in fieldsets:
            if name == 'Permissions':
                fields = list(opts.get('fields', ()))
                fields = [f for f in fields if f != 'groups']
                opts = {**opts, 'fields': tuple(fields)}
            cleaned.append((name, opts))
        return cleaned