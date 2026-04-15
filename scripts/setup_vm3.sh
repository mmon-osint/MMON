#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# MMON — VM3 (TG-ENGINE) Provisioning Script
# Target OS: Debian 12 Bookworm
# Installa: Python 3.12, Telethon, nftables (solo Telegram API)
# SCAFFOLD: engine è placeholder — sviluppo in M6+
# ─────────────────────────────────────────────────────────────
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }

[[ $EUID -ne 0 ]] && fail "Esegui come root: sudo bash $0"

info "═══════════════════════════════════════════════════"
info " MMON — VM3 TG-ENGINE Provisioning (Debian 12)"
info " ⚠  SCAFFOLD ONLY — engine development in M6+"
info "═══════════════════════════════════════════════════"

# ── 1. Prerequisiti ──
apt-get update -qq && apt-get upgrade -y -qq
apt-get install -y -qq curl wget git build-essential libffi-dev libssl-dev python3 python3-pip python3-venv python3-dev nftables jq
ok "Dipendenze base installate"

# ── 2. nftables — SOLO Telegram API IPs ──
info "Configurazione nftables (Telegram API only)..."
cat > /etc/nftables.conf << 'NFT'
#!/usr/sbin/nft -f
flush ruleset

table inet mmon_tg_firewall {
    # Telegram API IP ranges (datacenter ufficiali)
    set telegram_ips {
        type ipv4_addr
        flags interval
        elements = {
            149.154.160.0/20,
            91.108.4.0/22,
            91.108.8.0/22,
            91.108.12.0/22,
            91.108.16.0/22,
            91.108.20.0/22,
            91.108.56.0/22
        }
    }

    # Backend API IP (da configurare post-wizard)
    set backend_ips {
        type ipv4_addr
        flags interval
        elements = {
            10.0.0.0/8,
            172.16.0.0/12,
            192.168.0.0/16
        }
    }

    chain input {
        type filter hook input priority 0; policy drop;
        iif lo accept
        ct state established,related accept
        # SSH management
        tcp dport 22 ip saddr { 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 } accept
    }

    chain output {
        type filter hook output priority 0; policy drop;
        oif lo accept
        ct state established,related accept
        # Telegram API HTTPS
        tcp dport 443 ip daddr @telegram_ips accept
        # Telegram MTProto
        tcp dport { 80, 443, 5222 } ip daddr @telegram_ips accept
        # DNS (necessario per risoluzione iniziale)
        udp dport 53 accept
        tcp dport 53 accept
        # Backend API (per inviare findings)
        tcp dport 8000 ip daddr @backend_ips accept
        # TUTTO IL RESTO: DROP
    }

    chain forward {
        type filter hook forward priority 0; policy drop;
    }
}
NFT

nft -f /etc/nftables.conf 2>/dev/null || warn "nftables non applicato (verificare in produzione)"
systemctl enable nftables
ok "Firewall: solo Telegram API + backend consentiti"

# ── 3. Python venv ──
info "Creazione venv VM3..."
useradd -r -s /bin/false -d /opt/mmon mmon 2>/dev/null || true
mkdir -p /opt/mmon/vm3/{engine,logs,data}
mkdir -p /opt/mmon/config
python3 -m venv /opt/mmon/vm3/venv
source /opt/mmon/vm3/venv/bin/activate
pip install --upgrade pip wheel 2>&1 | tail -1
pip install \
    Telethon==1.37.* \
    httpx==0.28.* \
    structlog==24.* \
    pyyaml==6.* \
    cryptg==0.4.* \
    2>&1 | tail -3
deactivate
chown -R mmon:mmon /opt/mmon/vm3
ok "Venv VM3 pronto"

# ── 4. Scaffold engine ──
info "Creazione scaffold engine..."

cat > /opt/mmon/vm3/engine/__init__.py << 'PY'
"""MMON VM3 TG Engine — scaffold."""
PY

cat > /opt/mmon/vm3/engine/tg_client.py << 'PY'
"""
MMON VM3 — Telegram Client
Monitoring canali Telegram tramite puppet account (Telethon).
Sviluppo completo in M6.
"""
import structlog

logger = structlog.get_logger(__name__)


class TelegramClient:
    """Client Telegram per monitoring canali via puppet account."""

    def __init__(self, api_id: int, api_hash: str, phone: str):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self._client = None

    async def connect(self) -> bool:
        """Connetti puppet account a Telegram."""
        # TODO M6: implementare connessione Telethon
        logger.info("tg_client.connect", phone=self.phone[:4] + "****")
        raise NotImplementedError("VM3 engine in sviluppo — M6")

    async def monitor_channel(self, channel_id: str) -> list[dict]:
        """Monitora messaggi da un canale specifico."""
        raise NotImplementedError("VM3 engine in sviluppo — M6")

    async def list_monitored_channels(self) -> list[dict]:
        """Lista canali attualmente monitorati."""
        raise NotImplementedError("VM3 engine in sviluppo — M6")

    async def get_status(self) -> dict:
        """Stato connessione: active / idle / not working."""
        raise NotImplementedError("VM3 engine in sviluppo — M6")
PY

chown -R mmon:mmon /opt/mmon/vm3
ok "Scaffold engine VM3 creato"

# ── 5. Systemd units ──
cat > /etc/systemd/system/mmon-tg-engine.service << 'UNIT'
[Unit]
Description=MMON Telegram Engine (VM3)
After=network.target

[Service]
Type=simple
User=mmon
Group=mmon
WorkingDirectory=/opt/mmon/vm3
Environment=MMON_CONFIG=/opt/mmon/config/mmon.conf
ExecStart=/opt/mmon/vm3/venv/bin/python -m engine.tg_client
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
UNIT

cat > /etc/systemd/system/mmon-tg-scheduler.service << 'UNIT'
[Unit]
Description=MMON Telegram Scheduler (VM3)
After=network.target mmon-tg-engine.service

[Service]
Type=simple
User=mmon
Group=mmon
WorkingDirectory=/opt/mmon/vm3
Environment=MMON_CONFIG=/opt/mmon/config/mmon.conf
ExecStart=/opt/mmon/vm3/venv/bin/python -m engine.tg_client --schedule
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
ok "Systemd units creati (mmon-tg-engine, mmon-tg-scheduler)"

echo ""
ok "VM3 TG-ENGINE scaffold provisioning completato!"
warn "Engine development previsto in M6"
