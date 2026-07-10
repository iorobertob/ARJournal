# CLAUDE.md — Trans/Act Journal Platform

## Project Overview
Django-based academic journal platform for artistic research. Full lifecycle: submission → peer review → editorial workflow → HTML publication with multimedia.

## Architecture
- **Backend**: Django 5.x, DRF, PostgreSQL, Celery (no Redis in dev)
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

### Celery / Redis
**Dev**: No Redis or Celery worker needed. `CELERY_TASK_ALWAYS_EAGER=True` is set in `config/settings/development.py`. **Important:** `task_always_eager` was removed in Celery 5 — calling `.delay()` still tries to reach a real broker. All task dispatch goes through `_dispatch_task()` in `apps/production/views.py`, which calls `task.apply()` (synchronous, no broker) when `CELERY_TASK_ALWAYS_EAGER=True`, and `.delay()` otherwise.

**Production**: Redis is only needed if you want async PDF generation (WeasyPrint typically takes 2–10s per article). All other tasks remain synchronous. Run a worker only if PDF export is used:
```bash
celery -A config.celery worker --loglevel=info
```

### PDF Generation (WeasyPrint)
PDFs are rendered from the stored `HTMLBuild.html_content` via WeasyPrint — no LaTeX toolchain required.

**WeasyPrint needs OS-level libraries** (GLib, Pango, Cairo). These are not pip packages:

- **macOS**: `brew install pango cairo glib libffi` — then set `DYLD_LIBRARY_PATH=/opt/homebrew/lib` in `.env`. `setup_dev.sh` handles both steps automatically.
- **Linux**: `apt-get install libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libharfbuzz0b libffi-dev shared-mime-info fonts-liberation`

Two PDF modes: **flat** (plain print layout) and **interactive** (adds PDF bookmarks from headings). Both use a self-contained HTML document with inlined CSS — no external resources fetched at render time.

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

## Design System — inAct identity (Figma "TRANS/ACT", 2026)
- CSS variables in `static/css/main.css`; @font-face in `static/css/fonts.css`
- Palette: Orange `#FF4500` (accent), Shadow `#21252B` (text), White `#FBFAFC` (bg),
  Ghost `#F4F2F7`, Silver `#E4E2E7` (borders), Ash `#6E667A`, lavender `#A9A1B4` (captions),
  Clay `#764D40` + Amber `#FFBD6D` (alt button / footer labels)
- Single typeface identity: **FK Grotesk Neue** (commercial, not bundled). Interim:
  **Space Grotesk** (bundled, `static/fonts/space-grotesk/`). Drop purchased FK Grotesk
  Neue woff2 files into `static/fonts/fk-grotesk-neue/` (see README.txt there) — they
  activate automatically via @font-face, no code changes.
- Logotype: dotted inAct SVGs in `static/img/brand/` (header/footer/orange/white).
  Logotype typeface **G.B. Jones** by Nat Pyper (free: librarystack.org/g-b-jones) goes
  into `static/fonts/gb-jones/` if ever needed as a text font.
- Type scale (Desktop-18): H1 36/40 · H2 28/34 · H3 22/28 · body 16/20 ·
  directional links 12/16 (orange, trailing ⟶, class `dir-link`/`link-arrow`) ·
  filter tags 10/14 (white-on-orange, radius 2, class `filter-tag`)
- Buttons: radius 2; `.btn--primary` solid orange, `.btn--outline`/`.btn--secondary`
  outlined orange, `.btn--inverse` white outline for orange surfaces, `.btn--clay`
  Clay/Amber variant
- Section headings on public pages are orange (`.section-heading`)
- Article reading CSS: `static/css/article.css`
- Dashboard CSS: `static/css/dashboard.css`
- Figma reference exports: `design/figma_reference/`

### Spacing tokens — valid values only
The scale is **1, 2, 3, 4, 6, 8, 10, 12, 16, 20, 24** — there is no `--spacing-5`, `--spacing-7`, `--spacing-9`, etc. Using an undefined token resolves to nothing and collapses the dimension to zero. Always use a token from this list.

### UI element formatting rule
Every new UI element — cards, info boxes, warning panels, form groups, confirmation dialogs — **must have sufficient internal padding so that no text or content touches its border**. Use at minimum `padding: var(--spacing-4) var(--spacing-6)` for bordered containers. Never use `padding: 0` on a bordered element. Apply this rule to every template you create or modify.

## Template Structure
```
templates/
├── base.html               — site shell
├── partials/nav.html       — sticky header nav (dotted inAct logo + search)
├── partials/footer.html    — full-width orange footer
├── public/                 — homepage, issue, article, archive, about, submit
├── author/                 — dashboard, 4-step submission wizard
├── editorial/              — screening queue, detail, moderation
└── reviewer/               — invitation response, workspace (split pane)
```

## UI Conventions

### Confirmation dialogs — always use the custom modal, never native browser dialogs
Never use `confirm()`, `alert()`, or `onsubmit="return confirm(…)"`. The site has a global Alpine.js modal store wired up in `base.html` + `static/js/main.js`.

**For forms** — add `data-confirm="Your message here"` to the `<form>` element. The `main.js` submit interceptor catches it automatically and shows the modal. Optionally add `data-confirm-ok="Label"` to customise the confirm button text:
```html
<form method="post" action="…"
      data-confirm="Are you sure you want to delete this?"
      data-confirm-ok="Delete">
  {% csrf_token %}
  <button type="submit">Delete</button>
</form>
```

**For JavaScript actions** — use the `showConfirm(message, { title, okLabel })` global (returns a Promise):
```js
showConfirm('Remove this item?', { okLabel: 'Remove' }).then(ok => {
  if (ok) { /* proceed */ }
});
```

**For non-destructive notices** — use `showAlert(message)`.

## API
REST API at `/api/v1/` uses JWT auth (`djangorestframework-simplejwt`).
See `apps/api/urls.py` and `design/openapi.yaml` for full endpoint list.

## Celery Beat Tasks
- `cleanup_expired_pdf_exports` — delete expired PDF files
- `send_review_reminders` — email reviewers with upcoming deadlines

## S3 Upgrade Path
Set `USE_S3=True` in `.env` + bucket credentials. `django-storages` is already installed. See README.md §Phase 2.

## Deployment
See `README.md` and `nginx/nginx.conf`. Uses Gunicorn (`config.wsgi`) behind Nginx,
deployed bare-metal via `scripts/deploy.sh` (systemd units, no Docker).
