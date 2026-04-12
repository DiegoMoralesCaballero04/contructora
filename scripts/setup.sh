#!/usr/bin/env bash
# ============================================================
# CONSTRUTECH-IA — First-time setup script
# Run from anywhere:  bash construtech-ia/scripts/setup.sh
# ============================================================
set -e

# ── Resolve project root (parent of scripts/) ───────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== CONSTRUTECH-IA Setup ==="
echo "Project directory: $PROJECT_DIR"
echo ""

cd "$PROJECT_DIR"

# 1. Copy .env ────────────────────────────────────────────────
if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    cp .env.example .env
    echo "✓ .env created from .env.example — EDIT IT with your credentials before continuing."
    echo ""
    echo "  Open .env, fill in your values, then re-run this script."
    exit 0
  else
    echo "✗ .env.example not found. Cannot create .env."
    exit 1
  fi
else
  echo "✓ .env already exists"
fi

# ── Helper: pull an image with retries ──────────────────────
pull_with_retry() {
  local IMAGE="$1"
  local MAX_RETRIES=5
  local RETRY_DELAY=10

  echo "  Pulling $IMAGE ..."
  for attempt in $(seq 1 $MAX_RETRIES); do
    if docker pull "$IMAGE"; then
      echo "  ✓ $IMAGE ready"
      return 0
    fi
    if [ "$attempt" -lt "$MAX_RETRIES" ]; then
      echo "  ✗ Pull failed (attempt $attempt/$MAX_RETRIES). Retrying in ${RETRY_DELAY}s..."
      sleep "$RETRY_DELAY"
      RETRY_DELAY=$((RETRY_DELAY * 2))
    fi
  done

  echo "  ✗ Could not pull $IMAGE after $MAX_RETRIES attempts."
  echo "    If the error is 'dial tcp ... connectex', Docker Hub CDN is unreachable from your network."
  echo "    Make sure C:\\Users\\ADiego\\AppData\\Roaming\\Docker\\daemon.json exists with registry-mirrors"
  echo "    and restart Docker Desktop, then re-run this script."
  return 1
}

# 2. Pre-pull all external images with retry ─────────────────
# nginx:alpine is pulled here explicitly so the local build step (docker/nginx/Dockerfile)
# can use the cached image instead of hitting Docker Hub during `docker compose build`.
echo ""
echo "Pulling external Docker images (with retry on network errors)..."
pull_with_retry "nginx:alpine"
pull_with_retry "postgres:16"
pull_with_retry "mongo:7"
pull_with_retry "redis:7-alpine"
pull_with_retry "ollama/ollama:latest"
pull_with_retry "n8nio/n8n:latest"

# 3. Build custom services (including nginx which builds locally from nginx:alpine) ──
echo ""
echo "Building custom Docker images..."
docker compose build django celery-worker celery-beat nginx

# 4. Start all services ───────────────────────────────────────
echo ""
echo "Starting all services..."
docker compose up -d --pull never

# 5. Wait for postgres to be ready ────────────────────────────
echo ""
echo "Waiting for PostgreSQL to be ready..."
RETRIES=20
until docker compose exec -T postgres pg_isready -q 2>/dev/null; do
  RETRIES=$((RETRIES - 1))
  if [ $RETRIES -le 0 ]; then
    echo "✗ PostgreSQL did not become ready in time."
    exit 1
  fi
  echo "  ...still waiting ($RETRIES retries left)"
  sleep 3
done
echo "✓ PostgreSQL is ready"

# 6. Wait for django container to finish migrations ───────────
echo ""
echo "Waiting for Django to finish startup (migrations + collectstatic)..."
sleep 15

# 7. Create superuser (interactive) ──────────────────────────
echo ""
echo "Create Django superuser (skip with Ctrl+C if already created):"
docker compose exec django python manage.py createsuperuser || true

# 8. Pull Ollama model ────────────────────────────────────────
echo ""
read -r -p "Pull Ollama model llama3.2:3b (~2 GB)? [y/N] " pull_ollama
if [[ "$pull_ollama" =~ ^[Yy]$ ]]; then
  docker compose exec ollama ollama pull llama3.2:3b
  echo "✓ Ollama model ready"
else
  echo "  Skipped. Pull later with: docker compose exec ollama ollama pull llama3.2:3b"
fi

# 9. Done ──────────────────────────────────────────────────────
echo ""
echo "=== Setup complete! ==="
echo ""
echo "  Portal:        http://localhost/portal/"
echo "  Django admin:  http://localhost/admin/"
echo "  API docs:      http://localhost/api/docs/"
echo "  n8n:           http://localhost:5678"
echo ""
echo "Next steps:"
echo "  1. Check .env — add AWS S3, email, and Telegram credentials if needed"
echo "  2. Import n8n workflows from n8n/workflows/"
echo "  3. First scraping