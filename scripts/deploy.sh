#!/usr/bin/env bash
# inAct Journal — bare-metal deploy (staging & production)
#
# Production target: https://inact.lmta.lt  ·  app dir: /var/www/inact
# One script for both environments. All differences live in .env.
#
# What a first run does end-to-end (no manual steps besides editing .env):
#   apt packages → app user → .env → venv + pip → git pull → PostgreSQL
#   role+database → dirs → collectstatic → migrate → deploy checks →
#   systemd units → Nginx site → Let's Encrypt SSL → start services →
#   Django superuser + JournalConfig seed.
#
# First deploy:
#   git clone <repo> /var/www/inact && cd /var/www/inact
#   sudo bash scripts/deploy.sh
#
# Subsequent deploys (skip system packages, DB creation, SSL):
#   sudo bash scripts/deploy.sh --update
#
# Service names default to inact-gunicorn / inact-celery / inact-celerybeat.
# Override at the top or via env vars before calling:
#   GUNICORN_SERVICE=my-service sudo bash scripts/deploy.sh --update
#
# ── Configurable ─────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$APP_DIR/venv"
DJANGO_SETTINGS="${DJANGO_SETTINGS_MODULE_OVERRIDE:-config.settings.production}"
GUNICORN_PORT="${GUNICORN_PORT:-5002}"
GUNICORN_WORKERS="${GUNICORN_WORKERS:-3}"

GUNICORN_SERVICE="${GUNICORN_SERVICE:-inact-gunicorn}"
CELERY_SERVICE="${CELERY_SERVICE:-inact-celery}"
CELERY_BEAT_SERVICE="${CELERY_BEAT_SERVICE:-inact-celerybeat}"
NGINX_SITE="${NGINX_SITE:-inact}"
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

UPDATE_ONLY=false
[[ "${1:-}" == "--update" ]] && UPDATE_ONLY=true

if [[ $EUID -ne 0 ]]; then
  echo "ERROR: Run with sudo." >&2
  exit 1
fi

# User who owns the repo (the person who ran sudo, or directory owner)
RUN_AS="${SUDO_USER:-$(stat -c '%U' "$APP_DIR" 2>/dev/null || echo root)}"

# ── Colours ──────────────────────────────────────────────────────────────────
BOLD=$(tput bold 2>/dev/null || true)
GREEN=$(tput setaf 2 2>/dev/null || true)
YELLOW=$(tput setaf 3 2>/dev/null || true)
RED=$(tput setaf 1 2>/dev/null || true)
RESET=$(tput sgr0 2>/dev/null || true)

step() { echo ""; echo "${BOLD}${GREEN}▶  $*${RESET}"; }
warn() { echo "${YELLOW}⚠   $*${RESET}"; }
die()  { echo "${RED}✗   $*${RESET}" >&2; exit 1; }

run_django() {
  # Run a manage.py command as RUN_AS with the correct settings
  sudo -u "$RUN_AS" env DJANGO_SETTINGS_MODULE="$DJANGO_SETTINGS" \
    "$VENV_DIR/bin/python" "$APP_DIR/manage.py" "$@"
}

echo ""
echo "${BOLD}inAct Journal — Deploy${RESET}  ($(date '+%Y-%m-%d %H:%M %Z'))"
echo "  App dir  : $APP_DIR"
echo "  Run as   : $RUN_AS"
echo "  Mode     : $( $UPDATE_ONLY && echo update || echo 'first deploy' )"

# ── 1. Verify repo ────────────────────────────────────────────────────────────
step "Verifying repository"
[[ -f "$APP_DIR/manage.py" ]] || die "manage.py not found in $APP_DIR — wrong directory?"

# ── 2. System packages ────────────────────────────────────────────────────────
if ! $UPDATE_ONLY; then
  step "Installing system packages"
  apt-get update -q --allow-releaseinfo-change
  apt-get install -y --no-install-recommends \
    python3.11 python3.11-venv python3.11-dev python3-pip \
    postgresql postgresql-contrib \
    redis-server \
    nginx \
    certbot python3-certbot-nginx \
    git curl build-essential \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 libharfbuzz0b libffi-dev \
    shared-mime-info fonts-liberation fonts-dejavu-core \
    libmagic1
fi

# ── 3. App user (production) ──────────────────────────────────────────────────
# On a dedicated server, create a system user to own the app files.
# On a shared server (staging) where RUN_AS is an existing user, skip this.
if ! $UPDATE_ONLY; then
  if ! id "$RUN_AS" &>/dev/null || [[ "$RUN_AS" == "root" ]]; then
    warn "No non-root owner detected — creating system user 'inact'."
    RUN_AS="inact"
    id "$RUN_AS" &>/dev/null || useradd --system --home "$APP_DIR" --shell /bin/bash "$RUN_AS"
    mkdir -p "$APP_DIR"
    chown "$RUN_AS:$RUN_AS" "$APP_DIR"
  fi
