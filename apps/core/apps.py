import logging
import os
from typing import Optional, Dict

from django.apps import AppConfig
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.utils import OperationalError, ProgrammingError, IntegrityError


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

        except (OperationalError, ProgrammingError, IntegrityError):
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
        """Create the superuser if missing; return the user instance.
        Safe for concurrent startup across multiple processes/containers.
        """
        User = get_user_model()
        username, email, password = creds["username"], creds["email"], creds["password"]

        try:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": email,
                    "is_superuser": True,
                    "is_staff": True,
                },
            )
        except IntegrityError:
            # Another process created it at the same time
            logger.info("Race detected creating superuser '%s'; fetching existing", username)
            user = User.objects.get(username=username)
            created = False

        if created:
            user.set_password(password)
            user.save(update_fields=["password"])
            logger.info("Created superuser '%s'", username)
        else:
            updates = []
            if not user.is_superuser:
                user.is_superuser = True
                updates.append("is_superuser")
            if not user.is_staff:
                user.is_staff = True
                updates.append("is_staff")
            if email and user.email != email:
                user.email = email
                updates.append("email")
            if updates:
                user.save(update_fields=updates)
                logger.info("Updated superuser '%s' fields: %s", username, updates)
            else:
                logger.info("Superuser '%s' already exists; skipping", username)

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
