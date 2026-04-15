#!/usr/bin/env bash
# Trans/Act Journal — STAGING deploy script
# Target: https://misc.lmta.lt/journal  (subpath on shared server)
# Tested on Ubuntu 22.04 LTS / Debian 12
#
# Usage (first deploy):
#   sudo bash scripts/deploy-staging.sh
#
# Usage (update only — skip system package install):
#   sudo bash scripts/deploy-staging.sh --update
#
# What this script does:
#   - Installs system packages (Python 3.11, WeasyPrint libs, libmagic1, etc.)
#   - Creates /opt/transact-staging and the 'transact' system user
#   - Sets up a Python venv, installs requirements/production.txt
#   - Writes systemd unit files for Gunicorn on port 5003
#     (separate from production so both can coexist on the same server)
#   - Does NOT touch Nginx — see nginx/nginx-staging.conf for the location
#     blocks you need to paste into the existing misc.lmta.lt server block
#   - Runs migrate + collectstatic
#
set -euo pipefail

APP_DIR="/opt/transact-staging"
APP_USER="transact"
REPO_URL=""                      # set if cloning fresh; leave empty if already present
DJANGO_SETTINGS="config.settings.staging"
GUNICORN_PORT=5003
GUNICORN_WORKERS=2

UPDATE_ONLY=false
[[ "${1:-}" == "--update" ]] && UPDATE_ONLY=true

if [[ $EUID -ne 0 ]]; then
  echo "ERROR: Run with sudo."
  exit 1
fi

log() { echo ""; echo "==> $*"; }

# ── 1. System packages ───────────────────────────────────────────────────────
if ! $UPDATE_ONLY; then
  log "Installing system packages..."
  apt-get update -q
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

# ── 2. App user and directory ────────────────────────────────────────────────
if ! $UPDATE_ONLY; then
  log "Creating app user and directory..."
  id "$APP_USER" &>/dev/null || useradd --system --home "$APP_DIR" --shell /bin/bash "$APP_USER"
  mkdir -p "$APP_DIR"
  chown "$APP_USER:$APP_USER" "$APP_DIR"
fi

# ── 3. Clone or pull ─────────────────────────────────────────────────────────
if [ ! -d "$APP_DIR/.git" ]; then
  if [ -z "$REPO_URL" ]; then
    echo ""
    echo "ERROR: REPO_URL not set and $APP_DIR is not a git repo."
    echo "  Clone manually: git clone <repo> $APP_DIR"
    echo "  Then re-run with --update"
    exit 1
  fi
  log "Cloning repository..."
  sudo -u "$APP_USER" git clone "$REPO_URL" "$APP_DIR"
else
  log "Pulling latest code..."
  sudo -u "$APP_USER" git -C "$APP_DIR" pull
fi

# ── 4. .env file ─────────────────────────────────────────────────────────────
if [ ! -f "$APP_DIR/.env" ]; then
  cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  chown "$APP_USER:$APP_USER" "$APP_DIR/.env"
  chmod 640 "$APP_DIR/.env"
  echo ""
  echo "  IMPORTANT: Edit $APP_DIR/.env now."
  echo "  At minimum set these for staging:"
  echo ""
  echo "    DEBUG=False"
  echo "    SECRET_KEY=<50+ random chars>"
  echo "    DJANGO_SETTINGS_MODULE=config.settings.staging"
  echo "    ALLOWED_HOSTS=misc.lmta.lt"
  echo "    CSRF_TRUSTED_ORIGINS=https://misc.lmta.lt"
  echo "    SITE_URL=https://misc.lmta.lt/journal"
  echo "    DB_NAME, DB_USER, DB_PASSWORD, DB_HOST=localhost"
  echo "    CELERY_BROKER_URL=redis://localhost:6379/1  (db=1, separate from prod)"
  echo "    CELERY_TASK_ALWAYS_EAGER=False"
  echo "    ANYMAIL_BACKEND=console  (or real backend for staging email tests)"
  echo ""
  read -rp "  Press Enter after editing .env to continue..." _
fi

# ── 5. Python virtual environment ────────────────────────────────────────────
log "Setting up Python virtual environment..."
if [ ! -d "$APP_DIR/venv" ]; then
  sudo -u "$APP_USER" python3.11 -m venv "$APP_DIR/venv"
fi
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -q --upgrade pip
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -q -r "$APP_DIR/requirements/production.txt"

