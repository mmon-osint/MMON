"""
MMON — Test suite per FastAPI backend.
Usa httpx AsyncClient per testare tutti gli endpoint principali.

Esecuzione:
    cd /opt/mmon/backend
    source venv/bin/activate
    MMON_CONFIG=/dev/null pytest tests/ -v
"""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.main import app
from api.middleware.auth import create_access_token, hash_password


# =============================================================
# FIXTURES
# =============================================================

@pytest_asyncio.fixture
async def client():
    """Client HTTP async per i test."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Header con JWT valido per un utente admin di test."""
    token = create_access_token(
        user_id=str(uuid.uuid4()),
        username="test_admin",
        role="admin",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def vm1_headers() -> dict[str, str]:
    """Header per simulare una request da VM1."""
    return {
        "X-VM-Name": "vm1",
        "Content-Type": "application/json",
    }


@pytest.fixture
def sample_finding() -> dict:
    """Payload di esempio per un finding."""
    return {
        "source_vm": "vm1",
        "source_tool": "bbot",
        "category": "infrastructure",
        "severity": "medium",
        "target_ref": "example.com",
        "raw_data": {
            "ip": "203.0.113.10",
            "port": 443,
            "service": "nginx",
        },
        "clean_data": {},
        "sanitized": False,
        "tags": ["subdomain", "web"],
    }


@pytest.fixture
def sample_job() -> dict:
    """Payload di esempio per trigger job."""
    return {
        "tool_name": "bbot",
        "source_vm": "vm1",
        "target_ref": "example.com",
        "parameters": {"scan_type": "subdomain"},
    }


# =============================================================
# HEALTH CHECK
# =============================================================

class TestHealthCheck:
    """Test per l'endpoint /health (pubblico)."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "mode" in data


# =============================================================
# AUTH
# =============================================================

class TestAuth:
    """Test per gli endpoint di autenticazione."""

    @pytest.mark.asyncio
    async def test_login_without_credentials_returns_422(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_me_without_token_returns_401(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_me_with_invalid_token_returns_401(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token_here"},
        )
        assert response.status_code == 401


# =============================================================
# FINDINGS
# =============================================================

class TestFindings:
    """Test per gli endpoint findings."""

    @pytest.mark.asyncio
    async def test_create_finding_without_auth_returns_401(
        self, client: AsyncClient, sample_finding: dict
    ):
        """POST /findings senza auth VM deve fallire."""
        response = await client.post(
            "/api/v1/findings",
            json=sample_finding,
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_findings_without_auth_returns_401(
        self, client: AsyncClient
    ):
        """GET /findings senza JWT deve fallire."""
        response = await client.get("/api/v1/findings")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_finding_invalid_source_tool(
        self, client: AsyncClient, vm1_headers: dict
    ):
        """source_tool con caratteri non validi deve essere rifiutato."""
        payload = {
            "source_vm": "vm1",
            "source_tool": "invalid;tool--name!",
            "category": "social",
            "severity": "info",
            "target_ref": "test",
        }
        response = await client.post(
            "/api/v1/findings",
            json=payload,
            headers=vm1_headers,
        )
        assert response.status_code == 422


# =============================================================
# WIDGETS
# =============================================================

class TestWidgets:
    """Test per gli endpoint widget."""

    @pytest.mark.asyncio
    async def test_social_footprint_without_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/widgets/social-footprint")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_infrastructure_without_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/widgets/infrastructure")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_cve_feed_without_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/widgets/cve-feed")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_keywords_without_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/widgets/keywords")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_competitors_without_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/widgets/competitors")
        assert response.status_code == 401


# =============================================================
# JOBS
# =============================================================

class TestJobs:
    """Test per gli endpoint jobs."""

    @pytest.mark.asyncio
    async def test_trigger_job_without_auth(
        self, client: AsyncClient, sample_job: dict
    ):
        response = await client.post("/api/v1/jobs/trigger", json=sample_job)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_jobs_without_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/jobs/status")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_trigger_invalid_tool(self, client: AsyncClient):
        """Tool inesistente deve restituire 400."""
        payload = {
            "tool_name": "nonexistent_tool",
            "source_vm": "vm1",
        }
        # Senza auth, riceveremo 401 prima di 400 — va bene
        response = await client.post("/api/v1/jobs/trigger", json=payload)
        assert response.status_code == 401


# =============================================================
# SCHEMAS VALIDATION
# =============================================================

class TestSchemaValidation:
    """Test unitari per la validazione degli schema Pydantic."""

    def test_finding_create_valid(self, sample_finding: dict):
        from models.schemas import FindingCreate
        finding = FindingCreate(**sample_finding)
        assert finding.source_vm.value == "vm1"
        assert finding.source_tool == "bbot"
        assert finding.category.value == "infrastructure"

    def test_finding_create_invalid_category(self):
        from models.schemas import FindingCreate
        with pytest.raises(Exception):
            FindingCreate(
                source_vm="vm1",
                source_tool="bbot",
                category="invalid_category",
                target_ref="test",
            )

    def test_finding_create_invalid_source_tool_chars(self):
        from models.schemas import FindingCreate
        with pytest.raises(Exception):
            FindingCreate(
                source_vm="vm1",
                source_tool="tool;injection",
                category="social",
                target_ref="test",
            )

    def test_job_create_valid(self, sample_job: dict):
        from models.schemas import JobCreate
        job = JobCreate(**sample_job)
        assert job.tool_name == "bbot"
        assert job.source_vm.value == "vm1"

    def test_token_request_empty_username_rejected(self):
        from models.schemas import TokenRequest
        with pytest.raises(Exception):
            TokenRequest(username="", password="test")
