#!/usr/bin/env bash
# Trans/Act Journal — PRODUCTION bare-metal deploy script
# Target: https://journal.lmta.lt  (own subdomain, no Docker)
# Tested on Ubuntu 22.04 LTS / Debian 12
#
# Usage (first deploy):
#   sudo bash scripts/deploy.sh
#
# Usage (update — skip system packages, user creation, SSL):
#   sudo bash scripts/deploy.sh --update
#
set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────────
APP_DIR="/opt/transact"
APP_USER="transact"
REPO_URL=""                         # e.g. git@github.com:org/journal.git
DOMAIN="journal.lmta.lt"
DJANGO_SETTINGS="config.settings.production"
GUNICORN_PORT=5002
GUNICORN_WORKERS=3                  # 2 × CPU cores + 1
# ─────────────────────────────────────────────────────────────────────────────

UPDATE_ONLY=false
[[ "${1:-}" == "--update" ]] && UPDATE_ONLY=true

if [[ $EUID -ne 0 ]]; then
  echo "ERROR: Run with sudo."
  exit 1
fi

log() { echo ""; echo "==> $*"; }

# ── 1. System packages ────────────────────────────────────────────────────────
if ! $UPDATE_ONLY; then
  log "Installing system packages..."
  apt-get update -q
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

# ── 2. App user and directory ─────────────────────────────────────────────────
if ! $UPDATE_ONLY; then
  log "Creating app user and directory..."
  id "$APP_USER" &>/dev/null || useradd --system --home "$APP_DIR" --shell /bin/bash "$APP_USER"
  mkdir -p "$APP_DIR"
  chown "$APP_USER:$APP_USER" "$APP_DIR"
fi

# ── 3. Clone or pull ──────────────────────────────────────────────────────────
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
  echo "  IMPORTANT: $APP_DIR/.env was created from .env.example."
  echo "  Edit it now with your production values:"
  echo ""
  echo "    sudo nano $APP_DIR/.env"
  echo ""
  echo "  Required fields:"
  echo "    DEBUG=False"
  echo "    SECRET_KEY=<50+ random chars — python -c 'import secrets; print(secrets.token_hex(50))'>"
  echo "    DJANGO_SETTINGS_MODULE=config.settings.production"
  echo "    ALLOWED_HOSTS=${DOMAIN},www.${DOMAIN}"
  echo "    CSRF_TRUSTED_ORIGINS=https://${DOMAIN},https://www.${DOMAIN}"
  echo "    SITE_URL=https://${DOMAIN}"
  echo "    DB_NAME=transact_journal, DB_USER=transact, DB_PASSWORD=<strong>, DB_HOST=localhost"
  echo "    CELERY_BROKER_URL=redis://localhost:6379/0"
  echo "    CELERY_TASK_ALWAYS_EAGER=False"
  echo "    ANYMAIL_BACKEND + API key"
  echo "    DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_PASSWORD"
  echo ""
  read -rp "  Press Enter after editing .env to continue..." _
fi

# ── 5. Python virtual environment ─────────────────────────────────────────────
log "Setting up Python virtual environment..."
if [ ! -d "$APP_DIR/venv" ]; then
  sudo -u "$APP_USER" python3.11 -m venv "$APP_DIR/venv"
fi
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -q --upgrade pip
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -q -r "$APP_DIR/requirements/production.txt"
log "Python dependencies installed."

# ── 6. Database ───────────────────────────────────────────────────────────────
if ! $UPDATE_ONLY; then
  log "Setting up PostgreSQL..."
  DB_NAME=$(grep '^DB_NAME=' "$APP_DIR/.env" | cut -d= -f2 | tr -d ' ')
  DB_USER=$(grep '^DB_USER=' "$APP_DIR/.env" | cut -d= -f2 | tr -d ' ')
  DB_PASS=$(grep '^DB_PASSWORD=' "$APP_DIR/.env" | cut -d= -f2 | tr -d ' ')
  DB_NAME="${DB_NAME:-transact_journal}"
  DB_USER="${DB_USER:-transact}"

  systemctl enable --now postgresql

  sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE ROLE ${DB_USER} WITH LOGIN PASSWORD '${DB_PASS}';"

  sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"

  sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"
