"""
MMON — Jobs router: trigger, status, cancel scans.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..middleware.auth import get_current_user, require_role
from ...models.db_models import Job, User
from ...models.schemas import JobCreate, JobResponse, JobStatus

router = APIRouter(prefix="/jobs", tags=["jobs"])

# Tool ammessi per VM
ALLOWED_TOOLS: dict[str, list[str]] = {
    "vm1": ["bbot", "mosint", "trufflehog", "shodan", "theharvester", "dorks"],
    "vm2": ["ahmia", "torch", "tor_crawler", "puppet_manager"],
    "vm3": ["telethon", "informer"],
}


@router.post("/trigger", status_code=status.HTTP_201_CREATED, response_model=JobResponse)
async def trigger_job(
    body: JobCreate,
    user: User = Depends(require_role("analyst")),
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """Avvia un job di scan. Richiede ruolo analyst+."""
    # Valida tool per la VM
    allowed = ALLOWED_TOOLS.get(body.source_vm.value, [])
    if body.tool not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tool '{body.tool}' non ammesso per {body.source_vm.value}. Ammessi: {allowed}",
        )

    # Check job duplicato in esecuzione
    existing = await db.execute(
        select(Job).where(
            Job.tool == body.tool,
            Job.source_vm == body.source_vm.value,
            Job.status.in_(["pending", "running"]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job '{body.tool}' già in esecuzione su {body.source_vm.value}",
        )

    job = Job(
        tool=body.tool,
        source_vm=body.source_vm.value,
        target_ref=body.target_ref,
        params=body.params,
        status="pending",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return JobResponse.model_validate(job)


@router.get("/status", response_model=list[JobResponse])
async def list_jobs(
    status_filter: JobStatus | None = Query(None, alias="status"),
    tool: str | None = None,
    source_vm: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[JobResponse]:
    """Lista job con filtri opzionali."""
    query = select(Job)
    if status_filter:
        query = query.where(Job.status == status_filter.value)
    if tool:
        query = query.where(Job.tool == tool)
    if source_vm:
        query = query.where(Job.source_vm == source_vm)
    query = query.order_by(Job.created_at.desc()).limit(limit)

    result = await db.execute(query)
    return [JobResponse.model_validate(j) for j in result.scalars().all()]


@router.post("/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(
    job_id: uuid.UUID,
    user: User = Depends(require_role("analyst")),
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """Cancella un job pending o running."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job non trovato")

    if job.status not in ("pending", "running"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Impossibile cancellare job con status '{job.status}'",
        )

    job.status = "cancelled"
    job.finished_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(job)
    return JobResponse.model_validate(job)
