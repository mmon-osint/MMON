-- MMON — Schema iniziale PostgreSQL 16
-- Eseguire con: sudo -u postgres psql -f init_db.sql

-- =============================================================
-- DATABASE E RUOLO
-- =============================================================

CREATE ROLE mmon WITH LOGIN PASSWORD 'CHANGE_ME';
CREATE DATABASE mmon OWNER mmon;

\c mmon

-- Estensioni
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- =============================================================
-- ENUM TYPES
-- =============================================================

CREATE TYPE finding_category AS ENUM (
    'social',
    'infrastructure',
    'cve',
    'keyword',
    'leak',
    'competitor',
    'deepweb',
    'telegram',
    'threat_actor'
);

CREATE TYPE finding_severity AS ENUM (
    'critical',
    'high',
    'medium',
    'low',
    'info'
);

CREATE TYPE source_vm AS ENUM (
    'vm1',
    'vm2',
    'vm3'
);

CREATE TYPE job_status AS ENUM (
    'pending',
    'running',
    'completed',
    'failed',
    'cancelled'
);

CREATE TYPE deploy_mode AS ENUM (
    'personal',
    'company'
);

-- =============================================================
-- TABELLA: users
-- =============================================================

CREATE TABLE users (
    user_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username        VARCHAR(128) NOT NULL UNIQUE,
    password_hash   VARCHAR(256) NOT NULL,
    email           VARCHAR(256),
    role            VARCHAR(64) DEFAULT 'analyst',
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_username ON users (username);

-- =============================================================
-- TABELLA: targets
-- =============================================================

CREATE TABLE targets (
    target_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_name    VARCHAR(256),
    domains         TEXT[],
    public_ips      TEXT[],
    emails          TEXT[],
    usernames       TEXT[],
    full_names      TEXT[],
    technologies    TEXT[],
    industry        VARCHAR(128),
    products        TEXT[],
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================
-- TABELLA: findings (tabella principale)
-- =============================================================

CREATE TABLE findings (
    finding_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_vm       source_vm NOT NULL,
    source_tool     VARCHAR(64) NOT NULL,
    category        finding_category NOT NULL,
    severity        finding_severity NOT NULL DEFAULT 'info',
    target_ref      VARCHAR(512) NOT NULL,
    raw_data        JSONB DEFAULT '{}',
    clean_data      JSONB DEFAULT '{}',
    sanitized       BOOLEAN DEFAULT FALSE,
    tags            TEXT[] DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Indici per query frequenti dai widget
CREATE INDEX idx_findings_category ON findings (category);
CREATE INDEX idx_findings_severity ON findings (severity);
CREATE INDEX idx_findings_source_vm ON findings (source_vm);
CREATE INDEX idx_findings_source_tool ON findings (source_tool);
CREATE INDEX idx_findings_target_ref ON findings (target_ref);
CREATE INDEX idx_findings_created_at ON findings (created_at DESC);
CREATE INDEX idx_findings_sanitized ON findings (sanitized);
CREATE INDEX idx_findings_raw_data ON findings USING GIN (raw_data);
CREATE INDEX idx_findings_clean_data ON findings USING GIN (clean_data);
CREATE INDEX idx_findings_tags ON findings USING GIN (tags);

-- Indice composto per widget query tipiche
CREATE INDEX idx_findings_cat_sev_time ON findings (category, severity, created_at DESC);

-- =============================================================
-- TABELLA: jobs
-- =============================================================

CREATE TABLE jobs (
    job_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tool_name       VARCHAR(64) NOT NULL,
    source_vm       source_vm NOT NULL,
    status          job_status DEFAULT 'pending',
    target_ref      VARCHAR(512),
    parameters      JSONB DEFAULT '{}',
    result_summary  JSONB DEFAULT '{}',
    findings_count  INTEGER DEFAULT 0,
    error_message   TEXT,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_jobs_status ON jobs (status);
CREATE INDEX idx_jobs_tool ON jobs (tool_name);
CREATE INDEX idx_jobs_created_at ON jobs (created_at DESC);

-- =============================================================
-- TABELLA: config
-- =============================================================

CREATE TABLE config (
    config_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deploy_mode     deploy_mode DEFAULT 'personal',
    wizard_completed BOOLEAN DEFAULT FALSE,
    api_keys        JSONB DEFAULT '{}',     -- encrypted at application level
    vm_ips          JSONB DEFAULT '{}',
    scheduler_config JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================
-- TABELLA: audit_log
-- =============================================================

CREATE TABLE audit_log (
    log_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(user_id),
    action          VARCHAR(128) NOT NULL,
    resource_type   VARCHAR(64),
    resource_id     UUID,
    details         JSONB DEFAULT '{}',
    ip_address      INET,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_created_at ON audit_log (created_at DESC);
CREATE INDEX idx_audit_user ON audit_log (user_id);

-- =============================================================
-- FUNZIONE: updated_at trigger
-- =============================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_targets_updated_at
    BEFORE UPDATE ON targets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_findings_updated_at
    BEFORE UPDATE ON findings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_config_updated_at
    BEFORE UPDATE ON config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================
-- UTENTE DEFAULT (Personal mode)
-- =============================================================

INSERT INTO users (username, password_hash, role)
VALUES ('admin', 'TO_BE_SET_BY_WIZARD', 'admin');

-- =============================================================
-- GRANT
-- =============================================================

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO mmon;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO mmon;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO mmon;

-- Fine schema iniziale
