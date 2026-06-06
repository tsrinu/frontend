#!/usr/bin/env bash
# Pull latest, restart services, prune. Run on the droplet as the distrebute user.
set -euo pipefail

cd /opt/distrebute

echo "═══ Pulling latest code + images ═══"
git pull --ff-only
docker compose -f docker-compose.yml -f docker-compose.gap.yml --env-file .env.production pull

echo "═══ Restarting services ═══"
docker compose -f docker-compose.yml -f docker-compose.gap.yml --env-file .env.production up -d --remove-orphans

echo "═══ Health check (give services 10s to settle) ═══"
sleep 10
for p in 8001 8002 8012 8013 8014 8015 8016; do
  if curl -sf --max-time 3 "http://127.0.0.1:$p/healthz" > /dev/null; then
    echo "  ✓ port $p"
  else
    echo "  ✗ port $p — check 'docker compose logs'"
  fi
done

echo "═══ Pruning old images ═══"
docker system prune -f --volumes=false

echo ""
echo "Deploy complete. Check live at https://api.distrebute.com/.well-known/jwks.json"
