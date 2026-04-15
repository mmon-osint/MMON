#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# MMON — VM0 (Backend) Provisioning Script
# Target OS: Debian 12 Bookworm
# Installa: Python 3.12, FastAPI, PostgreSQL 16, Redis 7,
#           Apache2, PHP 8.x, Ollama (qwen2.5:14b)
# ─────────────────────────────────────────────────────────────
set -euo pipefail

# ── Colori ──
RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }

# ── Root check ──
[[ $EUID -ne 0 ]] && fail "Esegui come root: sudo bash $0"

info "═══════════════════════════════════════════════════"
info " MMON — VM0 Backend Provisioning (Debian 12)"
info "═══════════════════════════════════════════════════"

# ── 1. Prerequisiti OS ──
info "Aggiornamento sistema..."
apt-get update -qq && apt-get upgrade -y -qq
apt-get install -y -qq \
    curl wget gnupg2 lsb-release ca-certificates apt-transport-https \
    software-properties-common build-essential git unzip jq \
    libpq-dev libffi-dev libssl-dev
ok "Dipendenze base installate"

# ── 2. Python 3.12 ──
info "Installazione Python 3.12..."
if ! command -v python3.12 &>/dev/null; then
    # Debian 12 ha Python 3.11 di default — aggiungiamo deadsnakes-style build
    apt-get install -y -qq python3 python3-pip python3-venv python3-dev
    # Se 3.12 non disponibile in repo, compiliamo da sorgente
    if ! python3 --version 2>&1 | grep -q "3.12"; then
        warn "Python 3.12 non in repo, compilazione da sorgente..."
        cd /tmp
        wget -q "https://www.python.org/ftp/python/3.12.7/Python-3.12.7.tgz"
        tar xzf Python-3.12.7.tgz
        cd Python-3.12.7
        ./configure --enable-optimizations --prefix=/usr/local 2>&1 | tail -1
        make -j"$(nproc)" 2>&1 | tail -1
        make altinstall
        ln -sf /usr/local/bin/python3.12 /usr/local/bin/python3
        ln -sf /usr/local/bin/pip3.12 /usr/local/bin/pip3
        cd /tmp && rm -rf Python-3.12.7*
    fi
fi
ok "Python $(python3 --version 2>&1)"

# ── 3. PostgreSQL 16 ──
info "Installazione PostgreSQL 16..."
if ! command -v psql &>/dev/null; then
    echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list
    curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /etc/apt/trusted.gpg.d/pgdg.gpg
    apt-get update -qq
    apt-get install -y -qq postgresql-16 postgresql-client-16
fi
systemctl enable --now postgresql
ok "PostgreSQL $(psql --version | awk '{print $3}')"

# Crea utente e database MMON
DB_PASS=$(openssl rand -base64 24 | tr -d '/+=' | head -c 32)
sudo -u postgres psql -c "CREATE USER mmon WITH PASSWORD '${DB_PASS}';" 2>/dev/null || true
sudo -u postgres psql -c "CREATE DATABASE mmon_db OWNER mmon;" 2>/dev/null || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE mmon_db TO mmon;" 2>/dev/null || true
mkdir -p /opt/mmon/config
echo "${DB_PASS}" > /opt/mmon/config/.db_password
chmod 600 /opt/mmon/config/.db_password
ok "Database mmon_db creato (password in /opt/mmon/config/.db_password)"

# ── 4. Redis 7 ──
info "Installazione Redis 7..."
if ! command -v redis-server &>/dev/null; then
    apt-get install -y -qq redis-server
fi
systemctl enable --now redis-server
ok "Redis $(redis-server --version | awk '{print $3}' | tr -d 'v=')"

# ── 5. Apache2 + PHP 8.x ──
info "Installazione Apache2 + PHP..."
apt-get install -y -qq apache2 libapache2-mod-php php php-pgsql php-json php-mbstring php-curl
a2enmod proxy proxy_http rewrite headers ssl 2>/dev/null || true
systemctl enable --now apache2
ok "Apache2 $(apache2 -v 2>&1 | head -1 | awk '{print $3}')"
ok "PHP $(php -v | head -1 | awk '{print $2}')"