fi

# ── 4. .env file ─────────────────────────────────────────────────────────────
if [[ ! -f "$APP_DIR/.env" ]]; then
  step ".env not found — creating from template"
  sudo -u "$RUN_AS" cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  chmod 640 "$APP_DIR/.env"
  echo ""
  echo "  IMPORTANT: $APP_DIR/.env was created from .env.example."
  echo "  Edit it now — all fields below are required:"
  echo ""
  echo "    SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(50))')"
  echo "    DEBUG=False"
  echo "    DJANGO_SETTINGS_MODULE=config.settings.production"
  echo "    ALLOWED_HOSTS=inact.lmta.lt,www.inact.lmta.lt"
  echo "    CSRF_TRUSTED_ORIGINS=https://inact.lmta.lt,https://www.inact.lmta.lt"
  echo "    SITE_URL=https://inact.lmta.lt"
  echo "    # --- PostgreSQL (deploy.sh creates this role + database automatically) ---"
  echo "    DB_NAME=inact_journal"
  echo "    DB_USER=inact"
  echo "    DB_PASSWORD=<strong password>   # generate: openssl rand -base64 24"
  echo "    DB_HOST=localhost"
  echo "    CELERY_BROKER_URL=redis://localhost:6379/0"
  echo "    CELERY_TASK_ALWAYS_EAGER=False"
  echo "    ANYMAIL_BACKEND=mailersend"
  echo "    MAILERSEND_API_TOKEN=<token>"
  echo "    DEFAULT_FROM_EMAIL=noreply@inact.lmta.lt"
  echo "    # --- Django superuser (deploy.sh creates this login automatically) ---"
  echo "    DJANGO_SUPERUSER_EMAIL=admin@inact.lmta.lt"
  echo "    DJANGO_SUPERUSER_PASSWORD=<strong password>   # generate: openssl rand -base64 24"
  echo ""
  read -rp "  Press Enter after editing .env to continue..." _
fi

_env_val() { grep "^$1=" "$APP_DIR/.env" | cut -d= -f2- | tr -d ' "'"'" | head -1; }

# ── 5. Python virtual environment ─────────────────────────────────────────────
step "Python virtual environment"
if [[ ! -d "$VENV_DIR" ]]; then
  sudo -u "$RUN_AS" python3.11 -m venv "$VENV_DIR"
fi
sudo -u "$RUN_AS" "$VENV_DIR/bin/pip" install -q --upgrade pip
sudo -u "$RUN_AS" "$VENV_DIR/bin/pip" install -q -r "$APP_DIR/requirements/production.txt"
echo "  Dependencies installed."

# ── 6. Git pull ───────────────────────────────────────────────────────────────
step "Code update"
sudo -u "$RUN_AS" git -C "$APP_DIR" fetch --quiet
LOCAL=$(sudo -u "$RUN_AS" git -C "$APP_DIR" rev-parse HEAD)
REMOTE=$(sudo -u "$RUN_AS" git -C "$APP_DIR" rev-parse '@{u}' 2>/dev/null || echo "")
if [[ -z "$REMOTE" ]]; then
  warn "No upstream tracking branch — skipping pull."
elif [[ "$LOCAL" == "$REMOTE" ]]; then
  echo "  Already up to date ($(sudo -u "$RUN_AS" git -C "$APP_DIR" rev-parse --short HEAD))."
else
  sudo -u "$RUN_AS" git -C "$APP_DIR" pull --ff-only
  echo "  Updated to $(sudo -u "$RUN_AS" git -C "$APP_DIR" rev-parse --short HEAD)."
fi

