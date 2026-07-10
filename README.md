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
| Production | Nginx + Gunicorn + systemd — `inact.lmta.lt` (bare-metal, `/var/www/inact`) |

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

## First Admin User — Granting Roles

After the superuser account is created (via `createsuperuser` or the deploy script), that user still has **no journal roles**. Two separate permission layers exist:

| Layer | What it unlocks | How to set |
|---|---|---|
| `is_superuser` + `is_staff` | Django admin at `/admin/` | Shell or Django admin |
| `roles` field | Journal admin at `/journal-admin/` and editorial tools | Shell (first time), then UI |

**The first admin must be bootstrapped from the shell** — a one-time step. After that, all role management can be done through the UI.

```bash
source venv/bin/activate
# For staging add:  DJANGO_SETTINGS_MODULE=config.settings.staging
python manage.py shell -c "
from apps.accounts.models import User, UserRole
u = User.objects.get(email='your-admin@email.here')
u.is_staff = True
u.is_superuser = True
u.roles = [UserRole.SYSTEM_ADMIN, UserRole.JOURNAL_ADMIN]
u.save()
print('Done — roles:', u.roles)
"
```

Once logged in with those roles, manage all other users at:

```
/journal-admin/users/
```

Available roles:

| Role value | Label | Access |
|---|---|---|
| `system_admin` | System Administrator | Everything |
| `journal_admin` | Journal Administrator | `/journal-admin/` settings and user management |
| `editor_in_chief` | Editor-in-Chief | Full editorial workflow |
| `managing_editor` | Managing Editor | Editorial workflow |
| `handling_editor` | Handling Editor | Assigned submissions |
| `editorial_assistant` | Editorial Assistant | Screening queue |
| `production_editor` | Production Editor | HTML build and publication |
| `copyeditor` | Copyeditor | Production tasks |
| `reviewer` | Reviewer | Review workspace |

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

Two deployment stages, in order of progression:

| Stage | URL | Method | Script |
|---|---|---|---|
| 1 — Staging | `https://misc.lmta.lt/journal` | Bare-metal, subpath | `scripts/deploy-staging.sh` |
| 2 — Production | `https://inact.lmta.lt` | Bare-metal, subdomain (`/var/www/inact`) | `scripts/deploy.sh` |

Both scripts tested on **Ubuntu 22.04 LTS** and **Debian 12**. Each script accepts `--update` to skip system package installation and run only: git pull → pip install → migrate → collectstatic → service restart.

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

### Stage 2 — Production at `inact.lmta.lt` (bare-metal)

Full subdomain deployment, no Docker. `scripts/deploy.sh` is **fully self-contained** — a first run does everything end-to-end with no manual steps beyond editing `.env`:

> apt packages → dedicated `inact` system user → `.env` → venv + pip install → git pull → **PostgreSQL role + database (with schema ownership)** → media/static/log dirs → `collectstatic` → `migrate` → `check --deploy` → systemd units → Nginx site → Let's Encrypt SSL → start services → **Django superuser + admin roles** → JournalConfig seed.

**Settings module:** `config.settings.production`
**App directory:** `/var/www/inact`
**Gunicorn port:** `5002` (bound to `127.0.0.1`; Nginx proxies to it)
**Systemd units:** `inact-gunicorn`, `inact-celery`, `inact-celerybeat`
**Nginx site:** `nginx/nginx-production.conf` → `/etc/nginx/sites-available/inact`

**1. Clone and run — no script editing required.** `deploy.sh` reads everything from `.env` and derives its app directory from its own location. Optionally set `GUNICORN_WORKERS` (default 3 ≈ 2 × CPU cores + 1) as an env var:

```bash
ssh root@inact.lmta.lt
git clone <repo> /var/www/inact
cd /var/www/inact
sudo bash scripts/deploy.sh                 # or: GUNICORN_WORKERS=5 sudo bash scripts/deploy.sh
```

On first run the script copies `.env.example` to `.env` and pauses so you can fill it in (it prints a ready-to-paste template with a freshly generated `SECRET_KEY`).

The script installs:
- Python ≥ 3.11 (the distro default: 3.12 on Ubuntu 24.04, 3.11 on Debian 12; on Ubuntu 22.04 it pulls python3.11), PostgreSQL 16, Redis, Nginx, Certbot
- WeasyPrint native libs: `libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libharfbuzz0b libffi-dev shared-mime-info fonts-liberation fonts-dejavu-core`
- `libmagic1` (python-magic file type detection)
- All Python packages from `requirements/production.txt`, including **pikepdf** (binary wheel, no extra build deps on Ubuntu 22.04+)

