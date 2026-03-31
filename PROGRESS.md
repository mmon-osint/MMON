# MMON — Progress Tracker
> Ultimo aggiornamento: 2026-03-28

---

## Legenda stati
- [x] Completato
- [~] In corso
- [ ] Da fare
- [!] Bloccato / problema

---

## M1 — Scaffold + Provisioning (Settimana 1)

- [x] 1.1 Struttura filesystem `/opt/mmon/` nel repo
- [x] 1.2 `setup_backend.sh` — Python 3.12, PostgreSQL 16, Redis 7, Nginx, PHP 8.x, Ollama
- [x] 1.3 `setup_vm1.sh` — Python 3.12, venv, dipendenze tool OSINT
- [x] 1.4 Unit file systemd per `mmon-api`, `mmon-clearnet-engine`, `mmon-scheduler` (inclusi nei setup scripts)
- [x] 1.5 Schema SQL iniziale PostgreSQL (findings, targets, config, users, jobs, audit_log)
- [x] 1.6 `setup_vm2.sh` e `setup_vm3.sh` — scaffold + Tor/nftables/Telethon
- [x] 1.7 README con istruzioni setup e pre-requisiti

## M2 — Setup Wizard PHP (Settimana 2)

- [x] 2.1 Nginx config per servire wizard PHP su `:8080/wizard` (inclusa in setup_backend.sh)
- [x] 2.2 Step 1 — Selezione modalità Personal / Company
- [x] 2.3 Step 2 — Dati target (nome azienda, domini, IP, email)
- [x] 2.4 Step 3 — Username e nominativi da monitorare
- [x] 2.5 Step 4 — Tecnologie utilizzate (CVE feed)
- [x] 2.6 Step 5 — Settore e prodotti (Competitors)
- [x] 2.7 Step 6 — API keys opzionali (Shodan, Criminal IP, Quake360) con test connessione
- [x] 2.8 Step 7 — IP delle 3 VM + config Tor/Telegram
- [x] 2.9 Generazione `mmon.conf` + inizializzazione DB (in complete.php)
- [x] 2.10 Pagina riepilogo + redirect dashboard
- [x] 2.11 Lock wizard dopo primo setup (file .wizard_completed)

## M3 — FastAPI Backend (Settimane 3-4)

- [x] 3.1 Scaffold FastAPI + Uvicorn + config loader (api/main.py, api/config.py, api/database.py)
- [x] 3.2 Modelli SQLAlchemy/Pydantic (models/db_models.py, models/schemas.py)
- [x] 3.3 Auth JWT — login, token, middleware, role-based, VM auth (api/middleware/auth.py, routers/auth.py)
- [x] 3.4 `POST /api/v1/findings` — ingestione finding con validazione schema
- [x] 3.5 `GET /api/v1/findings` — query con filtri multipli + paginazione
- [x] 3.6 Rate limiting (slowapi 100/min) + input sanitization + content-type check
- [x] 3.7 `GET /api/v1/widgets/social-footprint`
- [x] 3.8 `GET /api/v1/widgets/infrastructure`
- [x] 3.9 `GET /api/v1/widgets/cve-feed`
- [x] 3.10 `GET /api/v1/widgets/keywords`
- [x] 3.11 `GET /api/v1/widgets/competitors`
- [x] 3.12 `POST /api/v1/jobs/trigger` con validazione tool + conflict check
- [x] 3.13 `GET /api/v1/jobs/status` + `POST /jobs/{id}/cancel`
- [x] 3.14 Systemd unit `mmon-api.service` (già in setup_backend.sh)
- [x] 3.15 Test suite pytest (tests/test_api.py — health, auth, findings, widgets, jobs, schemas)

## M4 — VM1 Tool Wrapper (Settimane 5-6)

- [x] 4.1 Base class `ToolWrapper` — run_command sicuro, retry, submit finding, temp dir
- [x] 4.2 Wrapper bbot — subdomain enum, IP discovery, port severity mapping
- [x] 4.3 Wrapper mosint — email OSINT, breach check, social lookup
- [x] 4.4 Wrapper h8mail — credential leak con JSON output parsing
- [x] 4.5 Wrapper maigret — username tracking multi-piattaforma
- [x] 4.6 Wrapper trufflehog — secret detection su GitHub org/repo, masked output
- [x] 4.7 Wrapper spiderfoot — OSINT multi-source con event type mapping
- [x] 4.8 Wrapper trape — tracking exposure analysis
- [x] 4.9 Wrapper Shodan API — host/search/dns, CVE extraction
- [x] 4.10 Custom scraper Google Dorks — DuckDuckGo, 5 categorie dork, anti-ban
- [x] 4.11 `scheduler.py` — orchestratore con scan plan, concurrency, loop, report
- [x] 4.12 Systemd unit engine + scheduler (già in setup_vm1.sh)
- [x] 4.13 Error handling e retry logic (in base.py — max_retries, exponential backoff)

## M5 — Dashboard v1 (Settimane 7-8)

- [x] 5.1 Layout base HTML/CSS cyberpunk (dashboard.css — tema dark, neon, grid layout, severity badges)
- [x] 5.2 `widget-engine.js` — caricamento modulare widget (IIFE, auth JWT, apiFetch, lifecycle)
- [x] 5.3 Sistema drag & resize (GridStack 12 colonne, 80px cellHeight, salvataggio posizioni)
- [x] 5.4 Widget SOCIAL FOOTPRINT (card-grid per piattaforma, raggruppamento per username)
- [x] 5.5 Widget INFRASTRUCTURE EXPOSURE (tabella asset/type/details/severity, severity summary bar)
- [x] 5.6 Integrazione HTMX (incluso in index.html, disponibile per widget futuri)
- [x] 5.7 Widget CVE FEED (tabella CVE con CVSS color coding, link NVD, severity mapping)
- [x] 5.8 Widget KEYWORDS (tabella keyword hits, frequency summary, source links)
- [x] 5.9 Widget COMPETITORS (card-grid raggruppato per competitor, severity breakdown)
- [x] 5.10 Sidebar navigazione + filtri (severity toggle, VM select, date range, quick stats)
- [x] 5.11 Salvataggio layout localStorage (save/load/reset in widget-engine.js)
- [x] 5.12 Responsive base (1024px+ — sidebar hidden sotto 1024px)
- [x] 5.13 Nginx config dashboard + proxy FastAPI (config/nginx-dashboard.conf, SSL, security headers)
- [ ] 5.14 Smoke test end-to-end
- [ ] 5.15 Fix bug + polish UI

---

## Note e decisioni

| Data | Nota |
|---|---|
| 2026-03-28 | Progetto iniziato. Creata struttura repo e PROGRESS.md |
| 2026-03-28 | M1 COMPLETATA: scaffold filesystem, 4 script provisioning, schema SQL, unit systemd, README |
| 2026-03-28 | M2 COMPLETATA: wizard PHP 7 step + riepilogo + generazione mmon.conf + init DB + lock + CSS cyberpunk |
| 2026-03-28 | M3 COMPLETATA: FastAPI backend completo — config, DB, auth JWT, findings CRUD, 5 widget endpoint, jobs, rate limit, test suite |
| 2026-03-28 | M4 COMPLETATA: 9 tool wrapper (bbot, mosint, h8mail, maigret, trufflehog, shodan, spiderfoot, trape, dorks) + scheduler + registry |
| 2026-03-28 | M5 QUASI COMPLETATA: dashboard cyberpunk (HTML/CSS/JS), widget-engine, 5 widget, filtri sidebar, GridStack, Nginx config. Manca smoke test + polish |

---

## Problemi aperti

_Nessuno al momento._
