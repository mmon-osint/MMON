"""
MMON — Findings router: ingestione e query dei findings.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.middleware.auth import authenticate_vm, get_current_user
from models.db_models import Finding, User
from models.schemas import (
    FindingCategory,
    FindingCreate,
    FindingListResponse,
    FindingResponse,
    FindingSeverity,
    SourceVM,
)

router = APIRouter(prefix="/api/v1/findings", tags=["findings"])


@router.post(
    "",
    response_model=FindingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_finding(
    body: FindingCreate,
    vm_name: str = Depends(authenticate_vm),
    db: AsyncSession = Depends(get_db),
) -> FindingResponse:
    """
    Ingestione di un nuovo finding da una VM.
    Autenticazione via IP whitelist + header X-VM-Name.
    """
    # Verificare coerenza: la VM che chiama deve corrispondere a source_vm
    if body.source_vm.value != vm_name:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"VM '{vm_name}' non può inserire findings per '{body.source_vm.value}'",
        )

    finding = Finding(
        source_vm=body.source_vm.value,
        source_tool=body.source_tool,
        category=body.category.value,
        severity=body.severity.value,
        target_ref=body.target_ref,
        raw_data=body.raw_data,
        clean_data=body.clean_data,
        sanitized=body.sanitized,
        tags=body.tags,
    )

    db.add(finding)
    await db.commit()
    await db.refresh(finding)

    return FindingResponse.model_validate(finding)


@router.get("", response_model=FindingListResponse)
async def list_findings(
    category: Optional[FindingCategory] = Query(None),
    severity: Optional[FindingSeverity] = Query(None),
    source_vm: Optional[SourceVM] = Query(None),
    source_tool: Optional[str] = Query(None, max_length=64),
    target_ref: Optional[str] = Query(None, max_length=512),
    sanitized: Optional[bool] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FindingListResponse:
    """
    Query findings con filtri multipli e paginazione.
    Richiede autenticazione JWT.
    """
    query = select(Finding)
    count_query = select(func.count(Finding.finding_id))

    # Applicare filtri
    if category:
        query = query.where(Finding.category == category.value)
        count_query = count_query.where(Finding.category == category.value)
    if severity:
        query = query.where(Finding.severity == severity.value)
        count_query = count_query.where(Finding.severity == severity.value)
    if source_vm:
        query = query.where(Finding.source_vm == source_vm.value)
        count_query = count_query.where(Finding.source_vm == source_vm.value)
    if source_tool:
        query = query.where(Finding.source_tool == source_tool)
        count_query = count_query.where(Finding.source_tool == source_tool)
    if target_ref:
        query = query.where(Finding.target_ref.ilike(f"%{target_ref}%"))
        count_query = count_query.where(Finding.target_ref.ilike(f"%{target_ref}%"))
    if sanitized is not None:
        query = query.where(Finding.sanitized == sanitized)
        count_query = count_query.where(Finding.sanitized == sanitized)
    if date_from:
        query = query.where(Finding.created_at >= date_from)
        count_query = count_query.where(Finding.created_at >= date_from)
    if date_to:
        query = query.where(Finding.created_at <= date_to)
        count_query = count_query.where(Finding.created_at <= date_to)

    # Count totale
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginazione e ordinamento
    offset = (page - 1) * page_size
    query = query.order_by(Finding.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    findings = result.scalars().all()

    return FindingListResponse(
        items=[FindingResponse.model_validate(f) for f in findings],
        total=total,
        page=page,
        page_size=page_size,
    )
