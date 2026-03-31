"""
MMON — Widget endpoints: aggregano findings per la dashboard.
Ogni endpoint serve dati pronti per un widget specifico.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.middleware.auth import get_current_user
from models.db_models import Finding, User
from models.schemas import (
    WidgetCompetitorItem,
    WidgetCompetitorResponse,
    WidgetCveItem,
    WidgetCveResponse,
    WidgetInfraItem,
    WidgetInfraResponse,
    WidgetKeywordItem,
    WidgetKeywordResponse,
    WidgetSocialItem,
    WidgetSocialResponse,
)

router = APIRouter(prefix="/api/v1/widgets", tags=["widgets"])


@router.get("/social-footprint", response_model=WidgetSocialResponse)
async def widget_social_footprint(
    limit: int = Query(100, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WidgetSocialResponse:
    """
    Widget SOCIAL FOOTPRINT — presenza social per username/nome.
    Aggrega findings con category='social' da maigret, mosint.
    """
    result = await db.execute(
        select(Finding)
        .where(Finding.category == "social")
        .order_by(Finding.created_at.desc())
        .limit(limit)
    )
    findings = result.scalars().all()

    items = []
    platforms_set = set()
    for f in findings:
        clean = f.clean_data or f.raw_data or {}
        platform = clean.get("platform", f.source_tool)
        platforms_set.add(platform)
        items.append(WidgetSocialItem(
            platform=platform,
            username=clean.get("username", f.target_ref),
            profile_url=clean.get("profile_url"),
            status=clean.get("status", "found"),
            source_tool=f.source_tool,
            found_at=f.created_at,
        ))

    return WidgetSocialResponse(
        items=items,
        total_platforms=len(platforms_set),
        total_profiles=len(items),
    )


@router.get("/infrastructure", response_model=WidgetInfraResponse)
async def widget_infrastructure(
    limit: int = Query(100, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WidgetInfraResponse:
    """
    Widget INFRASTRUCTURE EXPOSURE — IP, porte, servizi esposti.
    Aggrega findings con category='infrastructure' da bbot, Shodan.
    """
    result = await db.execute(
        select(Finding)
        .where(Finding.category == "infrastructure")
        .order_by(Finding.severity.desc(), Finding.created_at.desc())
        .limit(limit)
    )
    findings = result.scalars().all()

    items = []
    ips_set = set()
    for f in findings:
        clean = f.clean_data or f.raw_data or {}
        ip = clean.get("ip", f.target_ref)
        ips_set.add(ip)
        items.append(WidgetInfraItem(
            ip=ip,
            port=clean.get("port"),
            service=clean.get("service"),
            version=clean.get("version"),
            severity=f.severity,
            source_tool=f.source_tool,
            found_at=f.created_at,
        ))

    return WidgetInfraResponse(
        items=items,
        total_ips=len(ips_set),
        total_services=len(items),
    )


@router.get("/cve-feed", response_model=WidgetCveResponse)
async def widget_cve_feed(
    limit: int = Query(100, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WidgetCveResponse:
    """
    Widget CVE FEED — vulnerabilità sulle tecnologie dichiarate.
    Aggrega findings con category='cve'.
    """
    result = await db.execute(
        select(Finding)
        .where(Finding.category == "cve")
        .order_by(Finding.severity.desc(), Finding.created_at.desc())
        .limit(limit)
    )
    findings = result.scalars().all()

    items = []
    for f in findings:
        clean = f.clean_data or f.raw_data or {}
        cve_id = clean.get("cve_id", f.target_ref)
        items.append(WidgetCveItem(
            cve_id=cve_id,
            technology=clean.get("technology", ""),
            severity=f.severity,
            description=clean.get("description"),
            cvss_score=clean.get("cvss_score"),
            nvd_url=clean.get("nvd_url", f"https://nvd.nist.gov/vuln/detail/{cve_id}"),
            published_at=clean.get("published_at"),
        ))

    return WidgetCveResponse(items=items, total=len(items))


@router.get("/keywords", response_model=WidgetKeywordResponse)
async def widget_keywords(
    limit: int = Query(100, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WidgetKeywordResponse:
    """
    Widget KEYWORDS — risultati Google Dorks raggruppati per query.
    Aggrega findings con category='keyword'.
    """
    result = await db.execute(
        select(Finding)
        .where(Finding.category == "keyword")
        .order_by(Finding.created_at.desc())
        .limit(limit)
    )
    findings = result.scalars().all()

    items = []
    for f in findings:
        clean = f.clean_data or f.raw_data or {}
        items.append(WidgetKeywordItem(
            query=clean.get("query", ""),
            title=clean.get("title", f.target_ref),
            url=clean.get("url", ""),
            snippet=clean.get("snippet"),
            engine=clean.get("engine", "google"),
            found_at=f.created_at,
        ))

    return WidgetKeywordResponse(items=items, total=len(items))


@router.get("/competitors", response_model=WidgetCompetitorResponse)
async def widget_competitors(
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WidgetCompetitorResponse:
    """
    Widget COMPETITORS — aziende e prodotti competitor.
    Aggrega findings con category='competitor'.
    """
    result = await db.execute(
        select(Finding)
        .where(Finding.category == "competitor")
        .order_by(Finding.created_at.desc())
        .limit(limit)
    )
    findings = result.scalars().all()

    items = []
    for f in findings:
        clean = f.clean_data or f.raw_data or {}
        items.append(WidgetCompetitorItem(
            name=clean.get("name", f.target_ref),
            domain=clean.get("domain"),
            description=clean.get("description"),
            similarity_score=clean.get("similarity_score"),
            source_tool=f.source_tool,
        ))

    return WidgetCompetitorResponse(items=items, total=len(items))