Required production `.env` values:

```bash
DEBUG=False
SECRET_KEY=<50+ random chars>            # python -c "import secrets; print(secrets.token_hex(50))"
DJANGO_SETTINGS_MODULE=config.settings.production
ALLOWED_HOSTS=inact.lmta.lt,www.inact.lmta.lt
CSRF_TRUSTED_ORIGINS=https://inact.lmta.lt,https://www.inact.lmta.lt
SITE_URL=https://inact.lmta.lt

# PostgreSQL — deploy.sh creates this role + database automatically
DB_NAME=inact_journal
DB_USER=inact
DB_PASSWORD=<strong password>            # openssl rand -base64 24
DB_HOST=localhost

CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_TASK_ALWAYS_EAGER=False

ANYMAIL_BACKEND=mailersend
MAILERSEND_API_TOKEN=<token>
DEFAULT_FROM_EMAIL=noreply@inact.lmta.lt

# Django superuser — deploy.sh creates this login automatically
DJANGO_SUPERUSER_EMAIL=admin@inact.lmta.lt
DJANGO_SUPERUSER_PASSWORD=<strong password>   # openssl rand -base64 24
```

> **DNS first.** Point `inact.lmta.lt` (and `www.inact.lmta.lt` if you list it in `ALLOWED_HOSTS`) at the server's IP **before** running the script — Certbot requests a cert for every host in `ALLOWED_HOSTS` and fails if any of them doesn't resolve.

#### Database and superuser (created automatically)

`deploy.sh` provisions both from your `.env` — you do **not** create them by hand:

| What | Created from `.env` | Details |
|---|---|---|
| PostgreSQL role | `DB_USER` / `DB_PASSWORD` | `LOGIN` role; re-run syncs the password. UTF-8 / read-committed / UTC session defaults applied. |
| PostgreSQL database | `DB_NAME` | Owned by `DB_USER`. On PG 15/16 the `public` schema is re-owned by `DB_USER` so migrations can create tables. |
| Django superuser | `DJANGO_SUPERUSER_EMAIL` / `DJANGO_SUPERUSER_PASSWORD` | `is_staff` + `is_superuser`, and granted the `system_admin` + `journal_admin` journal roles — usable at `/admin/` **and** `/journal-admin/` immediately. Existing users are never password-reset. |

The DB password lives only in `.env` (mode `640`, git-ignored). To rotate it, change `DB_PASSWORD` in `.env` and re-run `sudo bash scripts/deploy.sh --update`. To reset the superuser password: `sudo -u inact venv/bin/python manage.py changepassword <email>`. Additional users are managed through the UI at `/journal-admin/users/` (see [First Admin User](#first-admin-user--granting-roles)).

**Update (subsequent deploys — skips packages, DB creation, SSL):**
```bash
cd /var/www/inact && git pull
sudo bash scripts/deploy.sh --update
```

**Service management:**
```bash
sudo systemctl status inact-gunicorn
sudo systemctl restart inact-gunicorn inact-celery inact-celerybeat
sudo journalctl -u inact-gunicorn -f
tail -f /var/www/inact/logs/gunicorn-error.log
tail -f /var/www/inact/logs/celery.log
```

**SSL renewal** (Certbot auto-renews via systemd timer, but to renew manually):
```bash
sudo certbot renew --dry-run
sudo certbot renew && sudo systemctl reload nginx
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

## Troubleshooting

### PostgreSQL "remaining connection slots are reserved for superuser"

**Symptom**: `OperationalError: connection to server at "localhost" … FATAL: remaining connection slots are reserved for roles with the SUPERUSER attribute`

**Cause**: PostgreSQL's default `max_connections` is 100. In development, idle connections from Django accumulate over time — the threaded dev server opens one connection per concurrent request, and autoreloader restarts leave orphaned connections that the OS may not close for hours.

**Immediate fix** — kill all idle connections:

```bash
psql postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND pid <> pg_backend_pid();"
```

Or restart PostgreSQL entirely:

```bash
brew services restart postgresql@16   # adjust version as needed
```

**Permanent fix** — raise the connection limit. Find `postgresql.conf`:

```bash
psql postgres -c "SHOW config_file;"
```

Edit the file and increase:

```
max_connections = 200
```

Then restart PostgreSQL. This is safe on a dev machine. In production, use PgBouncer as a connection pooler instead of raising this limit.

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
