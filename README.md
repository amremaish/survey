# Survey Suite

A Django + DRF application for building surveys, collecting responses, and managing organizations with JWT auth, role-based access, encrypted answers, invitations, and analytics.

## Features
- JWT authentication (including org dashboard tokens)
- Role-based access control using `Roles` enum (`Viewer`, `Editor`)
- Encrypted sensitive survey answers (Fernet)
- Organization dashboard (answers and surveys) with invitations system
- Celery + Redis for async email sending and periodic tasks
- Redis-backed caching for selected endpoints
- Standardized pagination utilities
- Swagger/Redoc API docs via drf-spectacular
- Comprehensive API tests (separate SQLite test DB)

## Tech Stack
- Django 5 / Django REST Framework
- PostgreSQL (production), SQLite (tests)
- Celery + Redis
- drf-spectacular (Swagger/Redoc)

## Requirements
- Docker and Docker Compose (recommended)
- Or: Python 3.12, PostgreSQL, Redis (for local non-Docker runs)

## Quickstart (Docker)
1. Copy environment example and adjust values.
   ```bash
   cp .env-example .env
   # Edit .env (DB creds, SMTP, SITE_URL, SUPERUSER_*, etc.)
   ```

2. Build and start the stack. Migrations are applied automatically before app start.
   ```bash
   docker compose up --build
   ```

3. Services:
   - App: http://localhost:8000/
   - Swagger UI: http://localhost:8000/api/docs/
   - Redoc: http://localhost:8000/api/redoc/


## Testing
- Uses separate SQLite DB (`db_test.sqlite3`)
```bash
docker compose run --rm web python manage.py test
```

## Environment
See `.env-example` for all variables. Key settings:

- Django
  - `SECRET_KEY` (required in production)
  - `DEBUG=0/1`
  - `SITE_URL`

- Database (PostgreSQL)
  - `DB_ENGINE=django.db.backends.postgresql`
  - `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
  - Tests always use SQLite: `db_test.sqlite3`

- SMTP (Gmail example)
  - `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`

- Celery / Redis
  - `CELERY_BROKER_URL=redis://redis:6379/0`
  - `CELERY_RESULT_BACKEND=redis://redis:6379/0`
  - `CELERY_EAGER=0` (set to `1` to run tasks synchronously without Redis)

- Caching (Redis)
  - `CACHE_BACKEND=django_redis.cache.RedisCache`
  - `CACHE_LOCATION=redis://redis:6379/1`

- Bootstrap Superuser (auto-created once on startup)
  - `SUPERUSER_USERNAME`, `SUPERUSER_EMAIL`, `SUPERUSER_PASSWORD`

## Architecture Schema

<p align="center">
  <a href="screenshots/schema.png" target="_blank">
    <img src="screenshots/schema.png" alt="System schema" style="max-width: 100%; height: auto;" />
  </a>
</p>

## HTML Pages (Server-rendered)
- `/` → Home dashboard (`index.html`): Charts overview; requires JWT login.
- `/builder` → Survey builder (`builder.html`): Create/edit surveys; JWT-protected.
- `/orgs/` → Organizations (`organizations.html`): List/manage orgs; JWT-protected.
- `/surveys/` → Surveys (`surveys.html`): Manage surveys; JWT-protected.
- `/users/<org_id>` → Org users (`org_users.html`): Manage org members; JWT-protected.
- `/dashboard/login` → Org dashboard login (`org_dashboard_login.html`): Login flow for org members (separate JWT).
- `/dashboard/<org_id>` → Org dashboard (`org_dashboard.html`): Answers & surveys with invitations; org JWT required.
- `/survey/<survey_code>` → Public runner (`public_runner.html`): Public submission UI; supports `?token=` invitations.
- `/login` → Generic login (`login.html`): Obtain JWT for core pages.

## Migrations
Migrations are run automatically by the `migrate` service before `web`, `worker`, and `beat` start.

Manual runs (if needed):
```bash
docker compose run --rm web python manage.py makemigrations
docker compose run --rm web python manage.py migrate
```

## Celery & Redis
- Worker: runs async tasks (e.g., invitation emails)
- Beat: runs periodic jobs (e.g., mark expired invitations)

Compose services:
- `worker`: `celery -A survey.celery:celery_app worker --loglevel=INFO`
- `beat`: `celery -A survey.celery:celery_app beat --loglevel=INFO`

To scale workers:
```bash
docker compose up --scale worker=2 -d
```

## Caching
- Endpoint `GET /api/v1/surveys/code/<code>/detail/` is cached for 1 day
- Invalidated on `PATCH /api/v1/surveys/questions/<id>/`

## API Docs
- Swagger UI: `/api/docs/`
- Redoc: `/api/redoc/`
- Raw OpenAPI JSON: `/api/schema/`

Use the Authorize button in Swagger UI to enter a JWT access token.

## Roles & Permissions

### Roles (RBAC)
Defined in `apps/core/enums.py`:
```python
from enum import Enum

class Roles(str, Enum):
    VIEWER = "Viewer"
    EDITOR = "Editor"

    def __str__(self) -> str:
        return self.value
```

- **Viewer**: Read-only access. Typically required for `GET` on index, builder, organizations, surveys, responses.
- **Editor**: Write access. Required for write methods (`POST`, `PATCH`, `PUT`, `DELETE`) across the same areas.

On startup, roles are ensured and assigned to the bootstrap superuser in `apps.core.apps.CoreConfig.ready()`.

### Permission classes
- **HasAllRoles**: Denies access unless the user has all roles listed in `view.required_roles` or method-specific `view.required_roles_by_method`.
  - Superusers do not bypass these checks.
  - Example:
    ```python
    from rest_framework import permissions
    from apps.core.permissions import HasAllRoles
    from apps.core.enums import Roles

    class SurveyListCreateView(APIView):
        permission_classes = [permissions.IsAuthenticated, HasAllRoles]
        required_roles_by_method = {
            "GET": [Roles.VIEWER],
            "POST": [Roles.EDITOR],
        }
    ```

- **HasAllPermissions**: Denies access unless the user has all Django permissions listed in `view.required_permissions` (e.g., `"accounts.delete_organizationmember"`).
  - Evaluates the user's effective permissions; superusers do not implicitly bypass.
  - Example:
    ```python
    from rest_framework import permissions
    from apps.core.permissions import HasAllPermissions

    class MeView(APIView):
        permission_classes = [permissions.IsAuthenticated, HasAllPermissions]
        required_permissions = ["accounts.delete_organizationmember"]
    ```

- You can combine both classes on a view to require both roles and permissions.

## Auditing
- Auditing is enabled via `django-auditlog` to track creates, updates, and deletes.
- Core domain models are registered with auditlog (e.g., organizations, roles, org members, surveys, sections, questions, options, sessions, responses, invitations).
- View entries in Django Admin under “Audit log entries”. Each record includes actor, timestamp, action (create/update/delete), and a JSON diff of changed fields.

## Encryption
- Sensitive answers are encrypted using Fernet
- Key read from `RESPONSES_ENCRYPTION_SECRET`

## Development (without Docker)
```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows
pip install -r requirements.txt

# Set up a local Postgres DB and export DB_* env vars or use .env
python manage.py migrate
python manage.py runserver

# Celery (requires Redis)
celery -A survey.celery:celery_app worker --loglevel=INFO
celery -A survey.celery:celery_app beat --loglevel=INFO
```


## License
Proprietary. All rights reserved (update as appropriate).
