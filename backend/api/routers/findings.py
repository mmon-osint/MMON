"""
MMON — Findings router: ingest da VM + query da dashboard.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..middleware.auth import authenticate_vm, get_current_user
from ...models.db_models import Finding, User
from ...models.schemas import (
    FindingCategory,
    FindingCreate,
    FindingListResponse,
    FindingResponse,
    FindingSeverity,
    SourceVM,
)

router = APIRouter(prefix="/findings", tags=["findings"])


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=FindingResponse)
async def create_finding(
    body: FindingCreate,
    vm_name: str = Depends(authenticate_vm),
    db: AsyncSession = Depends(get_db),
) -> FindingResponse:
    """Ingest finding da VM. Auth via IP whitelist + X-VM-Name."""
    # Consistenza: source_vm nel body deve matchare header
    if body.source_vm.value != vm_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"source_vm '{body.source_vm.value}' non corrisponde a X-VM-Name '{vm_name}'",
        )

    finding = Finding(
        source_vm=body.source_vm.value,
        source_tool=body.source_tool,
        category=body.category.value,
        severity=body.severity.value,
        target_ref=body.target_ref,
        raw_data=body.raw_data,
        clean_data=body.clean_data,
        tags=body.tags,
    )
    db.add(finding)
    await db.commit()
    await db.refresh(finding)
    return FindingResponse.model_validate(finding)


@router.get("/", response_model=FindingListResponse)
async def list_findings(
    category: FindingCategory | None = None,
    severity: FindingSeverity | None = None,
    source_vm: SourceVM | None = None,
    source_tool: str | None = None,
    target_ref: str | None = None,
    sanitized: bool | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FindingListResponse:
    """Query findings con filtri. Auth via JWT."""
    query = select(Finding)

    if category:
        query = query.where(Finding.category == category.value)
    if severity:
        query = query.where(Finding.severity == severity.value)
    if source_vm:
        query = query.where(Finding.source_vm == source_vm.value)
    if source_tool:
        query = query.where(Finding.source_tool == source_tool)
    if target_ref:
        query = query.where(Finding.target_ref.ilike(f"%{target_ref}%"))
    if sanitized is not None:
        query = query.where(Finding.sanitized == sanitized)
    if date_from:
        query = query.where(Finding.created_at >= date_from)
    if date_to:
        query = query.where(Finding.created_at <= date_to)

    # Count totale
    count_q = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    # Paginazione
    query = query.order_by(Finding.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    items = [FindingResponse.model_validate(f) for f in result.scalars().all()]

    return FindingListResponse(items=items, total=total, page=page, page_size=page_size)
