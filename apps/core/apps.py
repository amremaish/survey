import logging
import os
from typing import Optional, Dict

from django.apps import AppConfig
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.utils import OperationalError, ProgrammingError


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"

    def ready(self):
        """Bootstrap superuser + roles when the app starts (idempotent)."""
        logger = logging.getLogger("bootstrap")

        try:
            creds = self._read_superuser_env(logger)
            if not creds:
                return

            with transaction.atomic():
                admin = self._ensure_superuser(logger, creds)
                self._ensure_roles_and_assign(logger, admin)

        except (OperationalError, ProgrammingError):
            logger.info("Database not ready; skipping superuser bootstrap")


    def _read_superuser_env(self, logger) -> Optional[Dict[str, str]]:
        """Read SUPERUSER_* env vars. Return None if incomplete."""
        username = os.getenv("SUPERUSER_USERNAME")
        email = os.getenv("SUPERUSER_EMAIL")
        password = os.getenv("SUPERUSER_PASSWORD")

        if not username or not password:
            msg = "SUPERUSER_USERNAME/PASSWORD not set; skipping superuser creation"
            print(f"[bootstrap] {msg}")
            logger.info(msg)
            return None

        return {"username": username, "email": email or "", "password": password}

    def _ensure_superuser(self, logger, creds: Dict[str, str]):
        """Create the superuser if missing; return the user instance."""
        User = get_user_model()
        username, email, password = creds["username"], creds["email"], creds["password"]

        user = User.objects.filter(username=username).first()
        if user:
            logger.info("Superuser '%s' already exists; skipping", username)
            return user

        # create explicitly as superuser/staff
        user = User.objects.create_user(username=username, email=email)
        user.is_superuser = True
        user.is_staff = True
        user.set_password(password)
        user.save(update_fields=["is_superuser", "is_staff", "password", "email"])

        logger.info("Created superuser '%s'", username)
        return user

    def _ensure_roles_and_assign(self, logger, admin_user):
        from apps.accounts.models import Role
        from apps.core.enums import Roles
        """Ensure all Roles exist and assign them to the superuser."""
        created_roles = []
        for role in Roles:
            role_obj, created = Role.objects.get_or_create(name=str(role))
            if created:
                created_roles.append(role_obj.name)
            if admin_user:
                role_obj.users.add(admin_user)

        if created_roles:
            print(f"[bootstrap] Created roles: {', '.join(created_roles)}")
            logger.info("Created roles: %s", created_roles)

        print(f"[bootstrap] Assigned roles {[r for r in Roles]} to '{admin_user.username}'")
        logger.info("Assigned all roles to '%s'", admin_user.username)
