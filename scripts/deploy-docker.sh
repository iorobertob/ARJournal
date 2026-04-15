#!/usr/bin/env bash
# Trans/Act Journal — DOCKER production deploy script
# Target: https://journal.lmta.lt  (Docker Compose, Nginx on host)
# Tested on Ubuntu 22.04 LTS / Debian 12
#
# Usage (first deploy):
#   sudo bash scripts/deploy-docker.sh
#
# Usage (update — rebuild images, re-run migrations, reload):
#   sudo bash scripts/deploy-docker.sh --update
#
# Architecture:
#   - PostgreSQL, Redis, Gunicorn, Celery → inside Docker containers
#   - Nginx + Certbot → on the HOST (handles SSL, serves /media/ directly)
#   - Media files → bind-mounted at /opt/transact-docker/media (host + container share it)
#   - Static files → served by WhiteNoise inside the app container
#   - App port 5002 exposed on 127.0.0.1 only; Nginx proxies to it
#
set -euo pipefail

APP_DIR="/opt/transact-docker"
DOMAIN="journal.lmta.lt"
COMPOSE_FILE="docker-compose.prod.yml"

UPDATE_ONLY=false
[[ "${1:-}" == "--update" ]] && UPDATE_ONLY=true

if [[ $EUID -ne 0 ]]; then
  echo "ERROR: Run with sudo."
  exit 1
fi

log() { echo ""; echo "==> $*"; }

# ── 1. System packages (host: Nginx, Certbot, Docker) ─────────────────────────
if ! $UPDATE_ONLY; then
  log "Installing host dependencies (Nginx, Certbot, Docker)..."
  apt-get update -q
  apt-get install -y --no-install-recommends \
    nginx certbot python3-certbot-nginx \
    curl git ca-certificates gnupg

  # Docker (official repo)
  if ! command -v docker &>/dev/null; then
    log "Installing Docker..."
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
      | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
      https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
      | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update -q
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    systemctl enable --now docker
  fi
fi

# ── 2. App directory ──────────────────────────────────────────────────────────
if ! $UPDATE_ONLY; then
  log "Creating app directory..."
  mkdir -p "$APP_DIR"
fi

# ── 3. Clone or pull ──────────────────────────────────────────────────────────
if [ ! -d "$APP_DIR/.git" ]; then
  echo ""
  echo "ERROR: $APP_DIR is not a git repository."
  echo "  Clone the repo first: git clone <repo> $APP_DIR"
  echo "  Then re-run with --update"
  exit 1
fi
log "Pulling latest code..."
git -C "$APP_DIR" pull

# ── 4. .env file ─────────────────────────────────────────────────────────────
if [ ! -f "$APP_DIR/.env" ]; then
  cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  chmod 640 "$APP_DIR/.env"
  echo ""
  echo "  IMPORTANT: $APP_DIR/.env was created from .env.example."
  echo "  Edit it with your production values:"
  echo ""
  echo "    nano $APP_DIR/.env"
  echo ""
  echo "  Required fields:"
  echo "    DEBUG=False"
  echo "    SECRET_KEY=<50+ random chars>"
  echo "    DJANGO_SETTINGS_MODULE=config.settings.production"
  echo "    ALLOWED_HOSTS=${DOMAIN},www.${DOMAIN}"
  echo "    CSRF_TRUSTED_ORIGINS=https://${DOMAIN},https://www.${DOMAIN}"
  echo "    SITE_URL=https://${DOMAIN}"
  echo "    DB_NAME=transact_journal, DB_USER=transact, DB_PASSWORD=<strong>"
  echo "    DB_HOST=db  (Docker service name — NOT localhost)"
  echo "    CELERY_BROKER_URL=redis://redis:6379/0"
  echo "    CELERY_TASK_ALWAYS_EAGER=False"
  echo "    ANYMAIL_BACKEND + API key"
  echo "    DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_PASSWORD"
  echo ""
  echo "  NOTE: DB_HOST must be 'db' (the Docker service name), not localhost."
  echo ""
  read -rp "  Press Enter after editing .env to continue..." _
