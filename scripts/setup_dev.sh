#!/usr/bin/env bash
# Trans/Act Journal — one-command dev setup (without Docker)
set -e

echo "=== Trans/Act Journal — Dev Setup ==="

# Check Python
python3 -c "import sys; assert sys.version_info >= (3, 11), 'Python 3.11+ required'" 2>/dev/null || {
  echo "ERROR: Python 3.11+ is required."
  exit 1
}

# Virtual env
if [ ! -d "venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv venv
fi

source venv/bin/activate
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements/development.txt

# .env
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo ""
  echo "NOTE: .env created from .env.example."
  echo "  Please edit .env to set your DB credentials and SECRET_KEY."
  echo ""
fi

# Read DB config from .env
DB_NAME=$(grep '^DB_NAME=' .env | cut -d= -f2 | tr -d ' ')
DB_USER=$(grep '^DB_USER=' .env | cut -d= -f2 | tr -d ' ')
DB_PASSWORD=$(grep '^DB_PASSWORD=' .env | cut -d= -f2 | tr -d ' ')
DB_NAME=${DB_NAME:-transact_journal}
DB_USER=${DB_USER:-transact}
DB_PASSWORD=${DB_PASSWORD:-devpassword}

# Create PostgreSQL role and database if they don't exist
echo "Setting up PostgreSQL database..."
psql postgres -c "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" 2>/dev/null | grep -q 1 || \
  psql postgres -c "CREATE ROLE ${DB_USER} WITH LOGIN PASSWORD '${DB_PASSWORD}';" 2>/dev/null && \
  echo "  Role '${DB_USER}' ready."

psql postgres -c "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" 2>/dev/null | grep -q 1 || \
  psql postgres -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};" 2>/dev/null && \
  echo "  Database '${DB_NAME}' ready."

# Grant privileges
psql postgres -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};" 2>/dev/null || true

# Run migrations
echo "Running migrations..."
python manage.py migrate

# Create superuser if not exists
echo "Creating superuser..."
_SU_EMAIL=$(grep '^DJANGO_SUPERUSER_EMAIL=' .env | cut -d= -f2 | tr -d ' ')
_SU_PASSWORD=$(grep '^DJANGO_SUPERUSER_PASSWORD=' .env | cut -d= -f2 | tr -d ' ')
export DJANGO_SUPERUSER_EMAIL="${_SU_EMAIL:-admin@trans-act-journal.org}"
export DJANGO_SUPERUSER_PASSWORD="${_SU_PASSWORD:-changeme123}"

python manage.py shell -c "
from apps.accounts.models import User
import os
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@trans-act-journal.org')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'changeme123')
if not User.objects.filter(email=email).exists():
    User.objects.create_superuser(
        email=email,
        password=password,
        first_name='Admin',
        last_name='User',
    )
    print('Superuser created:', email)
else:
    print('Superuser already exists:', email)
" || echo "Superuser setup skipped (check .env)"

# Create initial journal config
echo "Seeding journal config..."
python manage.py shell -c "
from apps.journal.models import JournalConfig
j = JournalConfig.get()
if not j.name or j.name == 'Trans/Act':
    j.name = 'Trans/Act'
    j.tagline = 'A journal for artistic research'
    j.submission_open = True
    j.save()
    print('Journal config ready.')
" 2>/dev/null || echo "Journal config seed skipped."

echo ""
echo "=== Setup complete! ==="
echo ""
echo "Run the development server:"
echo "  source venv/bin/activate"
echo "  python manage.py runserver 0.0.0.0:5002"
echo ""
echo "Admin panel:  http://localhost:5002/admin/"
echo "Journal site: http://localhost:5002/"
echo ""
