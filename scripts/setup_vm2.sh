#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# MMON — VM2 (DEEP-ENGINE) Provisioning Script
# Target OS: Debian 12 Bookworm
# Installa: Python 3.12, Tor, nftables kill switch, scaffold engine
# SCAFFOLD: engine files sono placeholder — sviluppo in M6+
# ─────────────────────────────────────────────────────────────
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }

[[ $EUID -ne 0 ]] && fail "Esegui come root: sudo bash $0"

info "═══════════════════════════════════════════════════"
info " MMON — VM2 DEEP-ENGINE Provisioning (Debian 12)"
info " ⚠  SCAFFOLD ONLY — engine development in M6+"
info "═══════════════════════════════════════════════════"

# ── 1. Prerequisiti ──
apt-get update -qq && apt-get upgrade -y -qq
apt-get install -y -qq curl wget git build-essential libffi-dev libssl-dev python3 python3-pip python3-venv python3-dev jq nftables
ok "Dipendenze base installate"

# ── 2. Tor ──
info "Installazione Tor..."
apt-get install -y -qq tor
systemctl enable tor
ok "Tor installato"

# Configurazione Tor
cat > /etc/tor/torrc << 'TORRC'
# MMON Tor config — VM2
SocksPort 9050
ControlPort 9051
HashedControlPassword [TO_BE_SET_BY_WIZARD]
DNSPort 5353
AutomapHostsOnResolve 1
TransPort 9040
VirtualAddrNetworkIPv4 10.192.0.0/10
CircuitBuildTimeout 30
LearnCircuitBuildTimeout 0
NumEntryGuards 6
TORRC
ok "Tor configurato (password da impostare via wizard)"

# ── 3. nftables KILL SWITCH ──
# CRITICO: se Tor cade, TUTTO il traffico viene bloccato (zero clearnet leak)
info "Configurazione nftables kill switch..."
cat > /etc/nftables.conf << 'NFT'
#!/usr/sbin/nft -f
flush ruleset

table inet mmon_killswitch {
    chain input {
        type filter hook input priority 0; policy drop;
        # Loopback
        iif lo accept
        # Connessioni stabilite
        ct state established,related accept
        # SSH solo da rete locale (management)
        tcp dport 22 ip saddr 10.0.0.0/8 accept
        tcp dport 22 ip saddr 172.16.0.0/12 accept
        tcp dport 22 ip saddr 192.168.0.0/16 accept
        # Tutto il resto: DROP
    }

    chain output {
        type filter hook output priority 0; policy drop;
        # Loopback
        oif lo accept
        # DNS locale (Tor)
        udp dport 5353 accept
        # Tor SOCKS (locale)
        tcp dport 9050 ip daddr 127.0.0.1 accept
        # Tor Control (locale)
        tcp dport 9051 ip daddr 127.0.0.1 accept
        # Tor TransPort (locale)
        tcp dport 9040 ip daddr 127.0.0.1 accept
        # Tor ORPort — connessione ai relay Tor (UNICA uscita esterna permessa)
        tcp dport 9001 accept
        tcp dport 9030 accept
        tcp dport 443 accept
        # Connessioni stabilite
        ct state established,related accept
        # API backend (via Tor SOCKS)
        # Il traffico verso il backend passa attraverso Tor — nessuna regola clearnet diretta
        # Tutto il resto: DROP — ZERO CLEARNET LEAK
    }

    chain forward {
        type filter hook forward priority 0; policy drop;
    }
}
NFT

nft -f /etc/nftables.conf 2>/dev/null || warn "nftables non applicato (verificare in produzione)"
systemctl enable nftables
ok "Kill switch nftables configurato — se Tor cade, rete bloccata"

# ── 4. Python 3.12 + venv ──
info "Creazione venv VM2..."
useradd -r -s /bin/false -d /opt/mmon mmon 2>/dev/null || true
mkdir -p /opt/mmon/vm2/{engine,logs,data}
mkdir -p /opt/mmon/config
python3 -m venv /opt/mmon/vm2/venv
source /opt/mmon/vm2/venv/bin/activate
pip install --upgrade pip wheel 2>&1 | tail -1
pip install \
    stem==1.8.* \
    PySocks==1.7.* \
    httpx[socks]==0.28.* \
    beautifulsoup4==4.12.* \
    structlog==24.* \
    pyyaml==6.* \
    aiohttp==3.11.* \
    2>&1 | tail -3
deactivate
chown -R mmon:mmon /opt/mmon/vm2
ok "Venv VM2 pronto"

# ── 5. Scaffold engine files ──
info "Creazione scaffold engine..."

