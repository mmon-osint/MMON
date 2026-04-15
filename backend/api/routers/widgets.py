"""
MMON — Widget data endpoints.
Ogni endpoint serve un widget della dashboard, aggregando findings per categoria.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..middleware.auth import get_current_user
from ...models.db_models import Finding, User
from ...models.schemas import (
    WidgetAlertsResponse,
    WidgetAlertItem,
    WidgetBadActorsResponse,
    WidgetBadActorItem,
    WidgetCompetitorItem,
    WidgetCompetitorResponse,
    WidgetCVEItem,
    WidgetCVEResponse,
    WidgetForumItem,
    WidgetForumsResponse,
    WidgetInfraItem,
    WidgetInfraResponse,
    WidgetKeywordItem,
    WidgetKeywordResponse,
    WidgetMonitoredChannelItem,
    WidgetMonitoredChannelsResponse,
    WidgetSocialItem,
    WidgetSocialResponse,
    WidgetStatusResponse,
    WidgetTelegramStatusResponse,
)

router = APIRouter(prefix="/widgets", tags=["widgets"])


# ──────────────── VM1 Widgets ────────────────


@router.get("/social-footprint", response_model=WidgetSocialResponse)
async def widget_social_footprint(
    severity: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WidgetSocialResponse:
    """Widget SOCIAL FOOTPRINT — presenza social per username."""
    query = select(Finding).where(Finding.category == "social")
    if severity:
        sevs = [s.strip() for s in severity.split(",")]
        query = query.where(Finding.severity.in_(sevs))
    query = query.order_by(Finding.created_at.desc()).limit(limit)

    result = await db.execute(query)
    findings = result.scalars().all()

    items = []
    for f in findings:
        cd = f.clean_data or f.raw_data or {}
        items.append(WidgetSocialItem(
            username=cd.get("username", f.target_ref),
            platform=cd.get("platform", cd.get("source", "unknown")),
            profile_url=cd.get("profile_url", cd.get("url")),
            source_tool=f.source_tool,
            severity=f.severity,
        ))

    return WidgetSocialResponse(items=items, total_findings=len(items))


@router.get("/infrastructure", response_model=WidgetInfraResponse)
async def widget_infrastructure(
    severity: str | None = None,
    source_vm: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WidgetInfraResponse:
    """Widget INFRASTRUCTURE EXPOSURE — asset esposti."""
    query = select(Finding).where(Finding.category == "infrastructure")
    if severity:
        sevs = [s.strip() for s in severity.split(",")]
        query = query.where(Finding.severity.in_(sevs))
    if source_vm:
        query = query.where(Finding.source_vm == source_vm)
    query = query.order_by(Finding.created_at.desc()).limit(limit)

    result = await db.execute(query)
    findings = result.scalars().all()

    sev_counts: dict[str, int] = {}
    items = []
    for f in findings:
        cd = f.clean_data or f.raw_data or {}
        sev_counts[f.severity] = sev_counts.get(f.severity, 0) + 1
        items.append(WidgetInfraItem(
            asset=cd.get("host", cd.get("ip", f.target_ref)),
            finding_type=cd.get("type", cd.get("service")),
            details=cd.get("details", cd.get("banner", "")),
            severity=f.severity,
            source_tool=f.source_tool,
            created_at=f.created_at,
        ))

    return WidgetInfraResponse(items=items, total_findings=len(items), severity_counts=sev_counts)


@router.get("/cve-feed", response_model=WidgetCVEResponse)
async def widget_cve_feed(
    severity: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WidgetCVEResponse:
    """Widget CVE FEED — vulnerabilità per tecnologie monitorate."""
    query = select(Finding).where(Finding.category == "cve")
    if severity:
        sevs = [s.strip() for s in severity.split(",")]
        query = query.where(Finding.severity.in_(sevs))
    query = query.order_by(Finding.created_at.desc()).limit(limit)

    result = await db.execute(query)
    findings = result.scalars().all()

    items = []
    for f in findings:
        cd = f.clean_data or f.raw_data or {}
        items.append(WidgetCVEItem(
            cve_id=cd.get("cve_id", cd.get("id")),
            cvss_score=cd.get("cvss", cd.get("cvss_score")),
            severity=f.severity,
            affected_product=cd.get("product", cd.get("technology")),
            description=cd.get("description", cd.get("summary", "")),
            created_at=f.created_at,
        ))

    return WidgetCVEResponse(items=items, total_cves=len(items))


@router.get("/keywords", response_model=WidgetKeywordResponse)
async def widget_keywords(
    severity: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(100, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WidgetKeywordResponse:
    """Widget KEYWORDS — menzioni keyword monitorate."""
    query = select(Finding).where(Finding.category == "keyword")
    if severity:
        sevs = [s.strip() for s in severity.split(",")]
        query = query.where(Finding.severity.in_(sevs))
    if date_from:
        query = query.where(Finding.created_at >= date_from)
    if date_to:
        query = query.where(Finding.created_at <= date_to)
    query = query.order_by(Finding.created_at.desc()).limit(limit)

    result = await db.execute(query)
    findings = result.scalars().all()

    kw_counts: dict[str, int] = {}
    items = []
    for f in findings:
        cd = f.clean_data or f.raw_data or {}
        kw = cd.get("keyword", cd.get("matched_keyword", ""))
        if kw:
            kw_counts[kw] = kw_counts.get(kw, 0) + 1
        items.append(WidgetKeywordItem(
            keyword=kw,
            context=cd.get("context", cd.get("snippet", "")),
            source_tool=f.source_tool,
            source_url=cd.get("url", cd.get("source_url")),
            severity=f.severity,
            created_at=f.created_at,
        ))

    return WidgetKeywordResponse(items=items, total_hits=len(items), keyword_counts=kw_counts)


@router.get("/competitors", response_model=WidgetCompetitorResponse)
async def widget_competitors(
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WidgetCompetitorResponse:
    """Widget COMPETITORS — dati raccolti sui competitor."""
    query = select(Finding).where(Finding.category == "competitor")
    query = query.order_by(Finding.created_at.desc()).limit(limit)

    result = await db.execute(query)
    findings = result.scalars().all()

    competitors_set: set[str] = set()
    items = []
    for f in findings:
        cd = f.clean_data or f.raw_data or {}
        name = cd.get("competitor_name", cd.get("name", f.target_ref))
        competitors_set.add(name)
        items.append(WidgetCompetitorItem(
            competitor_name=name,
            target=f.target_ref,
            finding_type=cd.get("type"),
            description=cd.get("description", ""),
            severity=f.severity,
            source_tool=f.source_tool,
        ))

    return WidgetCompetitorResponse(items=items, total_competitors=len(competitors_set))


# ──────────────── VM2 Widgets ────────────────


@router.get("/status", response_model=WidgetStatusResponse)
async def widget_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WidgetStatusResponse:
    """Widget STATUS — uptime motori, Tor, ultimo crawl."""
    # Count totale findings
    count_result = await db.execute(select(func.count(Finding.id)))
    total = count_result.scalar() or 0

    # Ultimo crawl per VM
    last_crawl_result = await db.execute(
        select(Finding.created_at)
        .where(Finding.source_vm == "vm2")
        .order_by(Finding.created_at.desc())
        .limit(1)
    )
    last_crawl = last_crawl_result.scalar_one_or_none()

    return WidgetStatusResponse(
        total_findings=total,
        last_crawl_at=last_crawl,
        # Stato reale VM: sarebbe popolato da health check asincroni
        # Per ora restituisce "unknown" — integrazione live in M6+
    )


@router.get("/bad-actors", response_model=WidgetBadActorsResponse)
async def widget_bad_actors(
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WidgetBadActorsResponse:
    """Widget TOP ACTIVE BAD ACTORS — attori malevoli dal deep web."""
    query = select(Finding).where(Finding.category == "threat_actor")
    query = query.order_by(Finding.created_at.desc()).limit(limit)

    result = await db.execute(query)
    findings = result.scalars().all()

    items = []
    for f in findings:
        cd = f.clean_data or f.raw_data or {}
        items.append(WidgetBadActorItem(
            actor_name=cd.get("name", cd.get("actor", f.target_ref)),
            aliases=cd.get("aliases", []),
            context=cd.get("context", cd.get("description", "")),
            threat_level=f.severity,
            last_seen=f.created_at,
            source=f.source_tool,
        ))

    return WidgetBadActorsResponse(items=items, total=len(items))


@router.get("/criminal-forums", response_model=WidgetForumsResponse)
async def widget_criminal_forums(
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WidgetForumsResponse:
    """Widget TOP ACTIVE CRIMINAL FORUMS — forum monitorati."""
    query = select(Finding).where(Finding.category == "deepweb")
    query = query.order_by(Finding.created_at.desc()).limit(limit)

    result = await db.execute(query)
    findings = result.scalars().all()

    # Raggruppa per forum
    forums: dict[str, dict] = {}
    for f in findings:
        cd = f.clean_data or f.raw_data or {}
        name = cd.get("forum_name", cd.get("source", f.target_ref))
        if name not in forums:
            forums[name] = {
                "url": cd.get("url"),
                "status": cd.get("status", "active"),
                "last_crawl": f.created_at,
                "count": 0,
            }
        forums[name]["count"] += 1

    items = [
        WidgetForumItem(
            forum_name=name,
            url=data["url"],
            status=data["status"],
            last_crawl=data["last_crawl"],
            mentions_count=data["count"],
        )
        for name, data in forums.items()
    ]

    return WidgetForumsResponse(items=items, total=len(items))


@router.get("/alerts", response_model=WidgetAlertsResponse)
async def widget_alerts(
    severity: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WidgetAlertsResponse:
    """Widget ALERTS — occorrenze target nel deep web."""
    query = select(Finding).where(
        Finding.source_vm == "vm2",
        Finding.category.in_(["deepweb", "leak", "threat_actor"]),
    )
    if severity:
        sevs = [s.strip() for s in severity.split(",")]
        query = query.where(Finding.severity.in_(sevs))
    query = query.order_by(Finding.created_at.desc()).limit(limit)

    result = await db.execute(query)
    findings = result.scalars().all()

    items = []
    for f in findings:
        cd = f.clean_data or f.raw_data or {}
        items.append(WidgetAlertItem(
            alert_type=f.category,
            source=f.source_tool,
            matched_text=cd.get("matched_text", cd.get("keyword", "")),
            context=cd.get("context", cd.get("snippet", "")),
            severity=f.severity,
            found_at=f.created_at,
        ))

    return WidgetAlertsResponse(items=items, total=len(items))


# ──────────────── VM3 Widgets ────────────────


@router.get("/telegram-status", response_model=WidgetTelegramStatusResponse)
async def widget_telegram_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WidgetTelegramStatusResponse:
    """Widget TELEGRAM STATUS — stato crawling Telegram."""
    # Conta findings Telegram
    count_result = await db.execute(
        select(func.count(Finding.id)).where(Finding.source_vm == "vm3")
    )
    count = count_result.scalar() or 0

    # Ultimo messaggio
    last_msg_result = await db.execute(
        select(Finding.created_at)
        .where(Finding.source_vm == "vm3")
        .order_by(Finding.created_at.desc())
        .limit(1)
    )
    last_msg = last_msg_result.scalar_one_or_none()

    status = "not_configured"
    if count > 0:
        status = "active" if last_msg else "idle"

    return WidgetTelegramStatusResponse(
        status=status,
        last_message_at=last_msg,
        channels_count=0,  # Popolato da VM3 engine in M6+
    )


@router.get("/monitored-channels", response_model=WidgetMonitoredChannelsResponse)
async def widget_monitored_channels(
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WidgetMonitoredChannelsResponse:
    """Widget MONITORED CHANNELS — canali Telegram monitorati."""
    query = select(Finding).where(
        Finding.source_vm == "vm3",
        Finding.category == "telegram",
    )
    query = query.order_by(Finding.created_at.desc()).limit(limit)

    result = await db.execute(query)
    findings = result.scalars().all()

    # Raggruppa per canale
    channels: dict[str, dict] = {}
    for f in findings:
        cd = f.clean_data or f.raw_data or {}
        name = cd.get("channel_name", cd.get("channel", f.target_ref))
        if name not in channels:
            channels[name] = {
                "channel_id": cd.get("channel_id"),
                "members_count": cd.get("members_count"),
                "last_message_at": f.created_at,
                "messages": 0,
            }
        channels[name]["messages"] += 1

    items = [
        WidgetMonitoredChannelItem(
            channel_name=name,
            channel_id=data["channel_id"],
            members_count=data["members_count"],
            last_message_at=data["last_message_at"],
            messages_collected=data["messages"],
        )
        for name, data in channels.items()
    ]

    return WidgetMonitoredChannelsResponse(items=items, total=len(items))
