# VPS Deployment Status — Wellona SMART

**Data:** 2025-11-20  
**VPS IP:** 46.202.189.159  
**OS:** Ubuntu 24.04 LTS  
**Location:** Lithuania (Vilnius)  
**Domain:** wellonapharm.com (jo aktiv ende, duhet DNS)

---

## 1. GJENDJA AKTUALE

### ✅ E KRYER
- [x] VPS i blerë dhe aktiv (Hostinger)
- [x] SSH access si root
- [x] Packages të instaluara: git, python3, python3-venv, nginx, postgresql, ufw
- [x] Firewall konfiguruar (SSH, HTTP, HTTPS)
- [x] Kodi i ngarkuar në `/opt/wellona/wphAI_deploy.zip` (307MB)
- [x] Python venv krijuar në `/opt/wellona/venv`
- [x] Dependencies Python instaluar (flask, gunicorn, pandas, openpyxl, psycopg2-binary, requests, python-dotenv)

### ⏳ NË PROCES (hapi tjetër)
- [ ] Unzip kodi në `/opt/wellona/wphAI/`
- [ ] PostgreSQL DB & user setup (`wph_ai_0262000`, role `wph_ai`)
- [ ] Systemd service për backend (`wellona_backend.service`)
- [ ] Nginx reverse proxy config
- [ ] DNS A records për `wellonapharm.com` → `46.202.189.159`
- [ ] HTTPS certbot (Let's Encrypt)

---

## 2. LIDHJET E DATABAZËS

### 2.1 VPS Database (e re, lokale në VPS)
```bash
Host: 127.0.0.1 (localhost në VPS)
Port: 5432
Database: wph_ai_0262000
User: wph_ai
Password: WellonaVPS2025!
```

**Purpose:** Shadow DB për operacionet e Wellona SMART në VPS. Izolohet nga ERP `ebdata`.

**Schemas:**
- `stg` (staging)
- `ref` (reference)
- `wph_core` (core logic)
- `audit` (audit trail)

**Setup Command (në VPS):**
```bash
sudo -u postgres psql -c "CREATE ROLE wph_ai LOGIN PASSWORD 'WellonaVPS2025!';"
sudo -u postgres psql -c "CREATE DATABASE wph_ai_0262000 OWNER wph_ai ENCODING 'UTF8' TEMPLATE template0;"
sudo -u postgres psql -d wph_ai_0262000 -c "CREATE SCHEMA stg; CREATE SCHEMA ref; CREATE SCHEMA wph_core; CREATE SCHEMA audit;"
```

---

### 2.2 ERP Database (legacy, në Lenovo lokale)
```bash
Host: 100.69.251.92 (Tailscale VPN, Lenovo local)
Port: 5432
Database: ebdata
User: postgresPedja (ose smart_pedja)
Password: supersqlpedja (ose wellona-server)
Version: PostgreSQL 9.3 (legacy)
```

**Purpose:** ERP production data (EasyBusiness). READ-ONLY përmes Foreign Data Wrapper (FDW).

**Access Method:**
- Nga Windows lokale: direkt përmes Tailscale IP
- Nga VPS: duhet Tailscale client në VPS ose SSH tunnel

**Foreign Tables (në `wph_ai` local):**
- `eb_fdw.artikli` (katalog)
- `eb_fdw.artiklikartica` (lëvizjet stoku)
- `eb_fdw.promet_artikala` (shitje)
- `eb_fdw.pos` (POS transactions)

**FDW Setup (lokale, jo në VPS ende):**
```sql
CREATE SERVER eb_fdw FOREIGN DATA WRAPPER postgres_fdw
  OPTIONS (host '100.69.251.92', port '5432', dbname 'ebdata');

CREATE USER MAPPING FOR postgres SERVER eb_fdw
  OPTIONS (user 'smart_pedja', password 'wellona-server');

IMPORT FOREIGN SCHEMA public
  LIMIT TO (artikli, artiklikartica, promet_artikala, pos)
  FROM SERVER eb_fdw INTO eb_fdw;
```

---

### 2.3 Windows Local Database (zhvillim)
```bash
Host: 127.0.0.1 (localhost në Lenovo)
Port: 5432
Database: wph_ai
User: postgres
Password: 0262000
Version: PostgreSQL 18
```

**Purpose:** Zhvillim dhe test lokal në Lenovo para se të deploy-ohet në VPS.

**Environment Variables (local):**
```powershell
$env:WPH_DB_HOST = '127.0.0.1'
$env:WPH_DB_PORT = '5432'
$env:WPH_DB_NAME = 'wph_ai'
$env:WPH_DB_USER = 'postgres'
$env:WPH_DB_PASS = '0262000'
$env:WPH_APP_USE_DB = '1'
```

---

## 3. RRUGA E DEPLOYMENT-IT

### Hapi 1: Unzip kodi në VPS
```bash
cd /opt/wellona
unzip -o wphAI_deploy.zip -d wphAI
```

### Hapi 2: Setup PostgreSQL në VPS
```bash
sudo -u postgres psql -c "CREATE ROLE wph_ai LOGIN PASSWORD 'WellonaVPS2025!';"
sudo -u postgres psql -c "CREATE DATABASE wph_ai_0262000 OWNER wph_ai ENCODING 'UTF8' TEMPLATE template0;"
sudo -u postgres psql -d wph_ai_0262000 -c "CREATE SCHEMA stg; CREATE SCHEMA ref; CREATE SCHEMA wph_core; CREATE SCHEMA audit;"
```

### Hapi 3: Systemd Service
```bash
cat >/etc/systemd/system/wellona_backend.service <<'EOF'
[Unit]
Description=Wellona Backend (Gunicorn)
After=network.target postgresql.service

[Service]
WorkingDirectory=/opt/wellona/wphAI
Environment=PYTHONPATH=/opt/wellona/wphAI
Environment=APP_PORT=8056
Environment=WPH_APP_USE_DB=1
Environment=WPH_DB_HOST=127.0.0.1
Environment=WPH_DB_PORT=5432
Environment=WPH_DB_NAME=wph_ai_0262000
Environment=WPH_DB_USER=wph_ai
Environment=WPH_DB_PASS=WellonaVPS2025!
ExecStart=/opt/wellona/venv/bin/gunicorn WPH_EFaktura_Package.backend.app_v2:app -b 127.0.0.1:8056 --workers 3 --timeout 120
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now wellona_backend
systemctl status wellona_backend --no-pager
```

### Hapi 4: Nginx Reverse Proxy
```bash
cat >/etc/nginx/sites-available/wellona <<'EOF'
server {
  listen 80;
  server_name _;
  
  location /static/ {
    alias /opt/wellona/wphAI/WPH_EFaktura_Package/backend/public/;
  }
  
  location / {
    proxy_pass http://127.0.0.1:8056;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Real-IP $remote_addr;
  }
}
EOF

ln -s /etc/nginx/sites-available/wellona /etc/nginx/sites-enabled/ || true
nginx -t && systemctl reload nginx
```

### Hapi 5: Test Backend
```bash
# Në VPS
curl -I http://127.0.0.1:8056/ui
curl -I http://localhost/ui
curl http://127.0.0.1:8056/api/health/db

# Nga browser (local)
# http://46.202.189.159/ui
```

### Hapi 6: DNS (në Hostinger Panel)
- Shko te DNS management për `wellonapharm.com`
- Add A record: `@` → `46.202.189.159`
- Add A record: `www` → `46.202.189.159`
- Prit 5-10 min për propagim

### Hapi 7: HTTPS (Let's Encrypt)
```bash
apt -y install certbot python3-certbot-nginx
certbot --nginx -d wellonapharm.com -d www.wellonapharm.com
```

---

## 4. ENVIRONMENT VARIABLES — PËRMBLEDHJE

### Në VPS (systemd service)
```bash
APP_PORT=8056
WPH_APP_USE_DB=1
WPH_DB_HOST=127.0.0.1
WPH_DB_PORT=5432
WPH_DB_NAME=wph_ai_0262000
WPH_DB_USER=wph_ai
WPH_DB_PASS=WellonaVPS2025!
PYTHONPATH=/opt/wellona/wphAI
```

### Në Windows Local (dev)
```powershell
$env:APP_PORT = '8056'
$env:WPH_APP_USE_DB = '1'
$env:WPH_DB_HOST = '127.0.0.1'
$env:WPH_DB_PORT = '5432'
$env:WPH_DB_NAME = 'wph_ai'
$env:WPH_DB_USER = 'postgres'
$env:WPH_DB_PASS = '0262000'
```

---

## 5. RRJETI DHE SIGURISË

### Firewall (VPS)
```bash
# UFW rules aktive
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

### PostgreSQL Access
- **VPS DB:** Bound vetëm në `127.0.0.1` (jo eksponim publik)
- **ERP DB:** E arritshme vetëm përmes Tailscale VPN (`100.69.251.92`)

### SSH Access
```bash
ssh root@46.202.189.159
# Password: [nga Hostinger email]
```

---

## 6. STRUKTURA E KODIT NË VPS

```
/opt/wellona/
├── venv/                    # Python virtual environment
│   └── bin/
│       ├── python
│       ├── pip
│       └── gunicorn
├── wphAI_deploy.zip        # Uploaded (307MB)
└── wphAI/                  # Unzip këtu (hapi tjetër)
    ├── WPH_EFaktura_Package/
    │   └── backend/
    │       ├── app_v2.py   # Main Flask app
    │       └── public/     # Static files (UI)
    ├── app/
    ├── bin/
    ├── configs/
    ├── docs/
    ├── logs/
    ├── scripts/
    └── ...
```

---

## 7. HAPAT E MBETURA (TO-DO)

### 7.1 Deployment Fillestar (VPS)
- [ ] Unzip kodi
- [ ] Setup DB schemas
- [ ] Start systemd service
- [ ] Configure nginx
- [ ] Test nga IP `http://46.202.189.159/ui`

### 7.2 Domain & HTTPS
- [ ] DNS A records
- [ ] Certbot HTTPS
- [ ] Test `https://wellonapharm.com/ui`

### 7.3 Data Migration (optional)
- [ ] Backup lokal: `pg_dump -Fc wph_ai > wph_ai_backup.dump`
- [ ] Transfer në VPS: `scp wph_ai_backup.dump root@46.202.189.159:/tmp/`
- [ ] Restore në VPS: `pg_restore -d wph_ai_0262000 /tmp/wph_ai_backup.dump`

### 7.4 Nightly ETL (VPS)
- [ ] Krijo cron job për ETL: `/etc/cron.d/wellona_etl`
  ```
  15 2 * * * root /opt/wellona/venv/bin/python /opt/wellona/wphAI/bin/wph_ai_orchestrator.py >> /opt/wellona/wphAI/logs/etl_cron.log 2>&1
  ```

### 7.5 Monitoring & Logs
- [ ] Setup logrotate për `/opt/wellona/wphAI/logs/`
- [ ] Monitor disk usage: `df -h`
- [ ] Monitor service status: `systemctl status wellona_backend`
- [ ] Tail logs: `journalctl -u wellona_backend -f`

---

## 8. REFERENCE COMMANDS

### Check Service Status
```bash
systemctl status wellona_backend
journalctl -u wellona_backend -f
```

### Restart Service
```bash
systemctl restart wellona_backend
```

### Check Nginx
```bash
nginx -t
systemctl status nginx
tail -f /var/log/nginx/access.log
```

### Check PostgreSQL
```bash
sudo -u postgres psql -d wph_ai_0262000 -c "SELECT current_database(), version();"
```

### Test Backend Endpoints
```bash
curl -I http://localhost:8056/ui
curl http://localhost:8056/api/health/db
curl http://localhost:8056/api/suppliers
```

---

## 9. KONTAKTE & CREDENTIALS

### VPS
- Provider: Hostinger
- IP: 46.202.189.159
- SSH User: root
- Password: [nga email i Hostinger-it]

### Domain
- Registrar: Hostinger
- Domain: wellonapharm.com
- Expires: 2027-05-02

### Database Passwords
- VPS DB (`wph_ai`): `WellonaVPS2025!`
- Local DB (`wph_ai`): `0262000`
- ERP DB (`ebdata`): `supersqlpedja` / `wellona-server`

---

**Përditësuar:** 2025-11-20 06:49 UTC  
**Status:** Hapi 1 përfunduar (packages + upload). Hapi 2 në pritje (unzip + DB setup).