# ── 6. Struttura filesystem ──
info "Creazione struttura /opt/mmon..."
useradd -r -s /bin/false -d /opt/mmon mmon 2>/dev/null || true
mkdir -p /opt/mmon/{config,backend/{api/routers,api/middleware,models,llm,logs},dashboard/{css,js/widgets},wizard/{includes,steps,assets},scripts}
chown -R mmon:mmon /opt/mmon
ok "Struttura filesystem creata"

# ── 7. Python venv backend ──
info "Creazione venv backend..."
python3 -m venv /opt/mmon/backend/venv
source /opt/mmon/backend/venv/bin/activate
pip install --upgrade pip wheel 2>&1 | tail -1
pip install \
    fastapi==0.115.* \
    uvicorn[standard]==0.32.* \
    sqlalchemy[asyncio]==2.0.* \
    asyncpg==0.30.* \
    psycopg2-binary==2.9.* \
    alembic==1.14.* \
    pydantic==2.10.* \
    pydantic-settings==2.7.* \
    python-jose[cryptography]==3.3.* \
    passlib[bcrypt]==1.7.* \
    httpx==0.28.* \
    structlog==24.* \
    slowapi==0.1.* \
    redis==5.2.* \
    python-multipart==0.0.* \
    2>&1 | tail -3
deactivate
chown -R mmon:mmon /opt/mmon/backend/venv
ok "Venv backend pronto"

# ── 8. Ollama ──
info "Installazione Ollama..."
if ! command -v ollama &>/dev/null; then
    curl -fsSL https://ollama.ai/install.sh | sh
fi
systemctl enable --now ollama
ok "Ollama installato"

info "Download modello qwen2.5:14b (potrebbe richiedere tempo)..."
ollama pull qwen2.5:14b &
OLLAMA_PID=$!
warn "Download in background (PID: $OLLAMA_PID). Verifica con: ollama list"

# ── 9. UFW Firewall ──
info "Configurazione firewall..."
apt-get install -y -qq ufw
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    comment 'SSH'
ufw allow 443/tcp   comment 'HTTPS'
ufw allow 80/tcp    comment 'HTTP redirect'
# Porte interne (solo da IP VM)
ufw allow from any to any port 8000 proto tcp comment 'FastAPI internal'
ufw allow from any to any port 5432 proto tcp comment 'PostgreSQL internal'
ufw allow from any to any port 6379 proto tcp comment 'Redis internal'
echo "y" | ufw enable
ok "Firewall UFW configurato"

# ── 10. Systemd units ──
info "Creazione systemd units..."

cat > /etc/systemd/system/mmon-api.service << 'UNIT'
[Unit]
Description=MMON FastAPI Backend
After=network.target postgresql.service redis-server.service
Requires=postgresql.service redis-server.service

[Service]
Type=simple
User=mmon
Group=mmon
WorkingDirectory=/opt/mmon/backend
Environment=MMON_CONFIG=/opt/mmon/config/mmon.conf
ExecStart=/opt/mmon/backend/venv/bin/uvicorn api.main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

cat > /etc/systemd/system/mmon-llm.service << 'UNIT'
[Unit]
Description=MMON LLM Sanitization Service
After=network.target ollama.service
Requires=ollama.service

[Service]
Type=simple
User=mmon
Group=mmon
WorkingDirectory=/opt/mmon/backend
Environment=MMON_CONFIG=/opt/mmon/config/mmon.conf
ExecStart=/opt/mmon/backend/venv/bin/python -m llm.sanitizer
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
ok "Systemd units creati (mmon-api, mmon-llm)"

# ── 11. Self-signed SSL (placeholder) ──
info "Generazione certificato SSL self-signed..."
if [ ! -f /etc/ssl/certs/mmon.crt ]; then
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/ssl/private/mmon.key \
        -out /etc/ssl/certs/mmon.crt \
        -subj "/CN=mmon.local/O=MMON/C=IT" 2>/dev/null
fi
ok "Certificato SSL generato"

# ── 12. Health check ──
echo ""
info "═══════════════════════════════════════════════════"
info " HEALTH CHECK"
info "═══════════════════════════════════════════════════"

check_service() {
    if systemctl is-active --quiet "$1" 2>/dev/null; then
        ok "$1 ✓"
    else
        warn "$1 ✗ (non attivo)"
    fi
}

check_service postgresql
check_service redis-server
check_service apache2
check_service ollama

echo ""
ok "VM0 Backend provisioning completato!"
info "Password DB: $(cat /opt/mmon/config/.db_password)"
info "Prossimi step: esegui init_db.sql, poi avvia wizard"
