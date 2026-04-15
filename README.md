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
| Production | Nginx + Gunicorn + systemd (bare-metal Linux) |

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

## Production Deployment (Linux VPS — bare metal)

Tested on **Ubuntu 22.04 LTS** and **Debian 12**. No Docker required.

### Prerequisites on the server

- A clean Ubuntu/Debian VPS with SSH root access
- A domain pointing at the server's IP (DNS must propagate before running certbot)
- The repository accessible (GitHub, GitLab, or SFTP)

### First deployment

**1. Edit the deploy script configuration**

Open `scripts/deploy.sh` and set the variables at the top:

```bash
REPO_URL="git@github.com:your-org/journal.git"   # or https://
DOMAIN="trans-act-journal.org"
GUNICORN_WORKERS=3    # 2 × CPU cores + 1
```

**2. Copy the repository to the server and run the script**

```bash
# From your local machine — push the repo to the server, then:
ssh root@your-server
cd /opt/transact
sudo bash scripts/deploy.sh
```

The script will:
- Install Python 3.11, PostgreSQL, Redis, Nginx, Certbot
- Install all **WeasyPrint** native libraries (libcairo2, libpango, libgdk-pixbuf2.0, libharfbuzz0b, libffi-dev, shared-mime-info, fonts-liberation, fonts-dejavu-core)
- Install **libmagic1** (required by python-magic for file type detection)
- Install all Python packages from `requirements/production.txt` (including **pikepdf** via binary wheel — no extra build deps needed on Ubuntu 22.04+)
- Create the `transact` system user and `/opt/transact` directory
- Prompt you to edit `.env` with production values before continuing
- Run `migrate` and `collectstatic`
- Write systemd unit files for Gunicorn, Celery worker, and Celery Beat
- Deploy Nginx config and obtain SSL certificate via Let's Encrypt
- Start and enable all services

**3. Required `.env` values for production**

```bash
DEBUG=False
SECRET_KEY=<generate: python -c "import secrets; print(secrets.token_hex(50))">
ALLOWED_HOSTS=trans-act-journal.org,www.trans-act-journal.org
DJANGO_SETTINGS_MODULE=config.settings.production

# Database (PostgreSQL on localhost)
DB_NAME=transact_journal
DB_USER=transact
DB_PASSWORD=<strong password>
DB_HOST=localhost
DB_PORT=5432

# Celery / Redis
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_TASK_ALWAYS_EAGER=False

# Email (MailerSend, SendGrid, Mailgun, or console)
ANYMAIL_BACKEND=mailersend
MAILERSEND_API_TOKEN=<token>
DEFAULT_FROM_EMAIL=noreply@trans-act-journal.org

# Django admin superuser (created on first deploy)
DJANGO_SUPERUSER_EMAIL=admin@trans-act-journal.org
DJANGO_SUPERUSER_PASSWORD=<strong password>
```

### Updating an existing deployment

```bash
ssh root@your-server
cd /opt/transact
git pull
sudo bash scripts/deploy.sh --update
```

`--update` skips system package installation, user creation, and SSL steps — it only: pulls code, reinstalls Python deps, runs migrations, collects static files, and restarts services.

### Service management

```bash
# Status
sudo systemctl status transact-gunicorn
sudo systemctl status transact-celery
sudo systemctl status transact-celerybeat

# Restart
sudo systemctl restart transact-gunicorn
sudo systemctl restart transact-celery

# Live logs
sudo journalctl -u transact-gunicorn -f
sudo journalctl -u transact-celery -f

# Application log files
tail -f /opt/transact/logs/gunicorn-error.log
tail -f /opt/transact/logs/celery.log
```

### Nginx and SSL

The deploy script installs `nginx/nginx.conf` and runs certbot automatically. To renew SSL manually:

```bash
sudo certbot renew --dry-run     # test renewal
sudo certbot renew               # renew
sudo systemctl reload nginx
```

Certbot installs a cron job / systemd timer that auto-renews certificates — no manual action needed after the first run.

### Celery and async PDF generation

The Celery worker handles **interactive PDF generation** (WeasyPrint + pikepdf media embedding). It connects to Redis on `localhost:6379`.

- Flat PDFs (plain print layout) run synchronously in the request — no Celery needed.
- Interactive PDFs (bookmarks + embedded media annotations) are dispatched to Celery and the user sees a polling spinner page.

If you do not need interactive PDFs, you can disable the Celery services and set `CELERY_TASK_ALWAYS_EAGER=True` in `.env` — all PDF generation will run synchronously in the web process (slower but simpler).

### pikepdf note

pikepdf is installed as a binary wheel from PyPI (`pikepdf>=9.0,<11`) — no compilation needed on Ubuntu 22.04+. If installation fails on an older distro or ARM:

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