# ── 7. PostgreSQL ─────────────────────────────────────────────────────────────
if ! $UPDATE_ONLY; then
  step "PostgreSQL setup"
  DB_NAME=$(_env_val DB_NAME); DB_NAME="${DB_NAME:-inact_journal}"
  DB_USER=$(_env_val DB_USER); DB_USER="${DB_USER:-inact}"
  DB_PASS=$(_env_val DB_PASSWORD)
  [[ -n "$DB_PASS" ]] || die "DB_PASSWORD is empty in .env — set it before first deploy."

  systemctl enable --now postgresql

  # Role (idempotent: create if missing, otherwise sync the password from .env)
  if sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1; then
    sudo -u postgres psql -c "ALTER ROLE ${DB_USER} WITH LOGIN PASSWORD '${DB_PASS}';"
  else
    sudo -u postgres psql -c "CREATE ROLE ${DB_USER} WITH LOGIN PASSWORD '${DB_PASS}';"
  fi

  # Django-recommended per-role session defaults
  sudo -u postgres psql -c "ALTER ROLE ${DB_USER} SET client_encoding TO 'utf8';" || true
  sudo -u postgres psql -c "ALTER ROLE ${DB_USER} SET default_transaction_isolation TO 'read committed';" || true
  sudo -u postgres psql -c "ALTER ROLE ${DB_USER} SET timezone TO 'UTC';" || true

  # Database owned by the app role
  sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" \
    | grep -q 1 || sudo -u postgres psql -c \
    "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"

  sudo -u postgres psql -c \
    "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};" || true

  # PostgreSQL 15+ locks down the public schema — give the app role ownership so
  # migrations can CREATE tables. Without this, `migrate` fails with "permission
  # denied for schema public" on Postgres 15/16.
  sudo -u postgres psql -d "${DB_NAME}" -c "ALTER SCHEMA public OWNER TO ${DB_USER};" || true
  sudo -u postgres psql -d "${DB_NAME}" -c "GRANT ALL ON SCHEMA public TO ${DB_USER};" || true

  echo "  Database '${DB_NAME}' ready (owner: ${DB_USER})."
fi

# ── 8. Directories ────────────────────────────────────────────────────────────
step "Creating directories"
sudo -u "$RUN_AS" mkdir -p "$APP_DIR/media" "$APP_DIR/staticfiles" "$APP_DIR/logs"
echo "  media / staticfiles / logs ready."

# ── 9. Static files ───────────────────────────────────────────────────────────
step "Collecting static files"
run_django collectstatic --noinput

# ── 10. Migrations ────────────────────────────────────────────────────────────
step "Database migrations"
run_django migrate --noinput
echo "  Migrations applied (post_migrate signals fired — Site domain synced)."

# ── 11. Django system check ───────────────────────────────────────────────────
step "Django deployment checks"
run_django check --deploy 2>&1 | grep -vE "^(System check|$)" || true

# ── 12. Systemd units ─────────────────────────────────────────────────────────
step "Writing systemd units"

cat > /etc/systemd/system/"${GUNICORN_SERVICE}.service" << EOF
[Unit]
Description=inAct Journal — Gunicorn
After=network.target postgresql.service

[Service]
User=${RUN_AS}
Group=${RUN_AS}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
Environment=DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS}
ExecStart=${VENV_DIR}/bin/gunicorn \\
    config.wsgi:application \\
    --workers ${GUNICORN_WORKERS} \\
    --bind 127.0.0.1:${GUNICORN_PORT} \\
    --timeout 120 \\
    --access-logfile ${APP_DIR}/logs/gunicorn-access.log \\
    --error-logfile ${APP_DIR}/logs/gunicorn-error.log
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/"${CELERY_SERVICE}.service" << EOF
[Unit]
Description=inAct Journal — Celery worker
After=network.target redis.service

[Service]
User=${RUN_AS}
Group=${RUN_AS}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
Environment=DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS}
ExecStart=${VENV_DIR}/bin/celery \\
    -A config.celery worker \\
    --loglevel=info \\
    --logfile=${APP_DIR}/logs/celery.log \\
    --concurrency=2
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/"${CELERY_BEAT_SERVICE}.service" << EOF
[Unit]
Description=inAct Journal — Celery Beat scheduler
After=network.target redis.service

[Service]
User=${RUN_AS}
Group=${RUN_AS}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
Environment=DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS}
ExecStart=${VENV_DIR}/bin/celery \\
    -A config.celery beat \\
    --loglevel=info \\
    --logfile=${APP_DIR}/logs/celerybeat.log \\
    --scheduler django_celery_beat.schedulers:DatabaseScheduler
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "  Units written: ${GUNICORN_SERVICE}, ${CELERY_SERVICE}, ${CELERY_BEAT_SERVICE}"

# ── 13. Nginx ─────────────────────────────────────────────────────────────────
if ! $UPDATE_ONLY; then
  step "Deploying Nginx config"
  cp "$APP_DIR/nginx/nginx-production.conf" "/etc/nginx/sites-available/${NGINX_SITE}"
  ln -sf "/etc/nginx/sites-available/${NGINX_SITE}" "/etc/nginx/sites-enabled/${NGINX_SITE}"
  rm -f /etc/nginx/sites-enabled/default
  nginx -t
fi

