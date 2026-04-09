# Trans/Act — Artistic Research Journal Platform

A Django-based journal management platform supporting the full lifecycle of an artistic research academic journal: submission, peer review, editorial workflow, and HTML-first publication with multimedia support.

---

## Stack

| Component | Technology |
|---|---|
| Backend | Django 5.x + Django REST Framework |
| Database | PostgreSQL 16 |
| Task queue | Celery + Redis |
| Frontend | Django templates + custom CSS (Figma-matched design) + HTMX + Alpine.js |
| Email | django-anymail (SendGrid / Mailgun) |
| Auth | django-allauth (email/password + optional ORCID OAuth) |
| Storage | Local filesystem (documented S3 upgrade path) |
| Dev server | Port **5002** |
| Production | Nginx + Gunicorn + Docker Compose |

---

## Local Development

### Prerequisites
- Python 3.11+
- PostgreSQL 16 running locally
- Redis running locally (for Celery)

### Quick Setup (without Docker)

```bash
git clone <repo>
cd JOURNAL_CLAUDE

# One-command setup
bash scripts/setup_dev.sh

# Then start the server
source venv/bin/activate
python manage.py runserver 0.0.0.0:5002
```

Visit:
- Journal: http://localhost:5002/
- Admin: http://localhost:5002/admin/
- Author portal: http://localhost:5002/author/dashboard/
- Editorial: http://localhost:5002/editorial/

### With Docker Compose

```bash
cp .env.example .env
# Edit .env — at minimum set DJANGO_SUPERUSER_PASSWORD

docker-compose up -d
docker-compose exec app python manage.py migrate
docker-compose exec app python manage.py createsuperuser --email admin@trans-act-journal.org
docker-compose exec app python manage.py shell -c "
from apps.journal.models import JournalConfig
j = JournalConfig.get(); j.name = 'Trans/Act'; j.save()
"
```

Visit http://localhost:5002/

---

## Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key — generate with `python -c "import secrets; print(secrets.token_hex(50))"` |
| `DEBUG` | `True` for dev, `False` for production |
| `DB_*` | PostgreSQL connection details |
| `DJANGO_SUPERUSER_*` | Initial superuser credentials |
| `ANYMAIL_BACKEND` | `sendgrid` or `mailgun` or `console` |
| `SENDGRID_API_KEY` | SendGrid API key |
| `ORCID_OAUTH_ENABLED` | `True` to enable ORCID OAuth (requires client ID/secret) |
| `DOI_ENABLED` | `True` to enable Crossref DOI deposit |
| `TURNITIN_ENABLED` | `True` to enable Turnitin similarity checks |
| `AI_FEATURES_ENABLED` | `True` to enable OpenAI semantic reviewer matching |
| `USE_S3` | `True` to use S3-compatible storage (see Phase 2 below) |

---

## Journal Configuration

After setup, configure the journal name and settings at:

`http://localhost:5002/admin/journal/journalconfig/1/change/`

Key fields:
- **Name** — journal display name (default: *Trans/Act*)
- **Tagline**, **Description**, **Logo**
- **ISSN** (print and online)
- **Review Model** — double blind (default), single blind, open, editorial
- **Submission Open** — toggle to close submissions
- **About / Mission / Methodology** — editorial content pages
- **Submission Guidelines** — shown on /submit/ page

---

## Architecture Overview

```
apps/
├── accounts/       User model (email-based), roles, ORCID
├── journal/        JournalConfig (singleton), Issue, Section
├── submissions/    Submission lifecycle, revisions, assets
├── documents/      Canonical JSON doc, LaTeX parser, HTML renderer
├── editorial/      Screening, assignments, decisions
├── reviewers/      Reviewer profiles, suggestion engine (scorer.py)
├── reviews/        Review forms, anchored annotations, moderation
├── notifications/  In-app + email notifications, audit trail
├── production/     DOI deposit, HTML build, ephemeral PDF export
└── api/            REST API (DRF, JWT auth) — matches openapi.yaml
```

