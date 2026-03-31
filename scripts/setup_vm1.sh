#!/usr/bin/env bash
# =============================================================
# MMON — setup_vm1.sh
# Provisioning script per VM1: CLEARNET-ENGINE (Ubuntu 22.04 LTS)
# Installa: Python 3.12, venv, tutti i tool OSINT
# =============================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

MMON_BASE="/opt/mmon"
MMON_USER="mmon"
VM_DIR="${MMON_BASE}/vm1"
LOG_FILE="/var/log/mmon-setup-vm1.log"

log_info()  { echo -e "${CYAN}[INFO]${NC}  $1" | tee -a "$LOG_FILE"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $1" | tee -a "$LOG_FILE"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1" | tee -a "$LOG_FILE"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"; }

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "Eseguire come root (sudo)."
        exit 1
    fi
}

check_os() {
    if ! grep -q "Ubuntu 22.04" /etc/os-release 2>/dev/null; then
        log_warn "OS non è Ubuntu 22.04 LTS."
        read -p "Continuare? (y/N): " confirm
        [[ "$confirm" =~ ^[yY]$ ]] || exit 1
    fi
}

# =============================================================
# 1. PREREQUISITI SISTEMA
# =============================================================

install_prerequisites() {
    log_info "Installazione prerequisiti sistema per tool OSINT..."
    apt-get update -qq
    apt-get install -y -qq \
        software-properties-common \
        build-essential \
        git \
        curl \
        wget \
        unzip \
        jq \
        whois \
        dnsutils \
        nmap \
        chromium-browser \
        libxml2-dev \
        libxslt1-dev \
        zlib1g-dev \
        libffi-dev \
        libssl-dev \
        golang-go

    log_ok "Prerequisiti sistema installati."
}

# =============================================================
# 2. PYTHON 3.12
# =============================================================

install_python() {
    log_info "Installazione Python 3.12..."
    add-apt-repository -y ppa:deadsnakes/ppa
    apt-get update -qq
    apt-get install -y -qq python3.12 python3.12-venv python3.12-dev python3-pip
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1
    log_ok "Python $(python3.12 --version) installato."
}

# =============================================================
# 3. STRUTTURA FILESYSTEM
# =============================================================

setup_filesystem() {
    log_info "Creazione struttura filesystem VM1..."
    id -u "$MMON_USER" &>/dev/null || useradd -r -m -s /bin/bash "$MMON_USER"

    mkdir -p "${VM_DIR}"/{venv,engine/tools,logs}
    mkdir -p "${MMON_BASE}"/{config,scripts}

    chown -R "${MMON_USER}:${MMON_USER}" "${VM_DIR}"
    chmod 750 "${VM_DIR}"

    log_ok "Struttura filesystem VM1 creata."
}

# =============================================================
# 4. PYTHON VENV + DIPENDENZE
# =============================================================

setup_venv() {
    log_info "Creazione virtualenv e installazione dipendenze Python..."

    sudo -u "$MMON_USER" python3.12 -m venv "${VM_DIR}/venv"
    sudo -u "$MMON_USER" "${VM_DIR}/venv/bin/pip" install --upgrade pip wheel setuptools

    cat > /tmp/mmon_vm1_requirements.txt <<'REQS'
# HTTP e requests
httpx==0.27.2
requests==2.32.3
aiohttp==3.10.5

# bbot — subdomain enumeration / attack surface
bbot==2.1.0

# h8mail — credential leak
h8mail==2.5.6

# maigret — username/social tracking
maigret==0.4.4

# mosint — email OSINT
# Installato da source (Go binary), wrapper Python lo chiama via subprocess

# trufflehog — secret/token leak
# Installato come Go binary, wrapper Python lo chiama via subprocess

# spiderfoot — multi-source OSINT
spiderfoot==4.0.0

# Shodan API
shodan==1.31.0

# Parsing e processing
beautifulsoup4==4.12.3
lxml==5.3.0
pandas==2.2.2

# Scheduling
schedule==1.2.2
apscheduler==3.10.4

# Logging strutturato
structlog==24.4.0

# Config
pydantic==2.9.2
pydantic-settings==2.5.2
REQS

    sudo -u "$MMON_USER" "${VM_DIR}/venv/bin/pip" install -r /tmp/mmon_vm1_requirements.txt 2>&1 | tee -a "$LOG_FILE"
    rm /tmp/mmon_vm1_requirements.txt

    log_ok "Virtualenv VM1 configurato."
}

# =============================================================
# 5. TOOL BINARI (Go-based)
# =============================================================

install_go_tools() {
    log_info "Installazione tool Go-based..."

    # trufflehog
    log_info "Installazione trufflehog..."
    curl -sSfL https://raw.githubusercontent.com/trufflesecurity/trufflehog/main/scripts/install.sh | sh -s -- -b /usr/local/bin
    if command -v trufflehog &>/dev/null; then
        log_ok "trufflehog $(trufflehog --version 2>&1 | head -1) installato."
    else
        log_warn "trufflehog: installazione fallita. Verificare manualmente."
    fi

    # mosint
    log_info "Installazione mosint..."
    go install github.com/alpkeskin/mosint/v3/cmd/mosint@latest 2>&1 | tee -a "$LOG_FILE"
    cp "$(go env GOPATH)/bin/mosint" /usr/local/bin/ 2>/dev/null || \
        cp ~/go/bin/mosint /usr/local/bin/ 2>/dev/null || \
        log_warn "mosint: binary non trovato. Verificare GOPATH."

    if command -v mosint &>/dev/null; then
        log_ok "mosint installato."
    else
        log_warn "mosint: installazione fallita."
    fi

    log_ok "Tool Go-based installati."
}

