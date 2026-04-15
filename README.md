# MMON — Morpheus MONitoring

SaaS self-hosted per il monitoraggio continuo del digital footprint.

## Quick Start

```bash
# VM0 — Backend
sudo bash scripts/setup_backend.sh
sudo -u postgres psql mmon_db < scripts/init_db.sql

# VM1 — Clearnet Engine
sudo bash scripts/setup_vm1.sh

# VM2 — Deep Engine (scaffold)
sudo bash scripts/setup_vm2.sh

# VM3 — Telegram Engine (scaffold)
sudo bash scripts/setup_vm3.sh
```

Apri il wizard: `https://<backend-ip>/wizard`

## Architettura

4 VM Debian 12 isolate, comunicazione solo via API REST.

| VM | Funzione | Rete |
|----|----------|------|
| VM0 | Backend + Dashboard | LAN |
| VM1 | Clearnet OSINT | Clearnet |
| VM2 | Deep/Dark Web | Tor only |
| VM3 | Telegram monitoring | Telegram API only |

## Stack

Python 3.12 · FastAPI · PostgreSQL 16 · Redis 7 · Apache2 · PHP 8.x · Vanilla JS + HTMX · Ollama
