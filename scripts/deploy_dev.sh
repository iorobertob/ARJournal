#!/usr/bin/env bash
# Trans/Act Journal — development update script
#
# Run this after pulling new code to sync your local environment:
#   bash scripts/deploy_dev.sh
#
# First-time setup: use scripts/setup_dev.sh instead.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$APP_DIR/venv"

# ── Colours ───────────────────────────────────────────────────────────────────
BOLD=$(tput bold 2>/dev/null || true)
GREEN=$(tput setaf 2 2>/dev/null || true)
YELLOW=$(tput setaf 3 2>/dev/null || true)
RED=$(tput setaf 1 2>/dev/null || true)
RESET=$(tput sgr0 2>/dev/null || true)

step() { echo "${BOLD}${GREEN}▶  $*${RESET}"; }
warn() { echo "${YELLOW}⚠   $*${RESET}"; }
die()  { echo "${RED}✗   $*${RESET}" >&2; exit 1; }

cd "$APP_DIR"

# ── Preflight ─────────────────────────────────────────────────────────────────
[[ -f "manage.py" ]]    || die "manage.py not found — run from the repo root."
[[ -d "$VENV_DIR" ]]    || die "venv not found. Run scripts/setup_dev.sh first."
[[ -f ".env" ]]         || die ".env not found. Copy .env.example and fill it in."

source "$VENV_DIR/bin/activate"

# ── Dependencies ─────────────────────────────────────────────────────────────
step "Checking dependencies"
pip install -q --upgrade pip
# Only reinstall if requirements file is newer than the venv's pip cache stamp
REQ="requirements/development.txt"
STAMP="$VENV_DIR/.last_install"
if [[ ! -f "$STAMP" || "$REQ" -nt "$STAMP" ]]; then
  echo "  requirements/development.txt changed — reinstalling…"
  pip install -q -r "$REQ"
  touch "$STAMP"
else
  echo "  Requirements up to date."
fi

# ── Uncommitted model changes ─────────────────────────────────────────────────
step "Checking for missing migrations"
if ! python manage.py migrate --check --run-syncdb 2>/dev/null; then
  warn "Unapplied migrations detected."
elif python manage.py makemigrations --check --dry-run 2>/dev/null; then
  echo "  No new migrations needed."
else
  warn "Model changes detected without a migration file."
  warn "Run: python manage.py makemigrations"
fi

# ── Migrations ────────────────────────────────────────────────────────────────
step "Running migrations"
python manage.py migrate
echo "  Done."

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo "${BOLD}${GREEN}✓ Dev environment updated${RESET}"
echo ""
echo "  Start the server:"
echo "    source venv/bin/activate"
echo "    python manage.py runserver 0.0.0.0:5002"
echo ""
