"""
MMON — Configuration loader.
Legge mmon.conf (INI) e espone Settings via Pydantic.
"""
from __future__ import annotations

import configparser
import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel


class Settings(BaseModel):
    """Configurazione MMON caricata da mmon.conf."""

    # general
    deploy_mode: str = "personal"
    instance_name: str = "MMON"

    # target
    company_name: str = ""
    domains: list[str] = []
    public_ips: list[str] = []
    emails: list[str] = []

    # social
    usernames: list[str] = []
    full_names: list[str] = []

    # infrastructure
    backend_ip: str = "127.0.0.1"
    vm1_ip: str = ""
    vm2_ip: str = ""
    vm3_ip: str = ""

    # database
    db_host: str = "127.0.0.1"
    db_port: int = 5432
    db_name: str = "mmon_db"
    db_user: str = "mmon"
    db_password: str = ""

    # redis
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_db: int = 0

    # jwt
    jwt_secret: str = "CHANGE_ME"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # keycloak
    keycloak_enabled: bool = False
    keycloak_server_url: str = ""
    keycloak_realm: str = "mmon"
    keycloak_client_id: str = "mmon-dashboard"
    keycloak_client_secret: str = ""

    # scheduler
    scan_interval_hours: int = 24
    max_concurrent_tools: int = 3

    # api_keys
    shodan_key: str = ""
    criminal_ip_key: str = ""
    quake360_key: str = ""

    # ollama
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:14b"
    ollama_timeout: int = 120

    @property
    def database_url(self) -> str:
        """URL asyncpg per SQLAlchemy async."""
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def database_url_sync(self) -> str:
        """URL psycopg2 per operazioni sync."""
        return f"postgresql+psycopg2://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def vm_whitelist(self) -> list[str]:
        """IP autorizzati per autenticazione VM."""
        ips = [ip for ip in [self.vm1_ip, self.vm2_ip, self.vm3_ip] if ip]
        ips.append("127.0.0.1")
        return ips


def _split_csv(value: str) -> list[str]:
    """Splitta stringa CSV in lista pulita."""
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


@lru_cache()
def get_settings() -> Settings:
    """Factory cached per Settings. Legge da mmon.conf."""
    conf_path = os.environ.get("MMON_CONFIG", "/opt/mmon/config/mmon.conf")

    if not Path(conf_path).exists():
        return Settings()

    cp = configparser.ConfigParser()
    cp.read(conf_path)

    def g(section: str, key: str, default: str = "") -> str:
        return cp.get(section, key, fallback=default).strip()

    return Settings(
        deploy_mode=g("general", "deploy_mode", "personal"),
        instance_name=g("general", "instance_name", "MMON"),
        company_name=g("target", "company_name"),
        domains=_split_csv(g("target", "domains")),
        public_ips=_split_csv(g("target", "public_ips")),
        emails=_split_csv(g("target", "emails")),
        usernames=_split_csv(g("social", "usernames")),
        full_names=_split_csv(g("social", "full_names")),
        backend_ip=g("infrastructure", "backend_ip", "127.0.0.1"),
        vm1_ip=g("infrastructure", "vm1_ip"),
        vm2_ip=g("infrastructure", "vm2_ip"),
        vm3_ip=g("infrastructure", "vm3_ip"),
        db_host=g("database", "host", "127.0.0.1"),
        db_port=int(g("database", "port", "5432")),
        db_name=g("database", "name", "mmon_db"),
        db_user=g("database", "user", "mmon"),
        db_password=g("database", "password"),
        redis_host=g("redis", "host", "127.0.0.1"),
        redis_port=int(g("redis", "port", "6379")),
        redis_db=int(g("redis", "db", "0")),
        jwt_secret=g("jwt", "secret_key", "CHANGE_ME"),
        jwt_algorithm=g("jwt", "algorithm", "HS256"),
        jwt_expire_minutes=int(g("jwt", "expire_minutes", "1440")),
        keycloak_enabled=g("keycloak", "enabled", "false").lower() == "true",
        keycloak_server_url=g("keycloak", "server_url"),
        keycloak_realm=g("keycloak", "realm", "mmon"),
        keycloak_client_id=g("keycloak", "client_id", "mmon-dashboard"),
        keycloak_client_secret=g("keycloak", "client_secret"),
        scan_interval_hours=int(g("scheduler", "scan_interval_hours", "24")),
        max_concurrent_tools=int(g("scheduler", "max_concurrent_tools", "3")),
        shodan_key=g("api_keys", "shodan"),
        criminal_ip_key=g("api_keys", "criminal_ip"),
        quake360_key=g("api_keys", "quake360"),
        ollama_base_url=g("ollama", "base_url", "http://127.0.0.1:11434"),
        ollama_model=g("ollama", "model", "qwen2.5:14b"),
        ollama_timeout=int(g("ollama", "timeout", "120")),
    )
