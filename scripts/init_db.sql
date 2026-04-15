-- ─────────────────────────────────────────────────────────────
-- MMON — PostgreSQL 16 Schema Initialization
-- Eseguire su VM0: sudo -u postgres psql mmon_db < init_db.sql
-- ─────────────────────────────────────────────────────────────

-- Estensioni
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── ENUM types ──
DO $$ BEGIN
    CREATE TYPE finding_category AS ENUM (
        'social', 'infrastructure', 'cve', 'keyword', 'leak',
        'competitor', 'deepweb', 'telegram', 'threat_actor'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE finding_severity AS ENUM (
        'critical', 'high', 'medium', 'low', 'info'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE source_vm AS ENUM ('vm1', 'vm2', 'vm3');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE job_status AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE deploy_mode AS ENUM ('personal', 'company');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ── Tabella: users ──
CREATE TABLE IF NOT EXISTS users (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username    VARCHAR(100) UNIQUE NOT NULL,
    email       VARCHAR(255),
    password_hash VARCHAR(255) NOT NULL,
    role        VARCHAR(50) NOT NULL DEFAULT 'analyst',  -- viewer, analyst, admin
    is_active   BOOLEAN NOT NULL DEFAULT true,
    keycloak_id VARCHAR(255),  -- NULL in modalità Personal, popolato in Company
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Tabella: targets ──
CREATE TABLE IF NOT EXISTS targets (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        VARCHAR(255) NOT NULL,
    target_type VARCHAR(50) NOT NULL,  -- domain, ip, email, username, company
    value       TEXT NOT NULL,
    metadata    JSONB DEFAULT '{}',
    is_active   BOOLEAN NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Tabella: findings (cuore del sistema) ──
CREATE TABLE IF NOT EXISTS findings (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_vm   source_vm NOT NULL,
    source_tool VARCHAR(100) NOT NULL,
    category    finding_category NOT NULL,
    severity    finding_severity NOT NULL DEFAULT 'info',
    target_ref  VARCHAR(500) NOT NULL,
    raw_data    JSONB NOT NULL DEFAULT '{}',
    clean_data  JSONB DEFAULT '{}',
    sanitized   BOOLEAN NOT NULL DEFAULT false,
    tags        TEXT[] DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Tabella: jobs ──
CREATE TABLE IF NOT EXISTS jobs (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tool        VARCHAR(100) NOT NULL,
    source_vm   source_vm NOT NULL,
    status      job_status NOT NULL DEFAULT 'pending',
    target_ref  VARCHAR(500),
    params      JSONB DEFAULT '{}',
    result      JSONB DEFAULT '{}',
    error       TEXT,
    started_at  TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Tabella: config ──
CREATE TABLE IF NOT EXISTS config (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key         VARCHAR(255) UNIQUE NOT NULL,
    value       JSONB NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Tabella: audit_log ──
CREATE TABLE IF NOT EXISTS audit_log (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID REFERENCES users(id) ON DELETE SET NULL,
    action      VARCHAR(100) NOT NULL,
    resource    VARCHAR(255),
    details     JSONB DEFAULT '{}',
    ip_address  INET,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Indici ──
CREATE INDEX IF NOT EXISTS idx_findings_category ON findings(category);
CREATE INDEX IF NOT EXISTS idx_findings_severity ON findings(severity);
CREATE INDEX IF NOT EXISTS idx_findings_source_vm ON findings(source_vm);
CREATE INDEX IF NOT EXISTS idx_findings_source_tool ON findings(source_tool);
CREATE INDEX IF NOT EXISTS idx_findings_target_ref ON findings(target_ref);
CREATE INDEX IF NOT EXISTS idx_findings_created_at ON findings(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_findings_sanitized ON findings(sanitized);
CREATE INDEX IF NOT EXISTS idx_findings_raw_data ON findings USING GIN(raw_data);
CREATE INDEX IF NOT EXISTS idx_findings_clean_data ON findings USING GIN(clean_data);
CREATE INDEX IF NOT EXISTS idx_findings_tags ON findings USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_findings_composite ON findings(category, severity, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_tool ON jobs(tool);
CREATE INDEX IF NOT EXISTS idx_jobs_source_vm ON jobs(source_vm);

CREATE INDEX IF NOT EXISTS idx_targets_type ON targets(target_type);
CREATE INDEX IF NOT EXISTS idx_targets_active ON targets(is_active);

CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at DESC);

-- ── Trigger updated_at ──
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$ BEGIN
    CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users
        FOR EACH ROW EXECUTE FUNCTION update_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TRIGGER trg_targets_updated_at BEFORE UPDATE ON targets
        FOR EACH ROW EXECUTE FUNCTION update_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TRIGGER trg_findings_updated_at BEFORE UPDATE ON findings
        FOR EACH ROW EXECUTE FUNCTION update_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TRIGGER trg_config_updated_at BEFORE UPDATE ON config
        FOR EACH ROW EXECUTE FUNCTION update_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ── Utente admin default (password da impostare via wizard) ──
INSERT INTO users (username, password_hash, role)
VALUES ('admin', 'TO_BE_SET_BY_WIZARD', 'admin')
ON CONFLICT (username) DO NOTHING;

-- ── Config deploy mode default ──
INSERT INTO config (key, value)
VALUES ('deploy_mode', '"personal"')
ON CONFLICT (key) DO NOTHING;
