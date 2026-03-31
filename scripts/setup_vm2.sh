#!/usr/bin/env bash
# =============================================================
# MMON — setup_vm2.sh
# Provisioning script per VM2: DEEP-ENGINE (Ubuntu 22.04 LTS)
# SCAFFOLD ONLY — engine development posticipato a M8
# Installa: Python 3.12, Tor, nftables kill switch, struttura filesystem
# =============================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

MMON_BASE="/opt/mmon"
MMON_USER="mmon"
VM_DIR="${MMON_BASE}/vm2"
LOG_FILE="/var/log/mmon-setup-vm2.log"

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
    log_info "Installazione prerequisiti VM2..."
    apt-get update -qq
    apt-get install -y -qq \
        software-properties-common build-essential git curl wget \
        nftables tor

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
    log_info "Creazione struttura filesystem VM2..."
    id -u "$MMON_USER" &>/dev/null || useradd -r -m -s /bin/bash "$MMON_USER"

    mkdir -p "${VM_DIR}"/{venv,engine,logs}
    mkdir -p "${MMON_BASE}/config"

    # File placeholder per sviluppo futuro M8
    cat > "${VM_DIR}/engine/__init__.py" <<'PY'
"""MMON VM2 DEEP-ENGINE — Development deferred to M8."""
PY

    cat > "${VM_DIR}/engine/tor_client.py" <<'PY'
"""
MMON — Tor Client
Gestione connessione Tor con stem + PySocks.
TODO M8: implementare connection manager, circuit renewal, health check.
"""
PY

    cat > "${VM_DIR}/engine/puppet_manager.py" <<'PY'
"""
MMON — Puppet Account Manager
Gestione account puppet per forum con registrazione obbligatoria.
TODO M8: implementare account pool, rotation, captcha handling.
"""
PY

    cat > "${VM_DIR}/engine/crawler.py" <<'PY'
"""
MMON — Deep Web Crawler
Crawling forum e hidden services via Tor.
TODO M8: implementare crawler con rate limiting, parsing, finding submission.
"""
PY

    chown -R "${MMON_USER}:${MMON_USER}" "${VM_DIR}"
    chmod 750 "${VM_DIR}"

    log_ok "Struttura filesystem VM2 creata."
}

# =============================================================
# 3. PYTHON VENV (base)
# =============================================================

setup_venv() {
    log_info "Creazione virtualenv base VM2..."
    sudo -u "$MMON_USER" python3.12 -m venv "${VM_DIR}/venv"
    sudo -u "$MMON_USER" "${VM_DIR}/venv/bin/pip" install --upgrade pip wheel

    cat > /tmp/mmon_vm2_requirements.txt <<'REQS'
# Dipendenze base — M8 aggiungerà il resto
httpx==0.27.2
requests==2.32.3
PySocks==1.7.1
stem==1.8.2
beautifulsoup4==4.12.3
structlog==24.4.0
pydantic==2.9.2
REQS

    sudo -u "$MMON_USER" "${VM_DIR}/venv/bin/pip" install -r /tmp/mmon_vm2_requirements.txt
    rm /tmp/mmon_vm2_requirements.txt

    log_ok "Virtualenv VM2 configurato."
}

# =============================================================
# 4. TOR CONFIGURATION
# =============================================================

configure_tor() {
    log_info "Configurazione Tor..."

    cat > /etc/tor/torrc <<'TORRC'
SocksPort 9050
ControlPort 9051
HashedControlPassword GENERATE_WITH_tor_--hash-password
Log notice file /var/log/tor/notices.log
DataDirectory /var/lib/tor
TORRC

    systemctl enable tor
    # NON avviare Tor finché il kill switch non è attivo
    log_ok "Tor configurato (non avviato — richiede kill switch nftables)."
}

# =============================================================
# 5. NFTABLES KILL SWITCH
# =============================================================

