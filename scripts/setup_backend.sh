#!/usr/bin/env bash
# =============================================================
# MMON — setup_backend.sh
# Provisioning script per VM Backend (Ubuntu 22.04 LTS)
# Installa: Python 3.12, PostgreSQL 16, Redis 7, Nginx, PHP 8.x, Ollama
# =============================================================

set -euo pipefail

# Colori output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

MMON_BASE="/opt/mmon"
MMON_USER="mmon"
LOG_FILE="/var/log/mmon-setup-backend.log"

# =============================================================
# FUNZIONI UTILITY
# =============================================================

log_info()  { echo -e "${CYAN}[INFO]${NC}  $1" | tee -a "$LOG_FILE"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $1" | tee -a "$LOG_FILE"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1" | tee -a "$LOG_FILE"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"; }

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "Questo script deve essere eseguito come root (sudo)."
        exit 1
    fi
}

check_os() {
    if ! grep -q "Ubuntu 22.04" /etc/os-release 2>/dev/null; then
        log_warn "OS non è Ubuntu 22.04 LTS. Lo script potrebbe non funzionare correttamente."
        read -p "Continuare comunque? (y/N): " confirm
        [[ "$confirm" =~ ^[yY]$ ]] || exit 1
    fi
}

# =============================================================
# 1. PREREQUISITI
# =============================================================

install_prerequisites() {
    log_info "Aggiornamento sistema e installazione prerequisiti..."
    apt-get update -qq
    apt-get upgrade -y -qq
    apt-get install -y -qq \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        curl \
        wget \
        gnupg \
        lsb-release \
        build-essential \
        libssl-dev \
        libffi-dev \
        git \
        unzip \
        jq \
        htop \
        net-tools \
        ufw
    log_ok "Prerequisiti installati."
}

# =============================================================
# 2. PYTHON 3.12
# =============================================================

install_python() {
    log_info "Installazione Python 3.12..."
    add-apt-repository -y ppa:deadsnakes/ppa
    apt-get update -qq
    apt-get install -y -qq \
        python3.12 \
        python3.12-venv \
        python3.12-dev \
        python3-pip

    # Impostare python3.12 come default python3
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

    log_ok "Python $(python3.12 --version) installato."
}

# =============================================================
# 3. POSTGRESQL 16
# =============================================================

#install_postgresql() {
#   log_info "Installazione PostgreSQL 16..."
#
   # Repository ufficiale PostgreSQL
#    curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /usr/share/keyrings/postgresql-keyring.gpg
 #   echo "deb [signed-by=/usr/share/keyrings/postgresql-keyring.gpg] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
  #      > /etc/apt/sources.list.d/pgdg.list
#
 #   apt-get update -qq
  #  apt-get install -y -qq postgresql-16 postgresql-contrib-16
#
 #   systemctl enable postgresql
 #  systemctl start postgresql

  #  log_ok "PostgreSQL $(psql --version | head -1) installato e avviato."
#}

setup_database() {
    log_info "Configurazione database MMON..."

    # Generare password random per il DB
    DB_PASSWORD=$(openssl rand -base64 32 | tr -d '/+=' | head -c 32)

    sudo -u postgres psql -c "CREATE ROLE mmon WITH LOGIN PASSWORD '${DB_PASSWORD}';" 2>/dev/null || \
        log_warn "Ruolo mmon già esistente."
    sudo -u postgres psql -c "CREATE DATABASE mmon OWNER mmon;" 2>/dev/null || \
        log_warn "Database mmon già esistente."

    # Eseguire schema se presente
    if [[ -f "${MMON_BASE}/scripts/init_db.sql" ]]; then
        # Sostituire CHANGE_ME con password generata
        sed "s/CHANGE_ME/${DB_PASSWORD}/g" "${MMON_BASE}/scripts/init_db.sql" | \
            sudo -u postgres psql -d mmon -f - 2>&1 | tee -a "$LOG_FILE"
        log_ok "Schema DB inizializzato."
    else
        log_warn "File init_db.sql non trovato in ${MMON_BASE}/scripts/. Eseguire manualmente."
    fi

    # Salvare password in file protetto
    echo "${DB_PASSWORD}" > "${MMON_BASE}/config/.db_password"
    chmod 600 "${MMON_BASE}/config/.db_password"
    chown "${MMON_USER}:${MMON_USER}" "${MMON_BASE}/config/.db_password"

    log_ok "Database configurato. Password salvata in ${MMON_BASE}/config/.db_password"
}

# =============================================================
# 4. REDIS 7
# =============================================================

install_redis() {
    log_info "Installazione Redis 7..."

    curl -fsSL https://packages.redis.io/gpg | gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
    echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" \
        > /etc/apt/sources.list.d/redis.list

    apt-get update -qq
    apt-get install -y -qq redis-server

    # Configurare Redis per bind solo localhost
    sed -i 's/^bind .*/bind 127.0.0.1 ::1/' /etc/redis/redis.conf
    sed -i 's/^# maxmemory .*/maxmemory 256mb/' /etc/redis/redis.conf
    sed -i 's/^# maxmemory-policy .*/maxmemory-policy allkeys-lru/' /etc/redis/redis.conf

    systemctl enable redis-server
    systemctl restart redis-server

    log_ok "Redis $(redis-server --version | awk '{print $3}') installato e configurato."
}

