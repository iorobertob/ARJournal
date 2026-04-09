# CLAUDE.md — Trans/Act Journal Platform

## Project Overview
Django-based academic journal platform for artistic research. Full lifecycle: submission → peer review → editorial workflow → HTML publication with multimedia.

## Architecture
- **Backend**: Django 5.x, DRF, PostgreSQL, Celery + Redis
- **Frontend**: Django templates, custom CSS (Figma-matched), HTMX, Alpine.js
- **Dev port**: 5002 (`python manage.py runserver 0.0.0.0:5002`)
- **Settings module**: `config.settings.development`
- **Custom User model**: `apps.accounts.User` (email-based, no username field)

## Key Patterns

### Running the dev server
```bash
source venv/bin/activate
python manage.py runserver 0.0.0.0:5002
```

### Running migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Creating the superuser
Password is set in `.env` as `DJANGO_SUPERUSER_PASSWORD`.
```bash
python manage.py createsuperuser --email admin@trans-act-journal.org
```

### Running Celery (background tasks)
```bash
celery -A config.celery worker --loglevel=info
```

## App Responsibilities

| App | Responsibility |
|---|---|
| `accounts` | Custom User, UserProfile, role decorators |
| `journal` | JournalConfig (singleton), Issue, Section, editorial board |
| `submissions` | Submission lifecycle, SubmissionRevision, assets, Turnitin |
| `documents` | CanonicalDocument, LaTeX parser, HTML renderer |
| `editorial` | Screening queue, assignments, editorial decisions |
| `reviewers` | ReviewerProfile, suggestion engine (scorer.py), invitations |
| `reviews` | Review form, annotations, moderation |
| `notifications` | Celery email tasks, in-app notifications, AuditEvent |
| `production` | HTMLBuild (published articles), PDF export, Crossref DOI |
| `api` | DRF viewsets + APIViews for REST endpoints |

## Feature Flags (in .env)
- `ORCID_OAUTH_ENABLED` — ORCID login via allauth
- `DOI_ENABLED` — Crossref DOI deposit
- `TURNITIN_ENABLED` — similarity check
- `AI_FEATURES_ENABLED` — OpenAI semantic reviewer matching
- `USE_S3` — S3-compatible file storage

## Critical Files
- `apps/reviewers/scorer.py` — weighted reviewer suggestion engine
- `apps/documents/parsers/latex_parser.py` — `.tex` → canonical JSON
- `apps/documents/renderers/html_renderer.py` — canonical JSON → HTML
- `apps/production/tasks.py` — Celery: ingest, build, PDF generation
- `apps/journal/context_processors.py` — injects `journal` into all templates
- `config/settings/base.py` — all settings with django-environ

## Design System
- CSS variables in `static/css/main.css`
- Accent color: `--color-accent: #E86B1F` (orange from Figma)
- Serif font: Source Serif 4
- Sans font: Inter
- Article reading CSS: `static/css/article.css`
- Dashboard CSS: `static/css/dashboard.css`

## Template Structure
```
templates/
├── base.html               — site shell
├── partials/nav.html       — sticky header nav
├── partials/footer.html    — dark footer
├── public/                 — homepage, issue, article, archive, about, submit
├── author/                 — dashboard, 4-step submission wizard
├── editorial/              — screening queue, detail, moderation
└── reviewer/               — invitation response, workspace (split pane)
```

## API
REST API at `/api/v1/` uses JWT auth (`djangorestframework-simplejwt`).
See `apps/api/urls.py` and `design/openapi.yaml` for full endpoint list.

## Celery Beat Tasks
- `cleanup_expired_pdf_exports` — delete expired PDF files
- `send_review_reminders` — email reviewers with upcoming deadlines

## S3 Upgrade Path
Set `USE_S3=True` in `.env` + bucket credentials. `django-storages` is already installed. See README.md §Phase 2.

## Deployment
See `README.md` and `nginx/nginx.conf`. Uses Gunicorn (`config.wsgi`) behind Nginx.
Production Docker: `docker-compose up -d --build` + `collectstatic` + `migrate`.