fi

# ── 7. Directories ────────────────────────────────────────────────────────────
log "Creating directories..."
mkdir -p "$APP_DIR/media" "$APP_DIR/staticfiles" "$APP_DIR/logs"
chown -R "$APP_USER:$APP_USER" "$APP_DIR/media" "$APP_DIR/staticfiles" "$APP_DIR/logs"

# ── 8. migrate + collectstatic ────────────────────────────────────────────────
log "Running Django migrations..."
sudo -u "$APP_USER" env DJANGO_SETTINGS_MODULE="$DJANGO_SETTINGS" \
  "$APP_DIR/venv/bin/python" "$APP_DIR/manage.py" migrate --noinput

log "Collecting static files..."
sudo -u "$APP_USER" env DJANGO_SETTINGS_MODULE="$DJANGO_SETTINGS" \
  "$APP_DIR/venv/bin/python" "$APP_DIR/manage.py" collectstatic --noinput

# ── 9. Systemd: Gunicorn ──────────────────────────────────────────────────────
log "Writing systemd unit: transact-gunicorn.service..."
cat > /etc/systemd/system/transact-gunicorn.service << EOF
[Unit]
Description=Trans/Act Journal — Gunicorn WSGI server
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

# ── 10. Systemd: Celery worker ────────────────────────────────────────────────
log "Writing systemd unit: transact-celery.service..."
cat > /etc/systemd/system/transact-celery.service << EOF
[Unit]
Description=Trans/Act Journal — Celery worker (async PDF export)
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
    --concurrency=2
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# ── 11. Systemd: Celery Beat ──────────────────────────────────────────────────
log "Writing systemd unit: transact-celerybeat.service..."
cat > /etc/systemd/system/transact-celerybeat.service << EOF
[Unit]
Description=Trans/Act Journal — Celery Beat scheduler
After=network.target redis.service

[Service]
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
Environment=DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS}
ExecStart=${APP_DIR}/venv/bin/celery \\
    -A config.celery beat \\
    --loglevel=info \\
    --logfile=${APP_DIR}/logs/celerybeat.log \\
    --scheduler django_celery_beat.schedulers:DatabaseScheduler
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# ── 12. Nginx ─────────────────────────────────────────────────────────────────
log "Deploying Nginx config..."
cp "$APP_DIR/nginx/nginx-production.conf" /etc/nginx/sites-available/transact
ln -sf /etc/nginx/sites-available/transact /etc/nginx/sites-enabled/transact
rm -f /etc/nginx/sites-enabled/default
nginx -t

# ── 13. SSL via Let's Encrypt ─────────────────────────────────────────────────
if ! $UPDATE_ONLY; then
  log "Obtaining SSL certificate (Let's Encrypt)..."
  SU_EMAIL=$(grep '^DJANGO_SUPERUSER_EMAIL=' "$APP_DIR/.env" | cut -d= -f2 | tr -d ' ')
  certbot --nginx -d "$DOMAIN" -d "www.$DOMAIN" --non-interactive --agree-tos \
    --email "${SU_EMAIL:-admin@journal.lmta.lt}" \
    || echo "  WARNING: certbot failed — check DNS and re-run: sudo certbot --nginx -d $DOMAIN"
fi

# ── 14. Enable and start services ─────────────────────────────────────────────
log "Starting services..."
systemctl enable --now redis-server
systemctl daemon-reload
systemctl enable --now transact-gunicorn
systemctl enable --now transact-celery
systemctl enable --now transact-celerybeat
systemctl reload nginx

# ── 15. Superuser (first deploy only) ─────────────────────────────────────────
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

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "============================================================"
echo "  Trans/Act Journal (production) deployed."
echo ""
echo "  Site:   https://$DOMAIN"
echo "  Admin:  https://$DOMAIN/admin/"
echo ""
echo "  Service management:"
echo "    sudo systemctl status transact-gunicorn"
echo "    sudo systemctl status transact-celery"
echo "    sudo journalctl -u transact-gunicorn -f"
echo "    tail -f $APP_DIR/logs/gunicorn-error.log"
echo "    tail -f $APP_DIR/logs/celery.log"
echo "============================================================"
echo ""