fi

# ── 5. Media directory on host (shared with container via bind mount) ──────────
log "Creating media directory on host..."
mkdir -p "$APP_DIR/media"
# Docker runs as root inside the container — ensure directory is writable
chmod 777 "$APP_DIR/media"

# ── 6. Build and start containers ─────────────────────────────────────────────
log "Building Docker images..."
docker compose -f "$APP_DIR/$COMPOSE_FILE" build

log "Starting containers..."
docker compose -f "$APP_DIR/$COMPOSE_FILE" up -d

# Wait for db to be healthy
log "Waiting for database..."
sleep 5

# ── 7. Django migrate + collectstatic ─────────────────────────────────────────
log "Running Django migrations..."
docker compose -f "$APP_DIR/$COMPOSE_FILE" exec -T app \
  python manage.py migrate --noinput

log "Collecting static files..."
docker compose -f "$APP_DIR/$COMPOSE_FILE" exec -T app \
  python manage.py collectstatic --noinput

# ── 8. Superuser (first deploy only) ──────────────────────────────────────────
if ! $UPDATE_ONLY; then
  SU_EMAIL=$(grep '^DJANGO_SUPERUSER_EMAIL=' "$APP_DIR/.env" | cut -d= -f2 | tr -d ' ')
  SU_PASS=$(grep '^DJANGO_SUPERUSER_PASSWORD=' "$APP_DIR/.env" | cut -d= -f2 | tr -d ' ')

  docker compose -f "$APP_DIR/$COMPOSE_FILE" exec -T app python manage.py shell -c "
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

  docker compose -f "$APP_DIR/$COMPOSE_FILE" exec -T app python manage.py shell -c "
from apps.journal.models import JournalConfig
j = JournalConfig.get()
if not j.name:
    j.name = 'Trans/Act'; j.tagline = 'A journal for artistic research'
    j.submission_open = True; j.save(); print('Journal config seeded.')
"
fi

# ── 9. Nginx on host ──────────────────────────────────────────────────────────
log "Deploying Nginx config..."
cp "$APP_DIR/nginx/nginx-docker.conf" /etc/nginx/sites-available/transact
ln -sf /etc/nginx/sites-available/transact /etc/nginx/sites-enabled/transact
rm -f /etc/nginx/sites-enabled/default
nginx -t

# ── 10. SSL via Let's Encrypt ─────────────────────────────────────────────────
if ! $UPDATE_ONLY; then
  log "Obtaining SSL certificate..."
  SU_EMAIL=$(grep '^DJANGO_SUPERUSER_EMAIL=' "$APP_DIR/.env" | cut -d= -f2 | tr -d ' ')
  # Start temporary HTTP server for ACME challenge before app is fully up
  systemctl start nginx || true
  certbot --nginx -d "$DOMAIN" -d "www.$DOMAIN" --non-interactive --agree-tos \
    --email "${SU_EMAIL:-admin@journal.lmta.lt}" \
    || echo "  WARNING: certbot failed — check DNS and re-run: sudo certbot --nginx -d $DOMAIN"
fi

# ── 11. Reload Nginx ──────────────────────────────────────────────────────────
systemctl enable --now nginx
systemctl reload nginx

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "============================================================"
echo "  Trans/Act Journal (Docker) deployed."
echo ""
echo "  Site:   https://$DOMAIN"
echo "  Admin:  https://$DOMAIN/admin/"
echo ""
echo "  Docker management:"
echo "    docker compose -f $APP_DIR/$COMPOSE_FILE ps"
echo "    docker compose -f $APP_DIR/$COMPOSE_FILE logs -f app"
echo "    docker compose -f $APP_DIR/$COMPOSE_FILE logs -f celery"
echo "    docker compose -f $APP_DIR/$COMPOSE_FILE restart app"
echo ""
echo "  Update workflow:"
echo "    cd $APP_DIR && git pull"
echo "    sudo bash scripts/deploy-docker.sh --update"
echo "============================================================"
echo ""