cat > /opt/mmon/vm2/engine/__init__.py << 'PY'
"""MMON VM2 Deep Engine — scaffold."""
PY

cat > /opt/mmon/vm2/engine/tor_client.py << 'PY'
"""
MMON VM2 — Tor Client
Gestisce connessione Tor, verifica circuito, health check.
Sviluppo completo in M6.
"""
import structlog

logger = structlog.get_logger(__name__)


class TorClient:
    """Client Tor con verifica circuito e reconnect automatico."""

    def __init__(self, socks_port: int = 9050, control_port: int = 9051):
        self.socks_port = socks_port
        self.control_port = control_port
        self._connected = False

    async def connect(self) -> bool:
        """Stabilisce connessione al circuito Tor."""
        # TODO M6: implementare connessione via stem
        logger.info("tor_client.connect", socks_port=self.socks_port)
        raise NotImplementedError("VM2 engine in sviluppo — M6")

    async def check_circuit(self) -> dict:
        """Verifica stato circuito Tor."""
        raise NotImplementedError("VM2 engine in sviluppo — M6")

    async def get_exit_ip(self) -> str:
        """Ottieni IP di uscita attuale."""
        raise NotImplementedError("VM2 engine in sviluppo — M6")
PY

cat > /opt/mmon/vm2/engine/crawler.py << 'PY'
"""
MMON VM2 — Dark Web Crawler
Crawling .onion via Tor. Tool: ahmia, torch, custom crawler.
Sviluppo completo in M6.
"""
import structlog

logger = structlog.get_logger(__name__)


class DarkWebCrawler:
    """Crawler per hidden services via Tor."""

    async def crawl_ahmia(self, query: str) -> list[dict]:
        """Cerca su Ahmia (indexed hidden services)."""
        raise NotImplementedError("VM2 engine in sviluppo — M6")

    async def crawl_torch(self, query: str) -> list[dict]:
        """Cerca su Torch (Tor search engine)."""
        raise NotImplementedError("VM2 engine in sviluppo — M6")

    async def crawl_forum(self, url: str) -> list[dict]:
        """Crawl forum specifico da intelligence list proprietaria."""
        raise NotImplementedError("VM2 engine in sviluppo — M6")
PY

cat > /opt/mmon/vm2/engine/puppet_manager.py << 'PY'
"""
MMON VM2 — Puppet Account Manager
Gestione account puppet per forum con registrazione obbligatoria.
Sviluppo completo in M6.
"""
import structlog

logger = structlog.get_logger(__name__)


class PuppetManager:
    """Gestisce account puppet per accesso a forum dark web."""

    async def get_account(self, forum_id: str) -> dict:
        """Ottieni credenziali puppet per un forum specifico."""
        raise NotImplementedError("VM2 engine in sviluppo — M6")

    async def rotate_account(self, forum_id: str) -> dict:
        """Ruota account puppet (burn & recreate)."""
        raise NotImplementedError("VM2 engine in sviluppo — M6")
PY

chown -R mmon:mmon /opt/mmon/vm2
ok "Scaffold engine VM2 creato"

# ── 6. Systemd units ──
info "Creazione systemd units..."

cat > /etc/systemd/system/mmon-deep-engine.service << 'UNIT'
[Unit]
Description=MMON Deep Engine (VM2)
After=network.target tor.service
Requires=tor.service

[Service]
Type=simple
User=mmon
Group=mmon
WorkingDirectory=/opt/mmon/vm2
Environment=MMON_CONFIG=/opt/mmon/config/mmon.conf
ExecStart=/opt/mmon/vm2/venv/bin/python -m engine.crawler
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
UNIT

cat > /etc/systemd/system/mmon-tor-watchdog.service << 'UNIT'
[Unit]
Description=MMON Tor Watchdog (VM2 — verifica circuito)
After=tor.service

[Service]
Type=simple
User=mmon
Group=mmon
ExecStart=/bin/bash -c 'while true; do if ! curl -s --socks5 127.0.0.1:9050 https://check.torproject.org/api/ip | grep -q "true"; then logger -t mmon-watchdog "TOR CIRCUIT DOWN — kill switch attivo"; fi; sleep 60; done'
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
ok "Systemd units creati (mmon-deep-engine, mmon-tor-watchdog)"

# ── 7. Health check ──
echo ""
info "═══════════════════════════════════════════════════"
info " HEALTH CHECK"
info "═══════════════════════════════════════════════════"
check_service() {
    if systemctl is-active --quiet "$1" 2>/dev/null; then ok "$1 ✓"; else warn "$1 ✗"; fi
}
check_service tor
check_service nftables

echo ""
ok "VM2 DEEP-ENGINE scaffold provisioning completato!"
warn "Engine development previsto in M6"
