#!/usr/bin/env bash
# Trans/Act Journal — STAGING deploy script
# Target: https://misc.lmta.lt/<subpath>  (subpath on shared server)
# Tested on Ubuntu 22.04 LTS / Debian 12
#
# Run from inside the repository:
#   sudo bash scripts/deploy-staging.sh           # first deploy
#   sudo bash scripts/deploy-staging.sh --update  # subsequent deploys
#
# The script auto-detects the repo root from its own location, so the repo can
# live anywhere (/var/www/ARJournal, /opt/transact-staging, etc.).
# All file operations (venv, pip, Django) run as the repo's actual owner, not
# a created system user — this avoids permission issues on shared web servers.
#
set -euo pipefail

# ── Auto-detect paths ─────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# User who owns the repo files (the person who cloned it / ran sudo)
# SUDO_USER is set by sudo to the original caller; fall back to directory owner.
RUN_AS="${SUDO_USER:-$(stat -c '%U' "$APP_DIR")}"

DJANGO_SETTINGS="config.settings.staging"
GUNICORN_PORT=5003
GUNICORN_WORKERS=2

UPDATE_ONLY=false
[[ "${1:-}" == "--update" ]] && UPDATE_ONLY=true

if [[ $EUID -ne 0 ]]; then
  echo "ERROR: Run with sudo: sudo bash scripts/deploy-staging.sh"
  exit 1
fi

log() { echo ""; echo "==> $*"; }

log "App directory: $APP_DIR"
log "Running file operations as: $RUN_AS"

# ── 1. Verify repo ────────────────────────────────────────────────────────────
if [ ! -f "$APP_DIR/manage.py" ]; then
  echo "ERROR: manage.py not found in $APP_DIR"
  echo "  Run this script from inside the repository."
  exit 1
fi

# ── 2. System packages ────────────────────────────────────────────────────────
if ! $UPDATE_ONLY; then
  log "Installing system packages..."
  # --allow-releaseinfo-change: accepts PPAs that changed their Label metadata
  # (e.g. ondrej/apache2 on Ubuntu 22.04) without interactive prompts.
  apt-get update -q --allow-releaseinfo-change
  apt-get install -y --no-install-recommends \
    python3.11 python3.11-venv python3.11-dev python3-pip \
    postgresql postgresql-contrib \
    redis-server \
    git curl build-essential \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 libharfbuzz0b libffi-dev \
    shared-mime-info fonts-liberation fonts-dejavu-core \
    libmagic1
fi

# ── 3. Pull latest code ───────────────────────────────────────────────────────
log "Pulling latest code..."
sudo -u "$RUN_AS" git -C "$APP_DIR" pull || echo "  (git pull skipped)"

# ── 4. .env file ─────────────────────────────────────────────────────────────
if [ ! -f "$APP_DIR/.env" ]; then
  sudo -u "$RUN_AS" cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  chmod 640 "$APP_DIR/.env"
  echo ""
  echo "  IMPORTANT: Edit $APP_DIR/.env now."
  echo "  Required staging values:"
  echo ""
  echo "    DEBUG=False"
  echo "    SECRET_KEY=<50+ random chars>"
  echo "    DJANGO_SETTINGS_MODULE=config.settings.staging"
  echo "    SCRIPT_NAME=/ARJournal        # URL subpath — must start with /"
  echo "    ALLOWED_HOSTS=misc.lmta.lt"
  echo "    CSRF_TRUSTED_ORIGINS=https://misc.lmta.lt"
  echo "    SITE_URL=https://misc.lmta.lt/ARJournal"
  echo "    DB_NAME=transact_staging"
  echo "    DB_USER=transact"
  echo "    DB_PASSWORD=<password>"
  echo "    DB_HOST=localhost"
  echo "    CELERY_BROKER_URL=redis://localhost:6379/1"
  echo "    CELERY_TASK_ALWAYS_EAGER=False"
  echo "    ANYMAIL_BACKEND=console"
  echo "    DJANGO_SUPERUSER_EMAIL=admin@lmta.lt"
  echo "    DJANGO_SUPERUSER_PASSWORD=<password>"
  echo ""
  read -rp "  Press Enter after editing .env to continue..." _
fi

# Read DB config from .env
DB_NAME=$(grep '^DB_NAME=' "$APP_DIR/.env" | cut -d= -f2 | tr -d ' ')
DB_USER=$(grep '^DB_USER=' "$APP_DIR/.env" | cut -d= -f2 | tr -d ' ')
DB_PASS=$(grep '^DB_PASSWORD=' "$APP_DIR/.env" | cut -d= -f2 | tr -d ' ')
DB_NAME="${DB_NAME:-transact_staging}"
DB_USER="${DB_USER:-transact}"

# ── 5. Python virtual environment ─────────────────────────────────────────────
log "Setting up Python virtual environment..."
if [ ! -d "$APP_DIR/venv" ]; then
  sudo -u "$RUN_AS" python3.11 -m venv "$APP_DIR/venv"
fi
sudo -u "$RUN_AS" "$APP_DIR/venv/bin/pip" install -q --upgrade pip
sudo -u "$RUN_AS" "$APP_DIR/venv/bin/pip" install -q -r "$APP_DIR/requirements/production.txt"

# ── 6. PostgreSQL ─────────────────────────────────────────────────────────────
if ! $UPDATE_ONLY; then
  log "Setting up PostgreSQL (staging database)..."
  systemctl enable --now postgresql

  sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE ROLE ${DB_USER} WITH LOGIN PASSWORD '${DB_PASS}';"

  sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"

  sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"
