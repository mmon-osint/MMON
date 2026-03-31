"""
MMON — Jobs router: trigger scansioni e monitoraggio stato.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.middleware.auth import get_current_user, require_role
from models.db_models import Job, User
from models.schemas import (
    JobCreate,
    JobListResponse,
    JobResponse,
    JobStatus,
)

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])

# Tool consentiti per trigger manuale
ALLOWED_TOOLS = {
    "vm1": [
        "bbot", "mosint", "h8mail", "maigret",
        "trufflehog", "spiderfoot", "trape",
        "shodan", "dorks",
    ],
    "vm2": ["ahmia", "torch", "tor_crawler"],
    "vm3": ["telethon"],
}


@router.post(
    "/trigger",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def trigger_job(
    body: JobCreate,
    user: User = Depends(require_role("analyst")),
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """
    Avvia manualmente una scansione con un tool specifico.
    Solo utenti con ruolo 'analyst' o 'admin'.
    """
    vm = body.source_vm.value
    allowed = ALLOWED_TOOLS.get(vm, [])

    if body.tool_name not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tool '{body.tool_name}' non disponibile su {vm}. "
                   f"Tool consentiti: {', '.join(allowed)}",
        )

    # Verificare che non ci sia già un job running per lo stesso tool
    existing = await db.execute(
        select(Job)
        .where(Job.tool_name == body.tool_name)
        .where(Job.source_vm == vm)
        .where(Job.status.in_(["pending", "running"]))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job per '{body.tool_name}' su {vm} già in esecuzione.",
        )

    job = Job(
        tool_name=body.tool_name,
        source_vm=vm,
        status="pending",
        target_ref=body.target_ref,
        parameters=body.parameters,
    )

    db.add(job)
    await db.commit()
    await db.refresh(job)

    # TODO M4: notificare la VM via Redis pub/sub o polling
    # Per ora il job resta in stato 'pending' finché lo scheduler non lo raccoglie.

    return JobResponse.model_validate(job)


@router.get("/status", response_model=JobListResponse)
async def list_jobs(
    status_filter: Optional[JobStatus] = Query(None, alias="status"),
    tool_name: Optional[str] = Query(None, max_length=64),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobListResponse:
    """
    Lista job con filtri opzionali per stato e tool.
    """
    query = select(Job)
    count_query = select(func.count(Job.job_id))

    if status_filter:
        query = query.where(Job.status == status_filter.value)
        count_query = count_query.where(Job.status == status_filter.value)
    if tool_name:
        query = query.where(Job.tool_name == tool_name)
        count_query = count_query.where(Job.tool_name == tool_name)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(Job.created_at.desc()).limit(limit)
    result = await db.execute(query)
    jobs = result.scalars().all()

    return JobListResponse(
        items=[JobResponse.model_validate(j) for j in jobs],
        total=total,
    )


@router.post("/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(
    job_id: str,
    user: User = Depends(require_role("analyst")),
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """Cancella un job in stato pending o running."""
    result = await db.execute(select(Job).where(Job.job_id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job non trovato",
        )

    if job.status not in ("pending", "running"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Impossibile cancellare job in stato '{job.status}'",
        )

    job.status = "cancelled"
    job.completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(job)

    return JobResponse.model_validate(job)
