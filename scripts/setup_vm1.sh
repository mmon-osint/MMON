#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# MMON — VM1 (CLEARNET-ENGINE) Provisioning Script
# Target OS: Debian 12 Bookworm
# Installa: Python 3.12, venv, bbot, mosint, trufflehog,
#           shodan, theHarvester, custom dorks scraper
# ─────────────────────────────────────────────────────────────
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }

[[ $EUID -ne 0 ]] && fail "Esegui come root: sudo bash $0"

info "═══════════════════════════════════════════════════"
info " MMON — VM1 CLEARNET-ENGINE Provisioning (Debian 12)"
info "═══════════════════════════════════════════════════"

# ── 1. Prerequisiti ──
info "Aggiornamento sistema..."
apt-get update -qq && apt-get upgrade -y -qq
apt-get install -y -qq \
    curl wget git build-essential libffi-dev libssl-dev libxml2-dev \
    libxslt1-dev zlib1g-dev chromium chromium-driver jq
ok "Dipendenze base installate"

# ── 2. Python 3.12 ──
info "Installazione Python 3.12..."
apt-get install -y -qq python3 python3-pip python3-venv python3-dev
if ! python3 --version 2>&1 | grep -q "3.12"; then
    warn "Python 3.12 non in repo, compilazione da sorgente..."
    cd /tmp
    wget -q "https://www.python.org/ftp/python/3.12.7/Python-3.12.7.tgz"
    tar xzf Python-3.12.7.tgz && cd Python-3.12.7
    ./configure --enable-optimizations --prefix=/usr/local 2>&1 | tail -1
    make -j"$(nproc)" 2>&1 | tail -1 && make altinstall
    ln -sf /usr/local/bin/python3.12 /usr/local/bin/python3
    cd /tmp && rm -rf Python-3.12.7*
fi
ok "Python $(python3 --version 2>&1)"

# ── 3. Go (per trufflehog e mosint) ──
info "Installazione Go..."
if ! command -v go &>/dev/null; then
    GO_VER="1.22.5"
    wget -q "https://go.dev/dl/go${GO_VER}.linux-amd64.tar.gz" -O /tmp/go.tar.gz
    rm -rf /usr/local/go && tar -C /usr/local -xzf /tmp/go.tar.gz
    echo 'export PATH=$PATH:/usr/local/go/bin:/root/go/bin' >> /etc/profile.d/go.sh
    export PATH=$PATH:/usr/local/go/bin:/root/go/bin
    rm /tmp/go.tar.gz
fi
ok "Go $(go version | awk '{print $3}')"

# ── 4. Struttura filesystem ──
info "Creazione struttura /opt/mmon/vm1..."
useradd -r -s /bin/false -d /opt/mmon mmon 2>/dev/null || true
mkdir -p /opt/mmon/vm1/{engine/tools,logs,data}
mkdir -p /opt/mmon/config

# ── 5. Python venv ──
info "Creazione venv VM1..."
python3 -m venv /opt/mmon/vm1/venv
source /opt/mmon/vm1/venv/bin/activate
pip install --upgrade pip wheel 2>&1 | tail -1

# ── 6. Installazione tool Python ──
info "Installazione dipendenze Python..."
pip install \
    bbot==2.1.* \
    shodan==1.31.* \
    theHarvester==4.6.* \
    httpx==0.28.* \
    beautifulsoup4==4.12.* \
    structlog==24.* \
    pyyaml==6.* \
    fake-useragent==1.* \
    2>&1 | tail -3
ok "Dipendenze Python installate"

# ── 7. Installazione tool Go ──
info "Installazione mosint..."
go install github.com/alpkeskin/mosint/v3/cmd/mosint@latest 2>&1 | tail -1
cp ~/go/bin/mosint /usr/local/bin/ 2>/dev/null || true
ok "mosint $(mosint --version 2>&1 || echo 'installato')"

info "Installazione trufflehog..."
go install github.com/trufflesecurity/trufflehog/v3@latest 2>&1 | tail -1
cp ~/go/bin/trufflehog /usr/local/bin/ 2>/dev/null || true
ok "trufflehog installato"

deactivate

# ── 8. Permessi ──
chown -R mmon:mmon /opt/mmon/vm1

# ── 9. Systemd units ──
info "Creazione systemd units..."

cat > /etc/systemd/system/mmon-clearnet-engine.service << 'UNIT'
[Unit]
Description=MMON Clearnet Engine (VM1)
After=network.target

[Service]
Type=simple
User=mmon
Group=mmon
WorkingDirectory=/opt/mmon/vm1
Environment=MMON_CONFIG=/opt/mmon/config/mmon.conf
ExecStart=/opt/mmon/vm1/venv/bin/python -m engine.scheduler --run-all
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
UNIT

cat > /etc/systemd/system/mmon-scheduler.service << 'UNIT'
[Unit]
Description=MMON Scheduler (VM1 — continuous loop)
After=network.target

[Service]
Type=simple
User=mmon
Group=mmon
WorkingDirectory=/opt/mmon/vm1
Environment=MMON_CONFIG=/opt/mmon/config/mmon.conf
ExecStart=/opt/mmon/vm1/venv/bin/python -m engine.scheduler --loop
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
ok "Systemd units creati (mmon-clearnet-engine, mmon-scheduler)"

# ── 10. Health check ──
echo ""
info "═══════════════════════════════════════════════════"
info " HEALTH CHECK"
info "═══════════════════════════════════════════════════"

for cmd in python3 bbot mosint trufflehog; do
    if command -v "$cmd" &>/dev/null || /opt/mmon/vm1/venv/bin/"$cmd" --help &>/dev/null 2>&1; then
        ok "$cmd ✓"
    else
        warn "$cmd ✗ (verifica installazione)"
    fi
done

echo ""
ok "VM1 CLEARNET-ENGINE provisioning completato!"
info "Prossimo step: copia engine/ e config in /opt/mmon/vm1/"