configure_killswitch() {
    log_info "Configurazione nftables kill switch Tor..."

    cat > /etc/nftables.conf <<'NFT'
#!/usr/sbin/nft -f

# MMON VM2 — Tor Kill Switch
# Se Tor cade, TUTTO il traffico viene bloccato.
# Zero clearnet leak possibile.

flush ruleset

table inet mmon_killswitch {

    chain input {
        type filter hook input priority 0; policy drop;

        # Loopback
        iif "lo" accept

        # Connessioni stabilite
        ct state established,related accept

        # SSH (per manutenzione — rimuovere in produzione se non necessario)
        tcp dport 22 accept

        # ICMP base
        ip protocol icmp accept
        ip6 nexthdr icmpv6 accept
    }

    chain output {
        type filter hook output priority 0; policy drop;

        # Loopback
        oif "lo" accept

        # Connessioni stabilite
        ct state established,related accept

        # DNS locale (necessario per risolvere .onion via Tor)
        udp dport 53 accept
        tcp dport 53 accept

        # Tor SOCKS (locale)
        tcp dport 9050 accept
        tcp dport 9051 accept

        # Tor relay traffic (porte OR standard)
        tcp dport { 9001, 9030, 9040, 9150 } accept

        # SSH outbound (per manutenzione)
        tcp dport 22 accept

        # Accesso a backend API (configurare IP specifico)
        # tcp dport 8000 ip daddr <BACKEND_IP> accept

        # TUTTO IL RESTO: DROP
        # Se Tor cade, nessun traffico clearnet esce dalla VM.
    }

    chain forward {
        type filter hook forward priority 0; policy drop;
    }
}
NFT

    # Abilitare nftables al boot
    systemctl enable nftables

    log_warn "Kill switch nftables configurato ma NON attivato."
    log_warn "Attivare con: sudo systemctl start nftables"
    log_warn "ATTENZIONE: una volta attivato, solo traffico Tor e SSH funzionerà."
}

# =============================================================
# 6. SYSTEMD UNITS (placeholder)
# =============================================================

install_systemd_units() {
    log_info "Installazione unit file systemd VM2 (placeholder per M8)..."

    cat > /etc/systemd/system/mmon-deep-engine.service <<'UNIT'
[Unit]
Description=MMON Deep Web Engine (VM2) — NON ATTIVO, sviluppo M8
After=network.target tor.service
Requires=tor.service

[Service]
Type=simple
User=mmon
Group=mmon
WorkingDirectory=/opt/mmon/vm2
ExecStart=/opt/mmon/vm2/venv/bin/python -m engine.main
Restart=always
RestartSec=10
Environment=MMON_CONFIG=/opt/mmon/config/mmon.conf
Environment=MMON_VM=vm2

[Install]
WantedBy=multi-user.target
UNIT

    cat > /etc/systemd/system/mmon-tor-watchdog.service <<'UNIT'
[Unit]
Description=MMON Tor Watchdog — riavvia Tor se cade, blocca traffico
After=tor.service

[Service]
Type=simple
User=root
ExecStart=/opt/mmon/vm2/engine/tor_watchdog.sh
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

    systemctl daemon-reload
    log_ok "Unit file systemd VM2 installati (non abilitati)."
}

# =============================================================
# HEALTH CHECK
# =============================================================

health_check() {
    echo ""
    echo "============================================="
    echo "  MMON VM2 (DEEP-ENGINE) — Health Check"
    echo "  SCAFFOLD ONLY — Engine development at M8"
    echo "============================================="
    echo ""

    [[ -d "${VM_DIR}/engine" ]] && log_ok "Filesystem: OK" || log_error "Filesystem: INCOMPLETO"
    "${VM_DIR}/venv/bin/python" --version &>/dev/null && log_ok "Python venv: OK" || log_error "Python venv: FALLITO"
    command -v tor &>/dev/null && log_ok "Tor: installato" || log_error "Tor: NON TROVATO"
    [[ -f /etc/nftables.conf ]] && log_ok "Kill switch: configurato" || log_error "Kill switch: MANCANTE"

    echo ""
    log_warn "VM2 è in stato SCAFFOLD. Engine development inizia a M8."
    echo ""
}

# =============================================================
# MAIN
# =============================================================

main() {
    echo ""
    echo "============================================="
    echo "  MMON — VM2 DEEP-ENGINE Provisioning"
    echo "  SCAFFOLD MODE (M8 per engine completo)"
    echo "============================================="
    echo ""

    check_root
    touch "$LOG_FILE"

    install_prerequisites
    setup_filesystem
    setup_venv
    configure_tor
    configure_killswitch
    install_systemd_units
    health_check
}

main "$@"
