#!/usr/bin/env bash
# Provision a fresh DigitalOcean droplet (Ubuntu 24.04) for distrebute.com.
# Run as root once after creating the droplet:
#   ssh root@<droplet-ip> 'bash -s' < provision.sh
set -euo pipefail

echo "═══ Updating system ═══"
apt-get update && apt-get upgrade -y
apt-get install -y curl ufw git fail2ban unattended-upgrades

echo "═══ Installing Docker ═══"
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker

echo "═══ Installing Caddy (TLS auto from Let's Encrypt) ═══"
apt-get install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
apt-get update
apt-get install -y caddy

echo "═══ Firewall (UFW) — allow only SSH + HTTP + HTTPS ═══"
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "═══ Create distrebute user + project layout ═══"
useradd -m -s /bin/bash -G docker distrebute || true
mkdir -p /opt/distrebute
chown distrebute:distrebute /opt/distrebute

echo "═══ Auto-update OS security patches ═══"
dpkg-reconfigure -plow unattended-upgrades || true

echo ""
echo "═══ NEXT STEPS ═══"
echo "1. SSH as distrebute user: ssh distrebute@<droplet-ip>"
echo "2. git clone <your-repo> /opt/distrebute"
echo "3. cd /opt/distrebute"
echo "4. cp infra/digitalocean/.env.production.example .env.production"
echo "5. nano .env.production  (fill in secrets — see comments)"
echo "6. sudo cp infra/digitalocean/Caddyfile /etc/caddy/Caddyfile"
echo "7. sudo systemctl restart caddy"
echo "8. docker compose -f docker-compose.yml -f docker-compose.gap.yml --env-file .env.production up -d"