### Canonical Document Model

All manuscripts are parsed from `.tex` source into a **canonical JSON document** (`apps/documents/parsers/latex_parser.py`). This JSON is the source of truth for:
- HTML rendering (`apps/documents/renderers/html_renderer.py`)
- Reviewer annotations (anchored by stable block IDs)
- Role-based projections (blinded, editorial, public)
- PDF export (via pdflatex subprocess)

### Reviewer Suggestion Engine

`apps/reviewers/scorer.py` implements deterministic weighted scoring per spec §6.6:
- 12 scoring factors (expertise, discipline, keywords, methodology, etc.)
- Hard exclusion rules (same author, conflict, inactive)
- Temperature-based random selection to avoid always picking the same reviewers
- **AI path** (scaffolded, disabled): when `AI_FEATURES_ENABLED=True` and `OPENAI_API_KEY` is set, uses OpenAI embeddings for semantic abstract similarity

### External Integrations

All integrations are feature-flagged and disabled by default:

| Integration | Module | Enable |
|---|---|---|
| ORCID OAuth | `django-allauth` | `ORCID_OAUTH_ENABLED=True` + credentials |
| Crossref DOI | `apps/production/integrations/crossref.py` | `DOI_ENABLED=True` + credentials |
| Turnitin | `apps/submissions/integrations/turnitin.py` | `TURNITIN_ENABLED=True` + API key |
| OpenAI (AI) | `apps/reviewers/scorer.py` | `AI_FEATURES_ENABLED=True` + `OPENAI_API_KEY` |

---

## Production Deployment (Linux VPS)

### First Deployment

```bash
# On the server
git clone <repo> /opt/transact
cd /opt/transact
cp .env.example .env
# Edit .env: DEBUG=False, strong SECRET_KEY, ALLOWED_HOSTS=your-domain.com, DB/email config

docker-compose -f docker-compose.yml up -d --build
docker-compose exec app python manage.py migrate
docker-compose exec app python manage.py collectstatic --noinput
docker-compose exec app python manage.py createsuperuser --email admin@your-domain.com
```

### Nginx

```bash
sudo cp nginx/nginx.conf /etc/nginx/sites-available/transact
# Edit the server_name lines to match your domain
sudo ln -s /etc/nginx/sites-available/transact /etc/nginx/sites-enabled/
sudo certbot --nginx -d your-domain.com     # SSL via Let's Encrypt
sudo nginx -t && sudo systemctl reload nginx
```

### Updates

```bash
cd /opt/transact
git pull
docker-compose up -d --build
docker-compose exec app python manage.py migrate
docker-compose exec app python manage.py collectstatic --noinput
```

---

## Phase 2: S3 Storage Upgrade

When local storage is no longer sufficient (typically when video assets exceed ~50GB):

1. Create an S3-compatible bucket (AWS S3, DigitalOcean Spaces, Cloudflare R2, Backblaze B2)
2. In `.env`:
   ```
   USE_S3=True
   AWS_ACCESS_KEY_ID=your-key
   AWS_SECRET_ACCESS_KEY=your-secret
   AWS_STORAGE_BUCKET_NAME=your-bucket
   AWS_S3_ENDPOINT_URL=https://your-endpoint  # omit for AWS S3
   ```
3. Migrate existing media files to the bucket
4. Redeploy

The `django-storages` library is already installed and configured — switching `USE_S3=True` is all that's needed.

---

## Testing

```bash
source venv/bin/activate
pytest apps/
```

Key test targets:
- `apps/reviewers/tests/` — scorer algorithm, hard exclusions, temperature selection
- `apps/documents/tests/` — LaTeX parser, HTML renderer
- `apps/submissions/tests/` — submission state machine
- `apps/reviews/tests/` — annotation saving, draft autosave