# =============================================================
# 6. SYSTEMD UNITS
# =============================================================

install_systemd_units() {
    log_info "Installazione unit file systemd VM1..."

    # mmon-clearnet-engine.service
    cat > /etc/systemd/system/mmon-clearnet-engine.service <<'UNIT'
[Unit]
Description=MMON Clearnet Engine (VM1)
After=network.target

[Service]
Type=simple
User=mmon
Group=mmon
WorkingDirectory=/opt/mmon/vm1
ExecStart=/opt/mmon/vm1/venv/bin/python -m engine.main
Restart=always
RestartSec=10
Environment=MMON_CONFIG=/opt/mmon/config/mmon.conf
Environment=MMON_VM=vm1

[Install]
WantedBy=multi-user.target
UNIT

    # mmon-scheduler.service
    cat > /etc/systemd/system/mmon-scheduler.service <<'UNIT'
[Unit]
Description=MMON Scan Scheduler (VM1)
After=network.target mmon-clearnet-engine.service

[Service]
Type=simple
User=mmon
Group=mmon
WorkingDirectory=/opt/mmon/vm1
ExecStart=/opt/mmon/vm1/venv/bin/python -m engine.scheduler
Restart=always
RestartSec=30
Environment=MMON_CONFIG=/opt/mmon/config/mmon.conf
Environment=MMON_VM=vm1

[Install]
WantedBy=multi-user.target
UNIT

    systemctl daemon-reload
    log_ok "Unit file systemd VM1 installati."
}

# =============================================================
# 7. HEALTH CHECK
# =============================================================

health_check() {
    echo ""
    echo "============================================="
    echo "  MMON VM1 (CLEARNET-ENGINE) — Health Check"
    echo "============================================="
    echo ""

    local all_ok=true

    # Python
    if "${VM_DIR}/venv/bin/python" --version &>/dev/null; then
        log_ok "Python venv: $("${VM_DIR}/venv/bin/python" --version)"
    else
        log_error "Python venv: NOT WORKING"
        all_ok=false
    fi

    # bbot
    if "${VM_DIR}/venv/bin/python" -c "import bbot" 2>/dev/null; then
        log_ok "bbot:        importabile"
    else
        log_warn "bbot:        import fallito"
    fi

    # shodan
    if "${VM_DIR}/venv/bin/python" -c "import shodan" 2>/dev/null; then
        log_ok "shodan:      importabile"
    else
        log_warn "shodan:      import fallito"
    fi

    # h8mail
    if "${VM_DIR}/venv/bin/python" -c "import h8mail" 2>/dev/null; then
        log_ok "h8mail:      importabile"
    else
        log_warn "h8mail:      import check (potrebbe essere CLI-only)"
    fi

    # maigret
    if "${VM_DIR}/venv/bin/python" -c "import maigret" 2>/dev/null; then
        log_ok "maigret:     importabile"
    else
        log_warn "maigret:     import fallito"
    fi

    # trufflehog
    if command -v trufflehog &>/dev/null; then
        log_ok "trufflehog:  $(trufflehog --version 2>&1 | head -1)"
    else
        log_warn "trufflehog:  non trovato"
    fi

    # mosint
    if command -v mosint &>/dev/null; then
        log_ok "mosint:      installato"
    else
        log_warn "mosint:      non trovato"
    fi

    # nmap
    if command -v nmap &>/dev/null; then
        log_ok "nmap:        $(nmap --version | head -1)"
    else
        log_warn "nmap:        non trovato"
    fi

    # Struttura filesystem
    if [[ -d "${VM_DIR}/engine/tools" && -d "${VM_DIR}/logs" ]]; then
        log_ok "Filesystem:  ${VM_DIR} OK"
    else
        log_error "Filesystem:  struttura incompleta"
        all_ok=false
    fi

    echo ""
    if $all_ok; then
        log_ok "=== SETUP VM1 COMPLETATO ==="
    else
        log_error "=== SETUP INCOMPLETO — controlla gli errori sopra ==="
    fi
    echo ""
    echo "Prossimo passo: configurare mmon.conf con IP backend e avviare i servizi"
    echo "Log completo: ${LOG_FILE}"
}

# =============================================================
# MAIN
# =============================================================

main() {
    echo ""
    echo "============================================="
    echo "  MMON — VM1 CLEARNET-ENGINE Provisioning"
    echo "  Target: Ubuntu 22.04 LTS"
    echo "============================================="
    echo ""

    check_root
    check_os

    touch "$LOG_FILE"

    install_prerequisites
    install_python
    setup_filesystem
    setup_venv
    install_go_tools
    install_systemd_units
    health_check
}

main "$@"
