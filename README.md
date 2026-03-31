# MMON — Morpheus MONitoring

Monitoraggio continuo del digital footprint e dell'esposizione online di organizzazioni. Self-hosted, privacy-first, zero telemetria esterna.

## Architettura

Tre VM Linux isolate, ognuna dedicata a un dominio di intelligence:

- **VM1 — CLEARNET-ENGINE:** OSINT e scraping su clearnet (bbot, maigret, h8mail, Shodan, ecc.)
- **VM2 — DEEP-ENGINE:** crawling dark/deep web via Tor con kill switch nftables
- **VM3 — TG-ENGINE:** monitoring canali Telegram tramite puppet account

Le VM comunicano con il backend solo via API REST autenticata. Il backend espone i dati alla dashboard tramite endpoint widget-specific.

## Requisiti

- Ubuntu 22.04 LTS su ogni VM (bare-metal o virtualizzata)
- Minimo 4GB RAM per backend (8GB consigliati con Ollama)
- Minimo 2GB RAM per VM1, VM2, VM3
- PostgreSQL 16, Redis 7, Nginx, Python 3.12, PHP 8.x
- Accesso internet per VM1 (clearnet), Tor per VM2, IP Telegram per VM3

## Setup rapido

### 1. Backend

```bash
sudo bash scripts/setup_backend.sh
```

Installa PostgreSQL 16, Redis 7, Nginx, PHP 8.x, Ollama, Python 3.12, crea struttura `/opt/mmon/`, inizializza DB.

### 2. VM1 — CLEARNET-ENGINE

```bash
sudo bash scripts/setup_vm1.sh
```

Installa Python 3.12, venv con tool OSINT (bbot, maigret, h8mail, shodan, trufflehog, spiderfoot), configura servizi systemd.

### 3. VM2 — DEEP-ENGINE (scaffold)

```bash
sudo bash scripts/setup_vm2.sh
```

Installa Tor, configura kill switch nftables, crea struttura filesystem. Engine development a milestone M8.

### 4. VM3 — TG-ENGINE (scaffold)

```bash
sudo bash scripts/setup_vm3.sh
```

Installa Telethon, configura firewall per soli IP Telegram. Engine development a milestone M9.

### 5. Setup Wizard

Dopo il setup del backend, aprire `http://<BACKEND_IP>:8080` nel browser per il wizard di configurazione iniziale.

## Struttura progetto

```
MMON/
├── config/           # Configurazione (mmon.conf generato dal wizard)
├── vm1/engine/tools/ # Wrapper tool OSINT (un file per tool)
├── vm2/engine/       # Deep web crawler (M8)
├── vm3/engine/       # Telegram client (M9)
├── backend/api/      # FastAPI endpoints
├── backend/models/   # SQLAlchemy models
├── backend/llm/      # Pipeline LLM sanitization (M6)
├── dashboard/        # Frontend Vanilla JS + HTMX
├── wizard/           # Setup wizard PHP
├── scripts/          # Provisioning bash scripts
├── systemd/          # Unit file systemd
├── tests/            # Test suite
└── docs/             # Documentazione
```

## Stato sviluppo

Vedi `PROGRESS.md` per lo stato dettagliato di ogni task.