fi

# ── 7. Directories ────────────────────────────────────────────────────────────
sudo -u "$RUN_AS" mkdir -p "$APP_DIR/media" "$APP_DIR/staticfiles" "$APP_DIR/logs"

# ── 8. migrate + collectstatic ────────────────────────────────────────────────
log "Running Django migrations..."
sudo -u "$RUN_AS" env DJANGO_SETTINGS_MODULE="$DJANGO_SETTINGS" \
  "$APP_DIR/venv/bin/python" "$APP_DIR/manage.py" migrate --noinput

log "Collecting static files..."
sudo -u "$RUN_AS" env DJANGO_SETTINGS_MODULE="$DJANGO_SETTINGS" \
  "$APP_DIR/venv/bin/python" "$APP_DIR/manage.py" collectstatic --noinput

# ── 9. Systemd: Gunicorn ──────────────────────────────────────────────────────
log "Writing systemd unit: transact-staging-gunicorn.service..."
cat > /etc/systemd/system/transact-staging-gunicorn.service << EOF
[Unit]
Description=Trans/Act Journal STAGING — Gunicorn (port ${GUNICORN_PORT})
After=network.target postgresql.service

[Service]
User=${RUN_AS}
Group=${RUN_AS}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
Environment=DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS}
ExecStart=${APP_DIR}/venv/bin/gunicorn \\
    --workers ${GUNICORN_WORKERS} \\
    --bind 127.0.0.1:${GUNICORN_PORT} \\
    --timeout 120 \\
    --access-logfile ${APP_DIR}/logs/gunicorn-access.log \\
    --error-logfile ${APP_DIR}/logs/gunicorn-error.log \\
    config.wsgi:application
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# ── 10. Systemd: Celery ───────────────────────────────────────────────────────
log "Writing systemd unit: transact-staging-celery.service..."
cat > /etc/systemd/system/transact-staging-celery.service << EOF
[Unit]
Description=Trans/Act Journal STAGING — Celery worker
After=network.target redis.service

[Service]
User=${RUN_AS}
Group=${RUN_AS}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
Environment=DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS}
ExecStart=${APP_DIR}/venv/bin/celery \\
    -A config.celery worker \\
    --loglevel=info \\
    --logfile=${APP_DIR}/logs/celery.log \\
    --concurrency=1
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# ── 11. Enable and start ──────────────────────────────────────────────────────
log "Starting services..."
systemctl enable --now redis-server
systemctl daemon-reload
systemctl enable transact-staging-gunicorn transact-staging-celery
systemctl restart transact-staging-gunicorn transact-staging-celery

# ── 12. Superuser (first deploy only) ─────────────────────────────────────────
if ! $UPDATE_ONLY; then
  SU_EMAIL=$(grep '^DJANGO_SUPERUSER_EMAIL=' "$APP_DIR/.env" | cut -d= -f2 | tr -d ' ')
  SU_PASS=$(grep '^DJANGO_SUPERUSER_PASSWORD=' "$APP_DIR/.env" | cut -d= -f2 | tr -d ' ')

  sudo -u "$RUN_AS" env DJANGO_SETTINGS_MODULE="$DJANGO_SETTINGS" \
    "$APP_DIR/venv/bin/python" "$APP_DIR/manage.py" shell -c "
from apps.accounts.models import User
email = '${SU_EMAIL}'
password = '${SU_PASS}'
if not User.objects.filter(email=email).exists():
    User.objects.create_superuser(email=email, password=password,
                                  first_name='Admin', last_name='User')
    print('Superuser created:', email)
else:
    print('Superuser already exists:', email)
"

  sudo -u "$RUN_AS" env DJANGO_SETTINGS_MODULE="$DJANGO_SETTINGS" \
    "$APP_DIR/venv/bin/python" "$APP_DIR/manage.py" shell -c "
from apps.journal.models import JournalConfig
j = JournalConfig.get()
if not j.name:
    j.name = 'Trans/Act'; j.tagline = 'A journal for artistic research'
    j.submission_open = True; j.save(); print('Journal config seeded.')
"
fi

# Read SCRIPT_NAME from .env for the summary message
SCRIPT_NAME_VAL=$(grep '^SCRIPT_NAME=' "$APP_DIR/.env" 2>/dev/null | cut -d= -f2 | tr -d ' ' || echo "/ARJournal")

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "============================================================"
echo "  Trans/Act Journal STAGING deployed."
echo ""
echo "  Gunicorn running on 127.0.0.1:${GUNICORN_PORT}"
echo ""
echo "  NEXT STEP — add location blocks to the Nginx server for misc.lmta.lt:"
echo ""
echo "    sudo nano /etc/nginx/sites-available/misc.lmta.lt"
echo "    # Paste the blocks from: $APP_DIR/nginx/nginx-staging.conf"
echo "    sudo nginx -t && sudo systemctl reload nginx"
echo ""
echo "  Then visit: https://misc.lmta.lt${SCRIPT_NAME_VAL}"
echo "  Admin:       https://misc.lmta.lt${SCRIPT_NAME_VAL}/admin/"
echo ""
echo "  Service management:"
echo "    sudo systemctl status transact-staging-gunicorn"
echo "    sudo systemctl restart transact-staging-gunicorn"
echo "    sudo journalctl -u transact-staging-gunicorn -f"
echo "    tail -f ${APP_DIR}/logs/gunicorn-error.log"
echo "    tail -f ${APP_DIR}/logs/celery.log"
echo "============================================================"
echo ""