# ── 14. SSL ───────────────────────────────────────────────────────────────────
if ! $UPDATE_ONLY; then
  step "SSL certificate (Let's Encrypt)"
  DOMAIN=$(_env_val ALLOWED_HOSTS | cut -d, -f1)
  SU_EMAIL=$(_env_val DJANGO_SUPERUSER_EMAIL)
  # One -d flag per host in ALLOWED_HOSTS (e.g. inact.lmta.lt AND www.inact.lmta.lt),
  # so the cert matches every name in the Nginx server_name. Every host must resolve
  # in DNS or certbot will fail for the whole set.
  CERT_DOMAINS=()
  IFS=',' read -ra _hosts <<< "$(_env_val ALLOWED_HOSTS)"
  for _h in "${_hosts[@]}"; do
    _h="$(echo "$_h" | tr -d ' ')"
    [[ -n "$_h" ]] && CERT_DOMAINS+=(-d "$_h")
  done
  systemctl enable --now nginx
  certbot --nginx "${CERT_DOMAINS[@]}" --non-interactive --agree-tos \
    --redirect --email "${SU_EMAIL:-admin@${DOMAIN}}" \
    || warn "certbot failed — check DNS for all of: $(_env_val ALLOWED_HOSTS) — then re-run: sudo certbot --nginx ${CERT_DOMAINS[*]}"
fi

# ── 15. Start / restart services ─────────────────────────────────────────────
step "Starting services"
systemctl enable --now redis-server
systemctl daemon-reload
systemctl enable "${GUNICORN_SERVICE}" "${CELERY_SERVICE}" "${CELERY_BEAT_SERVICE}"
systemctl restart "${GUNICORN_SERVICE}" "${CELERY_SERVICE}" "${CELERY_BEAT_SERVICE}"
$UPDATE_ONLY || systemctl reload nginx
echo "  All services running."

# ── 16. Superuser + admin roles (first deploy only) ───────────────────────────
# Credentials come from .env (DJANGO_SUPERUSER_EMAIL / DJANGO_SUPERUSER_PASSWORD).
# The user is created as a Django superuser AND granted the SYSTEM_ADMIN +
# JOURNAL_ADMIN journal roles, so it can log in to /admin/ and /journal-admin/
# immediately — no manual shell bootstrap needed. Existing users are never
# password-reset; only roles/flags are (idempotently) re-applied.
if ! $UPDATE_ONLY; then
  step "Creating superuser + granting admin roles"
  SU_EMAIL=$(_env_val DJANGO_SUPERUSER_EMAIL)
  SU_PASS=$(_env_val DJANGO_SUPERUSER_PASSWORD)
  if [[ -z "$SU_EMAIL" || -z "$SU_PASS" ]]; then
    warn "DJANGO_SUPERUSER_EMAIL/PASSWORD not set in .env — skipping superuser creation."
  else
    run_django shell -c "
from apps.accounts.models import User, UserRole
u, created = User.objects.get_or_create(
    email='${SU_EMAIL}', defaults={'first_name': 'Admin', 'last_name': 'User'})
if created:
    u.set_password('${SU_PASS}')
u.is_staff = True
u.is_superuser = True
u.roles = [UserRole.SYSTEM_ADMIN, UserRole.JOURNAL_ADMIN]
u.save()
print('Superuser ' + ('created' if created else 'updated') + ':', u.email, '| roles:', u.roles)
"
  fi
  run_django shell -c "
from apps.journal.models import JournalConfig
j = JournalConfig.get()
if not j.name:
    j.name = 'inAct'; j.submission_open = True; j.save()
    print('Journal config seeded.')
"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
SITE_URL=$(_env_val SITE_URL || echo "https://$(hostname -f)")
COMMIT=$(sudo -u "$RUN_AS" git -C "$APP_DIR" rev-parse --short HEAD 2>/dev/null || echo "unknown")

echo ""
echo "${BOLD}${GREEN}✓ Deploy complete${RESET}  commit=${COMMIT}  $(date '+%Y-%m-%d %H:%M %Z')"
echo ""
echo "  Site:   ${SITE_URL}"
echo "  Admin:  ${SITE_URL}/admin/   ·   Journal admin: ${SITE_URL}/journal-admin/"
echo ""
echo "  Database:  $(_env_val DB_NAME) (owner $(_env_val DB_USER)) on localhost:5432"
echo "  Superuser: $(_env_val DJANGO_SUPERUSER_EMAIL)  (password from .env; roles: system_admin, journal_admin)"
echo ""
echo "  Logs:"
echo "    sudo journalctl -u ${GUNICORN_SERVICE} -f"
echo "    tail -f ${APP_DIR}/logs/gunicorn-error.log"
echo "    tail -f ${APP_DIR}/logs/celery.log"
echo ""
echo "  Future updates:"
echo "    sudo bash scripts/deploy.sh --update"
echo ""
