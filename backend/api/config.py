"""
MMON — Configuration loader
Legge mmon.conf (INI format) e espone un oggetto Settings Pydantic.
"""

import configparser
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configurazione applicativa caricata da mmon.conf + env vars."""

    # General
    mode: str = "personal"

    # Target
    company_name: str = ""
    domains: list[str] = []
    public_ips: list[str] = []
    emails: list[str] = []

    # Social
    usernames: list[str] = []
    full_names: list[str] = []

    # Technologies
    stack: list[str] = []

    # Sector
    industry: str = ""
    products: list[str] = []

    # API Keys
    shodan_key: str = ""
    criminal_ip_key: str = ""
    quake360_key: str = ""

    # Infrastructure
    backend_ip: str = "127.0.0.1"
    vm1_ip: str = ""
    vm2_ip: str = ""
    vm3_ip: str = ""

    # Database
    db_host: str = "127.0.0.1"
    db_port: int = 5432
    db_name: str = "mmon"
    db_user: str = "mmon"
    db_password: str = ""

    # Redis
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379

    # JWT
    jwt_secret_key: str = "CHANGE_ME"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # Ollama
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:14b"

    # Scheduler
    scan_interval_hours: int = 24
    max_concurrent_tools: int = 3

    @property
    def database_url(self) -> str:
        """Connection string PostgreSQL per SQLAlchemy async."""
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def database_url_sync(self) -> str:
        """Connection string PostgreSQL sincrona (per Alembic/test)."""
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def redis_url(self) -> str:
        """Connection string Redis."""
        return f"redis://{self.redis_host}:{self.redis_port}/0"


def _parse_csv(value: str) -> list[str]:
    """Splitta stringa CSV in lista, rimuovendo spazi e vuoti."""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def load_from_conf(conf_path: str) -> Settings:
    """
    Carica Settings da un file mmon.conf (INI format).

    Args:
        conf_path: Path assoluto al file mmon.conf

    Returns:
        Settings popolato dai valori del file

    Raises:
        FileNotFoundError: se il file non esiste
    """
    path = Path(conf_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file non trovato: {conf_path}")

    parser = configparser.ConfigParser()
    parser.read(conf_path)

    kwargs: dict = {}

    # [general]
    if parser.has_section("general"):
        kwargs["mode"] = parser.get("general", "mode", fallback="personal")

    # [target]
    if parser.has_section("target"):
        kwargs["company_name"] = parser.get("target", "company_name", fallback="")
        kwargs["domains"] = _parse_csv(parser.get("target", "domains", fallback=""))
        kwargs["public_ips"] = _parse_csv(parser.get("target", "public_ips", fallback=""))
        kwargs["emails"] = _parse_csv(parser.get("target", "emails", fallback=""))

    # [social]
    if parser.has_section("social"):
        kwargs["usernames"] = _parse_csv(parser.get("social", "usernames", fallback=""))
        kwargs["full_names"] = _parse_csv(parser.get("social", "full_names", fallback=""))

    # [technologies]
    if parser.has_section("technologies"):
        kwargs["stack"] = _parse_csv(parser.get("technologies", "stack", fallback=""))

    # [sector]
    if parser.has_section("sector"):
        kwargs["industry"] = parser.get("sector", "industry", fallback="")
        kwargs["products"] = _parse_csv(parser.get("sector", "products", fallback=""))

    # [api_keys]
    if parser.has_section("api_keys"):
        kwargs["shodan_key"] = parser.get("api_keys", "shodan_key", fallback="")
        kwargs["criminal_ip_key"] = parser.get("api_keys", "criminal_ip_key", fallback="")
        kwargs["quake360_key"] = parser.get("api_keys", "quake360_key", fallback="")

    # [infrastructure]
    if parser.has_section("infrastructure"):
        kwargs["backend_ip"] = parser.get("infrastructure", "backend_ip", fallback="127.0.0.1")
        kwargs["vm1_ip"] = parser.get("infrastructure", "vm1_ip", fallback="")
        kwargs["vm2_ip"] = parser.get("infrastructure", "vm2_ip", fallback="")
        kwargs["vm3_ip"] = parser.get("infrastructure", "vm3_ip", fallback="")

    # [database]
    if parser.has_section("database"):
        kwargs["db_host"] = parser.get("database", "host", fallback="127.0.0.1")
        kwargs["db_port"] = parser.getint("database", "port", fallback=5432)
        kwargs["db_name"] = parser.get("database", "name", fallback="mmon")
        kwargs["db_user"] = parser.get("database", "user", fallback="mmon")
        kwargs["db_password"] = parser.get("database", "password", fallback="")

    # [redis]
    if parser.has_section("redis"):
        kwargs["redis_host"] = parser.get("redis", "host", fallback="127.0.0.1")
        kwargs["redis_port"] = parser.getint("redis", "port", fallback=6379)

    # [jwt]
    if parser.has_section("jwt"):
        kwargs["jwt_secret_key"] = parser.get("jwt", "secret_key", fallback="CHANGE_ME")
        kwargs["jwt_algorithm"] = parser.get("jwt", "algorithm", fallback="HS256")
        kwargs["jwt_expire_minutes"] = parser.getint("jwt", "access_token_expire_minutes", fallback=60)

    # [ollama]
    if parser.has_section("ollama"):
        kwargs["ollama_base_url"] = parser.get("ollama", "base_url", fallback="http://127.0.0.1:11434")
        kwargs["ollama_model"] = parser.get("ollama", "model", fallback="qwen2.5:14b")

    # [scheduler]
    if parser.has_section("scheduler"):
        kwargs["scan_interval_hours"] = parser.getint("scheduler", "scan_interval_hours", fallback=24)
        kwargs["max_concurrent_tools"] = parser.getint("scheduler", "max_concurrent_tools", fallback=3)

    return Settings(**kwargs)


@lru_cache()
def get_settings() -> Settings:
    """
    Factory cached per Settings.
    Cerca mmon.conf nel path da env var MMON_CONFIG o nel default.
    """
    conf_path = os.environ.get("MMON_CONFIG", "/opt/mmon/config/mmon.conf")

    if Path(conf_path).exists():
        return load_from_conf(conf_path)

    # Fallback: Settings con default (per sviluppo/test)
    return Settings()