# ── 6. Database (staging uses its own DB on the same Postgres instance) ───────
if ! $UPDATE_ONLY; then
  log "Setting up PostgreSQL (staging database)..."
  DB_NAME=$(grep '^DB_NAME=' "$APP_DIR/.env" | cut -d= -f2 | tr -d ' ')
  DB_USER=$(grep '^DB_USER=' "$APP_DIR/.env" | cut -d= -f2 | tr -d ' ')
  DB_PASS=$(grep '^DB_PASSWORD=' "$APP_DIR/.env" | cut -d= -f2 | tr -d ' ')
  DB_NAME="${DB_NAME:-transact_staging}"
  DB_USER="${DB_USER:-transact}"

  systemctl enable --now postgresql

  sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE ROLE ${DB_USER} WITH LOGIN PASSWORD '${DB_PASS}';"

  sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"

  sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"
fi

# ── 7. Directories ───────────────────────────────────────────────────────────
mkdir -p "$APP_DIR/media" "$APP_DIR/staticfiles" "$APP_DIR/logs"
chown -R "$APP_USER:$APP_USER" "$APP_DIR/media" "$APP_DIR/staticfiles" "$APP_DIR/logs"

# ── 8. Django migrate + collectstatic ────────────────────────────────────────
log "Running Django migrations..."
sudo -u "$APP_USER" env DJANGO_SETTINGS_MODULE="$DJANGO_SETTINGS" \
  "$APP_DIR/venv/bin/python" "$APP_DIR/manage.py" migrate --noinput

log "Collecting static files..."
sudo -u "$APP_USER" env DJANGO_SETTINGS_MODULE="$DJANGO_SETTINGS" \
  "$APP_DIR/venv/bin/python" "$APP_DIR/manage.py" collectstatic --noinput

# ── 9. Systemd: Gunicorn (staging, port 5003) ─────────────────────────────────
log "Writing systemd unit: transact-staging-gunicorn.service..."
cat > /etc/systemd/system/transact-staging-gunicorn.service << EOF
[Unit]
Description=Trans/Act Journal STAGING — Gunicorn (port ${GUNICORN_PORT})
After=network.target postgresql.service

[Service]
User=${APP_USER}
Group=${APP_USER}
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

# ── 10. Systemd: Celery worker (staging, redis db=1) ─────────────────────────
log "Writing systemd unit: transact-staging-celery.service..."
cat > /etc/systemd/system/transact-staging-celery.service << EOF
[Unit]
Description=Trans/Act Journal STAGING — Celery worker
After=network.target redis.service

[Service]
User=${APP_USER}
Group=${APP_USER}
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

# ── 11. Enable and start ─────────────────────────────────────────────────────
log "Enabling and starting services..."
systemctl enable --now redis-server
systemctl daemon-reload
systemctl enable --now transact-staging-gunicorn
systemctl enable --now transact-staging-celery

# ── 12. Superuser (first deploy) ─────────────────────────────────────────────
if ! $UPDATE_ONLY; then
  SU_EMAIL=$(grep '^DJANGO_SUPERUSER_EMAIL=' "$APP_DIR/.env" | cut -d= -f2 | tr -d ' ')
  SU_PASS=$(grep '^DJANGO_SUPERUSER_PASSWORD=' "$APP_DIR/.env" | cut -d= -f2 | tr -d ' ')

  sudo -u "$APP_USER" env DJANGO_SETTINGS_MODULE="$DJANGO_SETTINGS" \
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

  sudo -u "$APP_USER" env DJANGO_SETTINGS_MODULE="$DJANGO_SETTINGS" \
    "$APP_DIR/venv/bin/python" "$APP_DIR/manage.py" shell -c "
from apps.journal.models import JournalConfig
j = JournalConfig.get()
if not j.name:
    j.name = 'Trans/Act'; j.tagline = 'A journal for artistic research'
    j.submission_open = True; j.save(); print('Journal config seeded.')
"
fi

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo "============================================================"
echo "  Trans/Act Journal STAGING deployed."
echo ""
echo "  App is running on 127.0.0.1:${GUNICORN_PORT}"
echo ""
echo "  NEXT STEP — add the Nginx location blocks:"
echo "    sudo nano /etc/nginx/sites-available/misc.lmta.lt"
echo "    (paste the blocks from nginx/nginx-staging.conf)"
echo "    sudo nginx -t && sudo systemctl reload nginx"
echo ""
echo "  Then visit: https://misc.lmta.lt/journal"
echo ""
echo "  Service management:"
echo "    sudo systemctl status transact-staging-gunicorn"
echo "    sudo systemctl status transact-staging-celery"
echo "    sudo journalctl -u transact-staging-gunicorn -f"
echo "    tail -f ${APP_DIR}/logs/gunicorn-error.log"
echo "============================================================"
echo ""
