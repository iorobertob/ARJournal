#!/usr/bin/env bash
# Trans/Act Journal — bare-metal deploy (staging & production)
#
# One script for both environments. All differences live in .env.
#
# First deploy:
#   sudo bash scripts/deploy.sh
#
# Subsequent deploys (skip system packages, DB creation, SSL):
#   sudo bash scripts/deploy.sh --update
#
# Service names default to transact-gunicorn / transact-celery / transact-celerybeat.
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

GUNICORN_SERVICE="${GUNICORN_SERVICE:-transact-gunicorn}"
CELERY_SERVICE="${CELERY_SERVICE:-transact-celery}"
CELERY_BEAT_SERVICE="${CELERY_BEAT_SERVICE:-transact-celerybeat}"
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
echo "${BOLD}Trans/Act Journal — Deploy${RESET}  ($(date '+%Y-%m-%d %H:%M %Z'))"
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
    warn "No non-root owner detected — creating system user 'transact'."
    RUN_AS="transact"
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
  echo "    ALLOWED_HOSTS=your-domain.com,www.your-domain.com"
  echo "    CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://www.your-domain.com"
  echo "    SITE_URL=https://your-domain.com"
  echo "    DB_NAME=transact_journal"
  echo "    DB_USER=transact"
  echo "    DB_PASSWORD=<strong password>"
  echo "    DB_HOST=localhost"
  echo "    CELERY_BROKER_URL=redis://localhost:6379/0"
  echo "    CELERY_TASK_ALWAYS_EAGER=False"
  echo "    ANYMAIL_BACKEND=mailersend"
  echo "    MAILERSEND_API_TOKEN=<token>"
  echo "    DEFAULT_FROM_EMAIL=noreply@your-domain.com"
  echo "    DJANGO_SUPERUSER_EMAIL=admin@your-domain.com"
  echo "    DJANGO_SUPERUSER_PASSWORD=<strong password>"
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
  DB_NAME=$(_env_val DB_NAME); DB_NAME="${DB_NAME:-transact_journal}"
  DB_USER=$(_env_val DB_USER); DB_USER="${DB_USER:-transact}"
  DB_PASS=$(_env_val DB_PASSWORD)

  systemctl enable --now postgresql

  sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" \
    | grep -q 1 || sudo -u postgres psql -c \
    "CREATE ROLE ${DB_USER} WITH LOGIN PASSWORD '${DB_PASS}';"

  sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" \
    | grep -q 1 || sudo -u postgres psql -c \
    "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"

  sudo -u postgres psql -c \
    "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};" || true

  echo "  Database '${DB_NAME}' ready."
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
Description=Trans/Act Journal — Gunicorn
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
Description=Trans/Act Journal — Celery worker
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
Description=Trans/Act Journal — Celery Beat scheduler
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
  cp "$APP_DIR/nginx/nginx-production.conf" /etc/nginx/sites-available/transact
  ln -sf /etc/nginx/sites-available/transact /etc/nginx/sites-enabled/transact
  rm -f /etc/nginx/sites-enabled/default
  nginx -t
fi

# ── 14. SSL ───────────────────────────────────────────────────────────────────
if ! $UPDATE_ONLY; then
  step "SSL certificate (Let's Encrypt)"
  DOMAIN=$(_env_val ALLOWED_HOSTS | cut -d, -f1)
  SU_EMAIL=$(_env_val DJANGO_SUPERUSER_EMAIL)
  systemctl enable --now nginx
  certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos \
    --email "${SU_EMAIL:-admin@${DOMAIN}}" \
    || warn "certbot failed — check DNS and re-run: sudo certbot --nginx -d ${DOMAIN}"
fi

# ── 15. Start / restart services ─────────────────────────────────────────────
step "Starting services"
systemctl enable --now redis-server
systemctl daemon-reload
systemctl enable "${GUNICORN_SERVICE}" "${CELERY_SERVICE}" "${CELERY_BEAT_SERVICE}"
systemctl restart "${GUNICORN_SERVICE}" "${CELERY_SERVICE}" "${CELERY_BEAT_SERVICE}"
$UPDATE_ONLY || systemctl reload nginx
echo "  All services running."

# ── 16. Superuser (first deploy only) ─────────────────────────────────────────
if ! $UPDATE_ONLY; then
  step "Creating superuser"
  SU_EMAIL=$(_env_val DJANGO_SUPERUSER_EMAIL)
  SU_PASS=$(_env_val DJANGO_SUPERUSER_PASSWORD)
  run_django shell -c "
from apps.accounts.models import User
if not User.objects.filter(email='${SU_EMAIL}').exists():
    User.objects.create_superuser(email='${SU_EMAIL}', password='${SU_PASS}',
                                  first_name='Admin', last_name='User')
    print('Superuser created.')
else:
    print('Superuser already exists.')
"
  run_django shell -c "
from apps.journal.models import JournalConfig
j = JournalConfig.get()
if not j.name:
    j.name = 'Trans/Act'; j.submission_open = True; j.save()
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
echo "  Admin:  ${SITE_URL}/admin/"
echo ""
echo "  Logs:"
echo "    sudo journalctl -u ${GUNICORN_SERVICE} -f"
echo "    tail -f ${APP_DIR}/logs/gunicorn-error.log"
echo "    tail -f ${APP_DIR}/logs/celery.log"
echo ""
echo "  Future updates:"
echo "    sudo bash scripts/deploy.sh --update"
echo ""
