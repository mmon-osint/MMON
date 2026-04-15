"""
MMON — Pydantic schemas per request/response.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


# ── Enums ──

class FindingCategory(str, Enum):
    social = "social"
    infrastructure = "infrastructure"
    cve = "cve"
    keyword = "keyword"
    leak = "leak"
    competitor = "competitor"
    deepweb = "deepweb"
    telegram = "telegram"
    threat_actor = "threat_actor"


class FindingSeverity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"


class SourceVM(str, Enum):
    vm1 = "vm1"
    vm2 = "vm2"
    vm3 = "vm3"


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


# ── Auth ──

class TokenRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: str | None = None
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


class SetupPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=8, max_length=128)


# ── Findings ──

class FindingCreate(BaseModel):
    source_vm: SourceVM
    source_tool: str = Field(..., min_length=1, max_length=100)
    category: FindingCategory
    severity: FindingSeverity = FindingSeverity.info
    target_ref: str = Field(..., min_length=1, max_length=500)
    raw_data: dict = {}
    clean_data: dict = {}
    tags: list[str] = []

    @field_validator("source_tool")
    @classmethod
    def validate_source_tool(cls, v: str) -> str:
        """Previeni injection nei nomi tool."""
        if not re.match(r"^[a-zA-Z0-9_\-\.]+$", v):
            raise ValueError("source_tool contiene caratteri non ammessi")
        return v


class FindingResponse(BaseModel):
    id: uuid.UUID
    source_vm: str
    source_tool: str
    category: str
    severity: str
    target_ref: str
    raw_data: dict
    clean_data: dict
    sanitized: bool
    tags: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class FindingListResponse(BaseModel):
    items: list[FindingResponse]
    total: int
    page: int
    page_size: int


class FindingFilter(BaseModel):
    category: FindingCategory | None = None
    severity: FindingSeverity | None = None
    source_vm: SourceVM | None = None
    source_tool: str | None = None
    target_ref: str | None = None
    sanitized: bool | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


# ── Jobs ──

class JobCreate(BaseModel):
    tool: str = Field(..., min_length=1, max_length=100)
    source_vm: SourceVM
    target_ref: str | None = None
    params: dict = {}


class JobResponse(BaseModel):
    id: uuid.UUID
    tool: str
    source_vm: str
    status: str
    target_ref: str | None
    params: dict
    result: dict
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Widget responses ──

class WidgetSocialItem(BaseModel):
    username: str
    platform: str
    profile_url: str | None = None
    source_tool: str | None = None
    severity: str = "info"


class WidgetSocialResponse(BaseModel):
    items: list[WidgetSocialItem]
    total_findings: int


class WidgetInfraItem(BaseModel):
    asset: str
    finding_type: str | None = None
    category: str | None = None
    details: str | None = None
    severity: str = "info"
    source_tool: str | None = None
    created_at: datetime | None = None


class WidgetInfraResponse(BaseModel):
    items: list[WidgetInfraItem]
    total_findings: int
    severity_counts: dict[str, int] = {}


class WidgetCVEItem(BaseModel):
    cve_id: str | None = None
    cvss_score: float | None = None
    severity: str = "info"
    affected_product: str | None = None
    description: str | None = None
    created_at: datetime | None = None


class WidgetCVEResponse(BaseModel):
    items: list[WidgetCVEItem]
    total_cves: int


class WidgetKeywordItem(BaseModel):
    keyword: str | None = None
    context: str | None = None
    source_tool: str | None = None
    source_url: str | None = None
    severity: str = "info"
    created_at: datetime | None = None


class WidgetKeywordResponse(BaseModel):
    items: list[WidgetKeywordItem]
    total_hits: int
    keyword_counts: dict[str, int] = {}


class WidgetCompetitorItem(BaseModel):
    competitor_name: str | None = None
    target: str | None = None
    finding_type: str | None = None
    category: str | None = None
    description: str | None = None
    severity: str = "info"
    source_tool: str | None = None


class WidgetCompetitorResponse(BaseModel):
    items: list[WidgetCompetitorItem]
    total_competitors: int


# ── VM2/VM3 Widget responses ──

class WidgetStatusResponse(BaseModel):
    """STATUS widget — uptime motore, Tor status, IP VM, ultimo crawl."""
    vm1_status: str = "unknown"
    vm2_status: str = "unknown"
    vm3_status: str = "unknown"
    tor_connected: bool = False
    tor_exit_ip: str | None = None
    last_crawl_at: datetime | None = None
    total_findings: int = 0


class WidgetBadActorItem(BaseModel):
    actor_name: str
    aliases: list[str] = []
    context: str | None = None
    threat_level: str = "medium"
    last_seen: datetime | None = None
    source: str | None = None


class WidgetBadActorsResponse(BaseModel):
    items: list[WidgetBadActorItem]
    total: int


class WidgetForumItem(BaseModel):
    forum_name: str
    url: str | None = None
    status: str = "active"
    last_crawl: datetime | None = None
    mentions_count: int = 0


class WidgetForumsResponse(BaseModel):
    items: list[WidgetForumItem]
    total: int


class WidgetAlertItem(BaseModel):
    alert_type: str
    source: str | None = None
    matched_text: str | None = None
    context: str | None = None
    severity: str = "high"
    found_at: datetime | None = None


class WidgetAlertsResponse(BaseModel):
    items: list[WidgetAlertItem]
    total: int


class WidgetTelegramStatusResponse(BaseModel):
    status: str = "not_configured"  # active | idle | not_working | not_configured
    connected_at: datetime | None = None
    last_message_at: datetime | None = None
    channels_count: int = 0


class WidgetMonitoredChannelItem(BaseModel):
    channel_name: str
    channel_id: str | None = None
    members_count: int | None = None
    last_message_at: datetime | None = None
    messages_collected: int = 0


class WidgetMonitoredChannelsResponse(BaseModel):
    items: list[WidgetMonitoredChannelItem]
    total: int


# ── Health ──

class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    redis: str
