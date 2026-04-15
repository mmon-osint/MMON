# MMON — Progress Tracker

> Generato automaticamente. Aggiornato ad ogni milestone completata.

## Stato Generale

| Milestone | Stato | Data |
|-----------|-------|------|
| M1 — Scaffold + Provisioning | [x] | 2026-04-15 |
| M2 — Setup Wizard PHP | [x] | 2026-04-15 |
| M3 — FastAPI Backend | [x] | 2026-04-15 |
| M4 — VM1 Tool Wrappers | [x] | 2026-04-15 |
| M5 — Dashboard v1 | [x] | 2026-04-15 |

---

## M1 — Scaffold + Provisioning

- [x] 1.1 Script `setup_backend.sh` (VM0: Python 3.12, FastAPI, PostgreSQL 16, Redis 7, Apache2, PHP 8.x, Ollama)
- [x] 1.2 Script `setup_vm1.sh` (VM1: Python 3.12, venv, bbot, mosint, trufflehog, shodan, theHarvester, systemd)
- [x] 1.3 Script `setup_vm2.sh` (VM2: scaffold — Python 3.12, Tor, nftables kill switch, engine scaffold)
- [x] 1.4 Script `setup_vm3.sh` (VM3: scaffold — Python 3.12, Telethon, nftables Telegram-only, engine scaffold)
- [x] 1.5 Schema DB `init_db.sql` (PostgreSQL 16 — 6 tabelle, ENUM, indici GIN, trigger)
- [x] 1.6 Config template `mmon.conf.example` (con sezione Keycloak)
- [x] 1.7 `.gitignore` + `README.md`

## M2 — Setup Wizard PHP

- [x] 2.1 Router `wizard/index.php`
- [x] 2.2 Shared functions `wizard/includes/functions.php`
- [x] 2.3 Step 1: Modalità (Personal/Company con Keycloak)
- [x] 2.4 Step 2: Target (domini, IP, email)
- [x] 2.5 Step 3: Social (username, nominativi)
- [x] 2.6 Step 4: Tecnologie (8 categorie, chip selezionabili)
- [x] 2.7 Step 5: Settore/Prodotti/Competitor
- [x] 2.8 Step 6: API Keys (con test button JS)
- [x] 2.9 Step 7: Infrastruttura (IP VM, Tor, Telegram, Keycloak condizionale)
- [x] 2.10 Step 8: Summary + conferma + genera mmon.conf + init DB
- [x] 2.11 CSS cyberpunk theme

## M3 — FastAPI Backend

- [x] 3.1 Config loader (`config.py`) — INI parser + Pydantic Settings + Keycloak
- [x] 3.2 Database async (`database.py`) — asyncpg + session factory
- [x] 3.3 ORM models (`db_models.py`) — 6 tabelle, UUID, JSONB, ARRAY
- [x] 3.4 Pydantic schemas (`schemas.py`) — 9 categorie finding, widget VM1+VM2+VM3
- [x] 3.5 Auth middleware (JWT + VM IP whitelist + require_role)
- [x] 3.6 Router auth (`/auth/login`, `/auth/me`, `/auth/setup-password`)
- [x] 3.7 Router findings (`POST /findings` VM auth, `GET /findings` JWT + 8 filtri)
- [x] 3.8 Router widgets (12 endpoint: social, infra, cve, keywords, competitors, status, bad-actors, criminal-forums, alerts, telegram-status, monitored-channels)
- [x] 3.9 Router jobs (`POST trigger`, `GET status`, `POST cancel` — ALLOWED_TOOLS per VM)
- [x] 3.10 Main app (`main.py` — rate limiter, CORS, logging, test-apikey)
- [x] 3.11 Test suite (12 test cases — schema validation + injection prevention)

## M4 — VM1 Tool Wrappers

- [x] 4.1 Base wrapper astratto (`base.py` — retry, submit, subprocess sicuro)
- [x] 4.2 `bbot_wrapper.py` (subdomain/attack surface → infrastructure)
- [x] 4.3 `mosint_wrapper.py` (email+breach+credential+social → social, leak)
- [x] 4.4 `trufflehog_wrapper.py` (secret/token leak → keyword, MASCHERA secrets)
- [x] 4.5 `shodan_wrapper.py` (infra scan + CVE → infrastructure, cve)
- [x] 4.6 `theharvester_wrapper.py` (multi-source OSINT → social, infrastructure)
- [x] 4.7 `dorks_wrapper.py` (DuckDuckGo, 5 categorie dork, rate limit 3-8s)
- [x] 4.8 Tool registry `__init__.py` (6 tool)
- [x] 4.9 Scheduler/orchestrator (`scheduler.py` — scan plan, concorrenza, loop, signal handling)

## M5 — Dashboard v1

- [x] 5.1 Layout HTML/CSS cyberpunk (dashboard.css — OpenCTI-inspired)
- [x] 5.2 `widget-engine.js` (IIFE, auth JWT, GridStack 12col, filtri, auto-refresh 5min)
- [x] 5.3 Widget: SOCIAL FOOTPRINT (card-grid per piattaforma/username)
- [x] 5.4 Widget: INFRASTRUCTURE EXPOSURE (tabella + severity bar)
- [x] 5.5 Widget: CVE FEED (tabella CVE + CVSS + link NVD)
- [x] 5.6 Widget: KEYWORDS (tabella + frequency summary)
- [x] 5.7 Widget: COMPETITORS (card-grid raggruppato per competitor)
- [x] 5.8 Widget: STATUS (VM status grid + Tor + last crawl + total findings)
- [x] 5.9 Widget: TOP ACTIVE BAD ACTORS (tabella attori + threat level)
- [x] 5.10 Widget: TOP ACTIVE CRIMINAL FORUMS (card list + status + mentions)
- [x] 5.11 Widget: ALERTS (tabella deep web alerts + matched text)
- [x] 5.12 Widget: TELEGRAM STATUS (status circle + channels count)
- [x] 5.13 Widget: MONITORED CHANNELS (card list + messages count)
- [x] 5.14 Apache2 config (`apache-mmon.conf` — SSL, proxy, PHP-FPM, SPA fallback)
- [ ] 5.15 Smoke test end-to-end

---

## Note e decisioni

| Data | Nota |
|------|------|
| 2026-04-15 | Rebuild completo allineato a prompt v2: Debian 12, Apache2, tool consolidati VM1, Keycloak Company, widget VM2/VM3 |
