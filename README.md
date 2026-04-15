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
| Staging | Nginx + Gunicorn + systemd — `misc.lmta.lt/journal` (subpath) |
| Production | Nginx + Gunicorn + systemd — `journal.lmta.lt` (bare-metal) |
| Production | Nginx + Docker Compose — `journal.lmta.lt` (containerised) |

---

## Local Development

### Prerequisites
- Python 3.11+
- PostgreSQL 16 running locally
- Redis running locally (only needed in production; dev runs tasks synchronously)
- **WeasyPrint system libraries** (for PDF generation — see below)

### WeasyPrint System Dependencies

PDF export uses [WeasyPrint](https://weasyprint.org), which requires native GLib/Pango/Cairo libraries. These are **not** Python packages — install them at the OS level before running `pip install`.

**macOS (Homebrew):**
```bash
brew install pango cairo glib libffi
```
Then add to your `.env`:
```
DYLD_LIBRARY_PATH=/opt/homebrew/lib
```
`setup_dev.sh` does both steps automatically.

**Linux (Debian/Ubuntu):**
```bash
sudo apt-get install -y libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
  libgdk-pixbuf2.0-0 libharfbuzz0b libffi-dev shared-mime-info \
  fonts-liberation fonts-dejavu-core
```
`setup_dev.sh` installs any missing packages automatically.

**Linux (production):** `scripts/deploy.sh` installs all required packages automatically.

---

### Quick Setup

```bash
git clone <repo>
cd JOURNAL_CLAUDE

# One-command setup (installs WeasyPrint system deps automatically)
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
- PDF export (via WeasyPrint — HTML→PDF, no LaTeX toolchain required)

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

## Deployment

Three deployment stages, in order of progression:

| Stage | URL | Method | Script |
|---|---|---|---|
| 1 — Staging | `https://misc.lmta.lt/journal` | Bare-metal, subpath | `scripts/deploy-staging.sh` |
| 2 — Production | `https://journal.lmta.lt` | Bare-metal, subdomain | `scripts/deploy.sh` |
| 3 — Production | `https://journal.lmta.lt` | Docker Compose | `scripts/deploy-docker.sh` |

All scripts tested on **Ubuntu 22.04 LTS** and **Debian 12**. Each script accepts `--update` to skip system package installation and run only: git pull → pip install → migrate → collectstatic → service restart.

---

### Stage 1 — Staging at `misc.lmta.lt/journal`

The app runs at a **subpath** (`/journal`) on an existing server that already hosts other things at `misc.lmta.lt`. A `staging` Django settings module handles the subpath configuration — Nginx strips the `/journal` prefix before forwarding to Gunicorn, and `FORCE_SCRIPT_NAME='/journal'` tells Django to include it in all generated URLs.

**Settings module:** `config.settings.staging`
**App directory:** `/opt/transact-staging`
**Gunicorn port:** `5003` (separate from production so both can coexist)
**Systemd units:** `transact-staging-gunicorn`, `transact-staging-celery`

**1. Set the repo URL in the script:**

```bash
# scripts/deploy-staging.sh — edit REPO_URL at the top
REPO_URL="git@github.com:your-org/journal.git"
```

**2. Run on the server:**

```bash
ssh root@misc.lmta.lt
git clone https://github.com/iorobertob/ARJournal.git ARJournal
cd ARJournal
sudo bash scripts/deploy-staging.sh
```

The script prompts you to edit `.env` before continuing. Required staging `.env` values:

```bash
DEBUG=False
SECRET_KEY=<50+ random chars>
DJANGO_SETTINGS_MODULE=config.settings.staging
ALLOWED_HOSTS=misc.lmta.lt
CSRF_TRUSTED_ORIGINS=https://misc.lmta.lt
SITE_URL=https://misc.lmta.lt/ARJournal

DB_NAME=transact_staging
DB_USER=transact
DB_PASSWORD=<password>
DB_HOST=localhost

CELERY_BROKER_URL=redis://localhost:6379/1   # db=1, separate from production
CELERY_TASK_ALWAYS_EAGER=False

ANYMAIL_BACKEND=console   # or real backend for email testing
DJANGO_SUPERUSER_EMAIL=admin@lmta.lt
DJANGO_SUPERUSER_PASSWORD=<password>
```

**3. Add Nginx location blocks** to the existing `misc.lmta.lt` server block:

```bash
sudo nano /etc/nginx/sites-available/misc.lmta.lt
# Paste the contents of nginx/nginx-staging.conf inside the server { } block
sudo nginx -t && sudo systemctl reload nginx
```

`nginx/nginx-staging.conf` contains the three location blocks (`/journal/static/`, `/journal/media/`, `/journal/`) with comments explaining how the proxy stripping works.

**Update:**
```bash
cd /opt/transact-staging && git pull
sudo bash scripts/deploy-staging.sh --update
```

**Logs:**
```bash
sudo journalctl -u transact-staging-gunicorn -f
tail -f /opt/transact-staging/logs/gunicorn-error.log
```

---

### Stage 2 — Production at `journal.lmta.lt` (bare-metal)

Full subdomain deployment, no Docker. The script installs all system packages, creates a dedicated `transact` system user, sets up the venv, writes systemd units, deploys Nginx, and obtains SSL via Let's Encrypt.

**Settings module:** `config.settings.production`
**App directory:** `/opt/transact`
**Gunicorn port:** `5002`
**Systemd units:** `transact-gunicorn`, `transact-celery`, `transact-celerybeat`
**Nginx config:** `nginx/nginx-production.conf`

**1. Edit the script configuration:**

```bash
# scripts/deploy.sh — edit at the top
REPO_URL="git@github.com:your-org/journal.git"
DOMAIN="journal.lmta.lt"
GUNICORN_WORKERS=3    # 2 × CPU cores + 1
```

**2. Run on the server:**

```bash
ssh root@journal.lmta.lt
git clone <repo> /opt/transact
cd /opt/transact
sudo bash scripts/deploy.sh
```

The script installs:
- Python 3.11, PostgreSQL 16, Redis, Nginx, Certbot
- WeasyPrint native libs: `libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libharfbuzz0b libffi-dev shared-mime-info fonts-liberation fonts-dejavu-core`
- `libmagic1` (python-magic file type detection)
- All Python packages from `requirements/production.txt`, including **pikepdf** (binary wheel, no extra build deps on Ubuntu 22.04+)

Required production `.env` values:

```bash
DEBUG=False
SECRET_KEY=<50+ random chars>
DJANGO_SETTINGS_MODULE=config.settings.production
ALLOWED_HOSTS=journal.lmta.lt,www.journal.lmta.lt
CSRF_TRUSTED_ORIGINS=https://journal.lmta.lt,https://www.journal.lmta.lt
SITE_URL=https://journal.lmta.lt

DB_NAME=transact_journal
DB_USER=transact
DB_PASSWORD=<strong password>
DB_HOST=localhost

CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_TASK_ALWAYS_EAGER=False

ANYMAIL_BACKEND=mailersend
MAILERSEND_API_TOKEN=<token>
DEFAULT_FROM_EMAIL=noreply@journal.lmta.lt

DJANGO_SUPERUSER_EMAIL=admin@lmta.lt
DJANGO_SUPERUSER_PASSWORD=<strong password>
```

**Update:**
```bash
cd /opt/transact && git pull
sudo bash scripts/deploy.sh --update
```

**Service management:**
```bash
sudo systemctl status transact-gunicorn
sudo systemctl restart transact-gunicorn
sudo journalctl -u transact-gunicorn -f
tail -f /opt/transact/logs/gunicorn-error.log
tail -f /opt/transact/logs/celery.log
```

**SSL renewal** (Certbot auto-renews via systemd timer, but to renew manually):
```bash
sudo certbot renew --dry-run
sudo certbot renew && sudo systemctl reload nginx
```

---

### Stage 3 — Production at `journal.lmta.lt` (Docker)

PostgreSQL, Redis, Gunicorn, and Celery run inside Docker containers. Nginx and Certbot run on the host and proxy to the Docker app container on port 5002. Media files are bind-mounted from the container to `/opt/transact-docker/media/` so Nginx can serve them directly. Static files are served by WhiteNoise from inside the app container.

**Docker Compose file:** `docker-compose.prod.yml`
**Nginx config:** `nginx/nginx-docker.conf`
**Script:** `scripts/deploy-docker.sh`

**1. Clone the repo and run the script:**

```bash
ssh root@journal.lmta.lt
git clone <repo> /opt/transact-docker
cd /opt/transact-docker
sudo bash scripts/deploy-docker.sh
```

The script installs Docker CE (official repo), Nginx, and Certbot on the host. It then builds the images, runs containers, runs migrations inside the app container, obtains SSL, and starts Nginx.

Required `.env` values — **note `DB_HOST=db`** (Docker service name, not localhost):

```bash
DEBUG=False
SECRET_KEY=<50+ random chars>
DJANGO_SETTINGS_MODULE=config.settings.production
ALLOWED_HOSTS=journal.lmta.lt,www.journal.lmta.lt
CSRF_TRUSTED_ORIGINS=https://journal.lmta.lt,https://www.journal.lmta.lt
SITE_URL=https://journal.lmta.lt

DB_NAME=transact_journal
DB_USER=transact
DB_PASSWORD=<strong password>
DB_HOST=db                          # ← Docker service name, NOT localhost
DB_PORT=5432

CELERY_BROKER_URL=redis://redis:6379/0   # ← 'redis' = Docker service name
CELERY_TASK_ALWAYS_EAGER=False

ANYMAIL_BACKEND=mailersend
MAILERSEND_API_TOKEN=<token>
DEFAULT_FROM_EMAIL=noreply@journal.lmta.lt

DJANGO_SUPERUSER_EMAIL=admin@lmta.lt
DJANGO_SUPERUSER_PASSWORD=<strong password>
```

**Update:**
```bash
cd /opt/transact-docker && git pull
sudo bash scripts/deploy-docker.sh --update
```

**Docker management:**
```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f app
docker compose -f docker-compose.prod.yml logs -f celery
docker compose -f docker-compose.prod.yml restart app

# Run a management command inside the container
docker compose -f docker-compose.prod.yml exec app python manage.py <command>
```

---

### Celery and PDF generation (all stages)

The Celery worker handles **interactive PDF generation** (WeasyPrint + pikepdf media embedding). Without a running worker, interactive PDFs will queue but never complete.

- **Flat PDFs** run synchronously in the request — no Celery needed.
- **Interactive PDFs** are dispatched to Celery; the user sees a polling spinner page.

To skip Celery entirely (simpler setup, all PDFs synchronous and slower), set `CELERY_TASK_ALWAYS_EAGER=True` in `.env` and disable/don't start the Celery service.

### pikepdf note

pikepdf ships as a binary wheel from PyPI (`pikepdf>=9.0,<11`) — no compilation needed on Ubuntu 22.04+. If installation fails on older distros or ARM:

```bash
sudo apt-get install libqpdf-dev
pip install pikepdf --no-binary pikepdf
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
