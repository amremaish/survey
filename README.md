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

## Project Structure
```text
survey/
  apps/
    accounts/          # Organizations, roles, org members, auth-related APIs
    analytics/         # Analytics APIs powering charts on the home page
    core/              # HTML pages, enums, permissions, utilities
    responses/         # Survey responses and answers APIs/services
    survey_sessions/   # Session start/autosave/complete APIs
    surveys/           # Surveys, sections, questions, options, invitations
    system/            # System-level models (admin/supporting)
  media/               # Uploaded files (e.g., organization logos)
  templates/           # Global templates (if any)
  survey/              # Django project (settings, urls, celery app)
  manage.py
  requirements.txt
  Dockerfile
  docker-compose.yml
  .dockerignore
  .github/workflows/tests.yml
  .env-example
```

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

## API (v1)

Base prefix: `api/v1/`

### Accounts
- `GET /api/v1/orgs/` — List organizations (Viewer)
- `POST /api/v1/orgs/` — Create organization (Editor)
- `GET /api/v1/orgs/<org_id>/` — Retrieve organization (Viewer)
- `PATCH /api/v1/orgs/<org_id>/` — Update organization (Editor)
- `DELETE /api/v1/orgs/<org_id>/` — Delete organization (Editor)
- `GET /api/v1/orgs/<org_id>/members/` — List organization members (Viewer)
- `POST /api/v1/orgs/<org_id>/members/` — Add organization member (Editor)
- `DELETE /api/v1/orgs/<org_id>/members/<member_id>/` — Remove organization member (Editor)
- `GET /api/v1/my-orgs/` — Organizations for the authenticated user (Viewer)
- `GET /api/v1/me/` — Current user info and assigned roles (auth required)

### Surveys
- `GET /api/v1/surveys/` — List surveys with pagination (Viewer)
- `POST /api/v1/surveys/` — Create survey (Editor)
- `GET /api/v1/surveys/<survey_id>/detail/` — Survey detail (Viewer)
- `GET /api/v1/surveys/code/<survey_code>/detail/` — Survey detail by code, Redis-cached 1 day (Viewer)
- `POST /api/v1/surveys/<survey_id>/sections/` — Create section (Editor)
- `POST /api/v1/surveys/sections/<section_id>/questions/` — Create question (Editor)
- `PATCH /api/v1/surveys/questions/<question_id>/` — Update question (Editor; invalidates cache)
- `GET /api/v1/surveys/questions/<question_id>/detail/` — Question detail (Viewer)
- `POST /api/v1/surveys/questions/<question_id>/options/` — Create option (Editor)
- `GET /api/v1/surveys/<survey_id>/invitations/?status=&page=&page_size=` — List invitations with filter + pagination (Viewer)
- `POST /api/v1/surveys/<survey_id>/invitations/` — Queue invitations email task (Editor; survey must be ACTIVE)

### Survey Sessions
- `POST /api/v1/sessions/sessions/start/` — Start a survey session
- `GET /api/v1/sessions/sessions/<session_id>/` — Session detail
- `POST /api/v1/sessions/sessions/<session_id>/autosave/` — Autosave responses for a session
- `POST /api/v1/sessions/sessions/<session_id>/complete/` — Complete session

### Responses
- `POST /api/v1/responses/submit/` — Submit a survey response; validates invitation token, expiry, one-time submission
- `GET /api/v1/responses/<response_id>/` — Response detail (Viewer, org-scoped)
- `GET /api/v1/responses/org/<org_id>/dashboard/?page=&page_size=` — Org responses dashboard (Viewer, paginated)

### Analytics
- `GET /api/v1/analytics/overall-submissions/` — Time series of submissions
- `GET /api/v1/analytics/submissions-by-organization/` — Totals by organization
- `GET /api/v1/analytics/invitation-status/` — Pending/Submited/Expired distribution
- `GET /api/v1/analytics/responses-by-survey-status/` — Responses grouped by survey status

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
## Continuous Integration (CI)
- GitHub Actions workflow at `.github/workflows/tests.yml` runs on every push and pull request.
- Uses Python 3.12 (alpine container) and forces a lightweight test environment:
  - `DB_ENGINE=django.db.backends.sqlite3`
  - `DB_NAME` points to a workspace-local SQLite file
  - `CACHE_BACKEND=django.core.cache.backends.locmem.LocMemCache`
  - `CELERY_EAGER=1` (run Celery tasks synchronously)
  - `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend`
- Steps: install deps, run `python manage.py migrate --noinput`, then `python manage.py test -v 2`.
- View results in the Actions tab; logs include full test output.

## License
Proprietary. All rights reserved (update as appropriate).
