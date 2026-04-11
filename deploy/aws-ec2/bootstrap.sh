#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

APP_USER="${APP_USER:-ubuntu}"
APP_GROUP="${APP_GROUP:-${APP_USER}}"
APP_DIR="${APP_DIR:-/home/${APP_USER}/autoreport}"
APP_HOST="${APP_HOST:-127.0.0.1}"
APP_PORT="${APP_PORT:-8000}"
APP_WORKERS="${APP_WORKERS:-2}"
SERVER_NAME="${SERVER_NAME:-_}"
CLIENT_MAX_BODY_SIZE="${CLIENT_MAX_BODY_SIZE:-25M}"

if [[ ! -d "${APP_DIR}" ]]; then
  echo "App directory not found: ${APP_DIR}" >&2
  echo "Clone the repo to ${APP_DIR} or override APP_DIR before running." >&2
  exit 1
fi

echo "Installing Ubuntu packages..."
sudo apt update
sudo apt install -y python3-venv python3-pip nginx

echo "Creating virtualenv and installing autoreport..."
cd "${APP_DIR}"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .

echo "Rendering systemd unit..."
sed \
  -e "s|__APP_USER__|${APP_USER}|g" \
  -e "s|__APP_GROUP__|${APP_GROUP}|g" \
  -e "s|__APP_DIR__|${APP_DIR}|g" \
  -e "s|__APP_HOST__|${APP_HOST}|g" \
  -e "s|__APP_PORT__|${APP_PORT}|g" \
  -e "s|__APP_WORKERS__|${APP_WORKERS}|g" \
  "${REPO_ROOT}/deploy/aws-ec2/autoreport.service" | sudo tee /etc/systemd/system/autoreport.service >/dev/null

echo "Rendering nginx site..."
sed \
  -e "s|__SERVER_NAME__|${SERVER_NAME}|g" \
  -e "s|__APP_HOST__|${APP_HOST}|g" \
  -e "s|__APP_PORT__|${APP_PORT}|g" \
  -e "s|__CLIENT_MAX_BODY_SIZE__|${CLIENT_MAX_BODY_SIZE}|g" \
  "${REPO_ROOT}/deploy/aws-ec2/nginx-autoreport.conf" | sudo tee /etc/nginx/sites-available/autoreport >/dev/null

sudo ln -sf /etc/nginx/sites-available/autoreport /etc/nginx/sites-enabled/autoreport
if [[ -f /etc/nginx/sites-enabled/default ]]; then
  sudo rm -f /etc/nginx/sites-enabled/default
fi

echo "Reloading services..."
sudo systemctl daemon-reload
sudo systemctl enable --now autoreport
sudo nginx -t
sudo systemctl enable nginx >/dev/null
if sudo systemctl is-active --quiet nginx; then
  sudo systemctl reload nginx
else
  sudo systemctl start nginx
fi

echo
echo "Autoreport deployment bootstrap completed."
echo "Health check: curl http://${APP_HOST}:${APP_PORT}/healthz"
echo "Service logs: journalctl -u autoreport -f"
echo "Public test: open http://<EC2-PUBLIC-IP>/ after security group allows 80/tcp"