# =============================================================
# 5. NGINX
# =============================================================

install_nginx() {
    log_info "Installazione Nginx..."
    apt-get install -y -qq nginx

    systemctl enable nginx
    systemctl start nginx

    log_ok "Nginx $(nginx -v 2>&1 | awk -F/ '{print $2}') installato."
}

configure_nginx() {
    log_info "Configurazione Nginx per MMON..."

    cat > /etc/nginx/sites-available/mmon <<'NGINX_CONF'
# MMON — Nginx configuration

# Dashboard (porta 80/443)
server {
    listen 80;
    server_name _;

    root /opt/mmon/dashboard;
    index index.html;

    # Dashboard statica
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy verso FastAPI backend
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Health check backend
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }
}

# Wizard PHP (porta 8080, disabilitato dopo setup)
server {
    listen 8080;
    server_name _;

    root /opt/mmon/wizard;
    index index.php;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/run/php/php-fpm.sock;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }

    location ~ /\.ht {
        deny all;
    }
}
NGINX_CONF

    # Attivare configurazione
    ln -sf /etc/nginx/sites-available/mmon /etc/nginx/sites-enabled/mmon
    rm -f /etc/nginx/sites-enabled/default

    nginx -t && systemctl reload nginx
    log_ok "Nginx configurato per dashboard (:80) e wizard (:8080)."
}

# =============================================================
# 6. PHP 8.x
# =============================================================

install_php() {
    log_info "Installazione PHP 8.x..."
    add-apt-repository -y ppa:ondrej/php
    apt-get update -qq
    apt-get install -y -qq \
        php8.3 \
        php8.3-fpm \
        php8.3-cli \
        php8.3-pgsql \
        php8.3-mbstring \
        php8.3-xml \
        php8.3-curl \
        php8.3-json

    systemctl enable php8.3-fpm
    systemctl start php8.3-fpm

    # Fix socket path nel conf nginx se necessario
    PHP_SOCK=$(find /run/php/ -name "*.sock" 2>/dev/null | head -1)
    if [[ -n "$PHP_SOCK" ]]; then
        sed -i "s|unix:/run/php/php-fpm.sock|unix:${PHP_SOCK}|g" /etc/nginx/sites-available/mmon
        nginx -t && systemctl reload nginx
    fi

    log_ok "PHP $(php -v | head -1 | awk '{print $2}') installato."
}

# =============================================================
# 7. OLLAMA
# =============================================================

install_ollama() {
    log_info "Installazione Ollama..."
    curl -fsSL https://ollama.ai/install.sh | sh

    systemctl enable ollama
    systemctl start ollama

    log_info "Download modello qwen2.5:14b (questo richiede tempo e ~9GB di spazio)..."
    ollama pull qwen2.5:14b

    log_ok "Ollama installato con modello qwen2.5:14b."
}

# =============================================================
# 8. STRUTTURA FILESYSTEM E UTENTE
# =============================================================

setup_filesystem() {
    log_info "Creazione utente e struttura filesystem MMON..."

    # Creare utente di sistema
    id -u "$MMON_USER" &>/dev/null || useradd -r -m -s /bin/bash "$MMON_USER"

    # Creare struttura directory
    mkdir -p "${MMON_BASE}"/{config,backend/{api/routers,api/middleware,models,llm,logs},dashboard/{js/widgets,css,assets},wizard/steps,scripts,systemd,docs,tests}

    # Permessi
    chown -R "${MMON_USER}:${MMON_USER}" "${MMON_BASE}"
    chmod 750 "${MMON_BASE}"
    chmod 700 "${MMON_BASE}/config"

    log_ok "Struttura filesystem creata in ${MMON_BASE}."
}

# =============================================================
# 9. PYTHON VENV BACKEND
# =============================================================

setup_backend_venv() {
    log_info "Creazione virtualenv backend e installazione dipendenze..."

    sudo -u "$MMON_USER" python3.12 -m venv "${MMON_BASE}/backend/venv"

    sudo -u "$MMON_USER" "${MMON_BASE}/backend/venv/bin/pip" install --upgrade pip wheel

    # Dipendenze backend
    cat > /tmp/mmon_backend_requirements.txt <<'REQS'
# FastAPI + server
fastapi==0.115.0
uvicorn[standard]==0.30.6
python-multipart==0.0.9

# Database
sqlalchemy==2.0.35
asyncpg==0.29.0
alembic==1.13.2
psycopg2-binary==2.9.9

# Redis
redis==5.1.0

# Auth
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# Validation e config
pydantic==2.9.2
pydantic-settings==2.5.2
python-dotenv==1.0.1

# HTTP client (per comunicazione tra servizi)
httpx==0.27.2

# Rate limiting
slowapi==0.1.9

# Logging
structlog==24.4.0

# Testing
pytest==8.3.3
pytest-asyncio==0.24.0
httpx==0.27.2
REQS

    sudo -u "$MMON_USER" "${MMON_BASE}/backend/venv/bin/pip" install -r /tmp/mmon_backend_requirements.txt
    rm /tmp/mmon_backend_requirements.txt

    log_ok "Virtualenv backend configurato."
}

