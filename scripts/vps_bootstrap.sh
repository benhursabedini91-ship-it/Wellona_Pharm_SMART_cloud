#!/usr/bin/env bash
set -euo pipefail

# Wellona SMART — Ubuntu VPS bootstrap
# Usage: sudo bash vps_bootstrap.sh

export DEBIAN_FRONTEND=noninteractive
apt update && apt -y upgrade
apt -y install git python3 python3-venv python3-pip nginx postgresql postgresql-contrib ufw

ufw allow OpenSSH || true
ufw allow 80 || true
ufw allow 443 || true
ufw --force enable || true

mkdir -p /opt/wellona && cd /opt/wellona
python3 -m venv /opt/wellona/venv
/opt/wellona/venv/bin/pip install --upgrade pip wheel
/opt/wellona/venv/bin/pip install flask waitress gunicorn pandas openpyxl psycopg2-binary requests python-dotenv

# Postgres minimal
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='wph_ai'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE ROLE wph_ai LOGIN PASSWORD 'ChangeMeStrong!';"
sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw wph_ai_0262000 || \
  sudo -u postgres psql -c "CREATE DATABASE wph_ai_0262000 OWNER wph_ai ENCODING 'UTF8' TEMPLATE template0;"
sudo -u postgres psql -d wph_ai_0262000 -c "CREATE SCHEMA IF NOT EXISTS stg; CREATE SCHEMA IF NOT EXISTS ref; CREATE SCHEMA IF NOT EXISTS wph_core; CREATE SCHEMA IF NOT EXISTS audit;"

echo "Bootstrap done. Copy repo to /opt/wellona/wphAI and configure systemd/nginx as per DEPLOY_VPS_GUIDE.md"