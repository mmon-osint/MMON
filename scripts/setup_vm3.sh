#!/usr/bin/env bash
# =============================================================
# MMON — setup_vm3.sh
# Provisioning script per VM3: TG-ENGINE (Ubuntu 22.04 LTS)
# SCAFFOLD ONLY — engine development posticipato a M9
# Installa: Python 3.12, Telethon, struttura filesystem, firewall
# =============================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

MMON_BASE="/opt/mmon"
MMON_USER="mmon"
VM_DIR="${MMON_BASE}/vm3"
LOG_FILE="/var/log/mmon-setup-vm3.log"

log_info()  { echo -e "${CYAN}[INFO]${NC}  $1" | tee -a "$LOG_FILE"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $1" | tee -a "$LOG_FILE"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1" | tee -a "$LOG_FILE"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"; }

check_root() {
    [[ $EUID -eq 0 ]] || { log_error "Eseguire come root."; exit 1; }
}

# =============================================================
# 1. PREREQUISITI + PYTHON
# =============================================================

install_prerequisites() {
    log_info "Installazione prerequisiti VM3..."
    apt-get update -qq
    apt-get install -y -qq \
        software-properties-common build-essential git curl wget nftables

    add-apt-repository -y ppa:deadsnakes/ppa
    apt-get update -qq
    apt-get install -y -qq python3.12 python3.12-venv python3.12-dev
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

    log_ok "Prerequisiti installati."
}

# =============================================================
# 2. STRUTTURA FILESYSTEM
# =============================================================

setup_filesystem() {
    log_info "Creazione struttura filesystem VM3..."
    id -u "$MMON_USER" &>/dev/null || useradd -r -m -s /bin/bash "$MMON_USER"

    mkdir -p "${VM_DIR}"/{venv,engine,logs}
    mkdir -p "${MMON_BASE}/config"

    cat > "${VM_DIR}/engine/__init__.py" <<'PY'
"""MMON VM3 TG-ENGINE — Development deferred to M9."""
PY

    cat > "${VM_DIR}/engine/tg_client.py" <<'PY'
"""
MMON — Telegram Client
Crawling canali Telegram tramite puppet account con Telethon.
TODO M9: implementare channel discovery, message parsing, finding submission.
"""
PY

    chown -R "${MMON_USER}:${MMON_USER}" "${VM_DIR}"
    chmod 750 "${VM_DIR}"
    log_ok "Struttura filesystem VM3 creata."
}

# =============================================================
# 3. PYTHON VENV
# =============================================================

setup_venv() {
    log_info "Creazione virtualenv base VM3..."
    sudo -u "$MMON_USER" python3.12 -m venv "${VM_DIR}/venv"
    sudo -u "$MMON_USER" "${VM_DIR}/venv/bin/pip" install --upgrade pip wheel

    cat > /tmp/mmon_vm3_requirements.txt <<'REQS'
# Dipendenze base — M9 aggiungerà il resto
httpx==0.27.2
Telethon==1.36.0
cryptg==0.4.0
structlog==24.4.0
pydantic==2.9.2
REQS

    sudo -u "$MMON_USER" "${VM_DIR}/venv/bin/pip" install -r /tmp/mmon_vm3_requirements.txt
    rm /tmp/mmon_vm3_requirements.txt
    log_ok "Virtualenv VM3 configurato."
}

# =============================================================
# 4. FIREWALL — SOLO IP TELEGRAM API
# =============================================================

configure_firewall() {
    log_info "Configurazione nftables — accesso limitato a Telegram API..."

    cat > /etc/nftables.conf <<'NFT'
#!/usr/sbin/nft -f

# MMON VM3 — Firewall: solo IP Telegram API
# Blocca tutto il traffico tranne Telegram e SSH.

flush ruleset

# Range IP Telegram (aggiornare periodicamente)
# Fonte: https://core.telegram.org/resources/cidr.txt
define telegram_nets = {
    149.154.160.0/20,
    91.108.4.0/22,
    91.108.8.0/22,
    91.108.12.0/22,
    91.108.16.0/22,
    91.108.20.0/22,
    91.108.56.0/22,
    95.161.64.0/20,
    185.76.151.0/24
}

table inet mmon_tg_firewall {

    chain input {
        type filter hook input priority 0; policy drop;
        iif "lo" accept
        ct state established,related accept
        tcp dport 22 accept
        ip protocol icmp accept
    }

    chain output {
        type filter hook output priority 0; policy drop;
        oif "lo" accept
        ct state established,related accept

        # DNS
        udp dport 53 accept
        tcp dport 53 accept

        # Telegram API
        ip daddr $telegram_nets tcp dport { 80, 443 } accept

        # Backend API (configurare IP specifico)
        # ip daddr <BACKEND_IP> tcp dport 8000 accept

        # SSH
        tcp dport 22 accept
    }

    chain forward {
        type filter hook forward priority 0; policy drop;
    }
}
NFT

    systemctl enable nftables
    log_warn "Firewall VM3 configurato ma NON attivato."
    log_warn "Attivare con: sudo systemctl start nftables"
}

# =============================================================
# 5. SYSTEMD UNITS (placeholder)
# =============================================================

install_systemd_units() {
    log_info "Installazione unit file systemd VM3 (placeholder per M9)..."

    cat > /etc/systemd/system/mmon-tg-engine.service <<'UNIT'
[Unit]
Description=MMON Telegram Engine (VM3) — NON ATTIVO, sviluppo M9
After=network.target

[Service]
Type=simple
User=mmon
Group=mmon
WorkingDirectory=/opt/mmon/vm3
ExecStart=/opt/mmon/vm3/venv/bin/python -m engine.main
Restart=always
RestartSec=10
Environment=MMON_CONFIG=/opt/mmon/config/mmon.conf
Environment=MMON_VM=vm3

[Install]
WantedBy=multi-user.target
UNIT

    cat > /etc/systemd/system/mmon-tg-scheduler.service <<'UNIT'
[Unit]
Description=MMON Telegram Scheduler (VM3) — NON ATTIVO, sviluppo M9
After=mmon-tg-engine.service

[Service]
Type=simple
User=mmon
Group=mmon
WorkingDirectory=/opt/mmon/vm3
ExecStart=/opt/mmon/vm3/venv/bin/python -m engine.scheduler
Restart=always
RestartSec=30
Environment=MMON_CONFIG=/opt/mmon/config/mmon.conf
Environment=MMON_VM=vm3

[Install]
WantedBy=multi-user.target
UNIT

    systemctl daemon-reload
    log_ok "Unit file systemd VM3 installati (non abilitati)."
}

# =============================================================
# HEALTH CHECK
# =============================================================

health_check() {
    echo ""
    echo "============================================="
    echo "  MMON VM3 (TG-ENGINE) — Health Check"
    echo "  SCAFFOLD ONLY — Engine development at M9"
    echo "============================================="
    echo ""

    [[ -d "${VM_DIR}/engine" ]] && log_ok "Filesystem: OK" || log_error "Filesystem: INCOMPLETO"
    "${VM_DIR}/venv/bin/python" --version &>/dev/null && log_ok "Python venv: OK" || log_error "Python venv: FALLITO"
    "${VM_DIR}/venv/bin/python" -c "import telethon" 2>/dev/null && log_ok "Telethon: importabile" || log_warn "Telethon: import fallito"
    [[ -f /etc/nftables.conf ]] && log_ok "Firewall: configurato" || log_error "Firewall: MANCANTE"

    echo ""
    log_warn "VM3 è in stato SCAFFOLD. Engine development inizia a M9."
    echo ""
}

# =============================================================
# MAIN
# =============================================================

main() {
    echo ""
    echo "============================================="
    echo "  MMON — VM3 TG-ENGINE Provisioning"
    echo "  SCAFFOLD MODE (M9 per engine completo)"
    echo "============================================="
    echo ""

    check_root
    touch "$LOG_FILE"

    install_prerequisites
    setup_filesystem
    setup_venv
    configure_firewall
    install_systemd_units
    health_check
}

main "$@"
