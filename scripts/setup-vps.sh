#!/usr/bin/env bash
# ReEngrave — First-time VPS setup
# Run as root on a fresh Ubuntu 22.04 / 24.04 server.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/YOURUSER/reengrave/main/scripts/setup-vps.sh | bash
#   -- or --
#   scp scripts/setup-vps.sh root@YOUR_SERVER_IP:~/ && ssh root@YOUR_SERVER_IP bash setup-vps.sh
#
# After this script finishes:
#   1. Clone your repo to /opt/reengrave
#   2. Fill in backend/.env.production
#   3. Set DOMAIN and ACME_EMAIL, then run scripts/deploy.sh

set -euo pipefail

REPO_DIR=/opt/reengrave

echo "==> Updating system packages"
apt-get update -q && apt-get upgrade -y -q

echo "==> Installing Docker"
if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | sh
fi

echo "==> Installing Docker Compose plugin"
apt-get install -y docker-compose-plugin

echo "==> Installing utilities"
apt-get install -y git curl ufw fail2ban

echo "==> Configuring firewall (UFW)"
ufw --force enable
ufw allow ssh
ufw allow http
ufw allow https
echo "UFW status:"
ufw status

echo "==> Creating deploy user (deploy)"
if ! id deploy &>/dev/null; then
  useradd -m -s /bin/bash deploy
  usermod -aG docker deploy
  mkdir -p /home/deploy/.ssh
  # Copy root's authorized_keys so your SSH key works for deploy user too
  if [ -f /root/.ssh/authorized_keys ]; then
    cp /root/.ssh/authorized_keys /home/deploy/.ssh/authorized_keys
    chown -R deploy:deploy /home/deploy/.ssh
    chmod 700 /home/deploy/.ssh
    chmod 600 /home/deploy/.ssh/authorized_keys
  fi
fi

echo "==> Creating app directory"
mkdir -p "$REPO_DIR"
chown deploy:deploy "$REPO_DIR"

echo ""
echo "===================================================="
echo "Server setup complete!"
echo ""
echo "Next steps:"
echo "  1. Clone your repo:"
echo "     git clone https://github.com/YOURUSER/reengrave.git $REPO_DIR"
echo ""
echo "  2. Create the production env file:"
echo "     cp $REPO_DIR/backend/.env.production.example $REPO_DIR/backend/.env.production"
echo "     nano $REPO_DIR/backend/.env.production"
echo ""
echo "  3. Set your domain + email, then deploy:"
echo "     export DOMAIN=yourdomain.com"
echo "     export ACME_EMAIL=you@yourdomain.com"
echo "     cd $REPO_DIR && bash scripts/deploy.sh"
echo "===================================================="