# =============================================================
# 10. SYSTEMD UNITS
# =============================================================

install_systemd_units() {
    log_info "Installazione unit file systemd..."

    # mmon-api.service
    cat > /etc/systemd/system/mmon-api.service <<'UNIT'
[Unit]
Description=MMON FastAPI Backend
After=network.target postgresql.service redis-server.service
Requires=postgresql.service redis-server.service

[Service]
Type=simple
User=mmon
Group=mmon
WorkingDirectory=/opt/mmon/backend
ExecStart=/opt/mmon/backend/venv/bin/uvicorn api.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5
Environment=MMON_CONFIG=/opt/mmon/config/mmon.conf

[Install]
WantedBy=multi-user.target
UNIT

    # mmon-llm.service
    cat > /etc/systemd/system/mmon-llm.service <<'UNIT'
[Unit]
Description=MMON LLM Sanitization Service
After=network.target ollama.service mmon-api.service

[Service]
Type=simple
User=mmon
Group=mmon
WorkingDirectory=/opt/mmon/backend
ExecStart=/opt/mmon/backend/venv/bin/python -m llm.sanitizer
Restart=always
RestartSec=10
Environment=MMON_CONFIG=/opt/mmon/config/mmon.conf

[Install]
WantedBy=multi-user.target
UNIT

    systemctl daemon-reload
    log_ok "Unit file systemd installati."
}

# =============================================================
# 11. FIREWALL BASE
# =============================================================

configure_firewall() {
    log_info "Configurazione firewall UFW..."

    ufw --force reset
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow ssh
    ufw allow 80/tcp        # Dashboard
    ufw allow 8080/tcp      # Wizard (disabilitare dopo setup)
    # Porta 8000 (FastAPI) NON esposta — solo via Nginx proxy
    ufw --force enable

    log_ok "Firewall configurato."
}

# =============================================================
# 12. HEALTH CHECK
# =============================================================

health_check() {
    echo ""
    echo "============================================="
    echo "  MMON Backend — Health Check"
    echo "============================================="
    echo ""

    local all_ok=true

    # PostgreSQL
    if systemctl is-active --quiet postgresql; then
        log_ok "PostgreSQL:  RUNNING"
    else
        log_error "PostgreSQL:  NOT RUNNING"
        all_ok=false
    fi

    # Redis
    if systemctl is-active --quiet redis-server; then
        log_ok "Redis:       RUNNING"
    else
        log_error "Redis:       NOT RUNNING"
        all_ok=false
    fi

    # Nginx
    if systemctl is-active --quiet nginx; then
        log_ok "Nginx:       RUNNING"
    else
        log_error "Nginx:       NOT RUNNING"
        all_ok=false
    fi

    # PHP-FPM
    if systemctl is-active --quiet "php*-fpm"; then
        log_ok "PHP-FPM:     RUNNING"
    else
        log_error "PHP-FPM:     NOT RUNNING"
        all_ok=false
    fi

    # Ollama
    if systemctl is-active --quiet ollama; then
        log_ok "Ollama:      RUNNING"
    else
        log_warn "Ollama:      NOT RUNNING (non critico per M1-M5)"
    fi

    # Python
    if python3.12 --version &>/dev/null; then
        log_ok "Python:      $(python3.12 --version)"
    else
        log_error "Python 3.12: NOT FOUND"
        all_ok=false
    fi

    # Struttura filesystem
    if [[ -d "${MMON_BASE}/backend" && -d "${MMON_BASE}/dashboard" && -d "${MMON_BASE}/config" ]]; then
        log_ok "Filesystem:  ${MMON_BASE} OK"
    else
        log_error "Filesystem:  struttura incompleta"
        all_ok=false
    fi

    echo ""
    if $all_ok; then
        log_ok "=== SETUP BACKEND COMPLETATO CON SUCCESSO ==="
    else
        log_error "=== SETUP INCOMPLETO — controlla gli errori sopra ==="
    fi
    echo ""
    echo "Prossimo passo: aprire http://<IP>:8080 per il Setup Wizard"
    echo "Log completo: ${LOG_FILE}"
}

# =============================================================
# MAIN
# =============================================================

main() {
    echo ""
    echo "============================================="
    echo "  MMON — Backend Provisioning Script"
    echo "  Target: Ubuntu 22.04 LTS"
    echo "============================================="
    echo ""

    check_root
    check_os

    touch "$LOG_FILE"

    install_prerequisites
    setup_filesystem
    install_python
    install_postgresql
    setup_database
    install_redis
    install_nginx
    install_php
    configure_nginx
    install_ollama
    setup_backend_venv
    install_systemd_units
    configure_firewall
    health_check
}

main "$@"
