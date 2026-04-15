"""
MMON — API Test Suite.
Test senza DB reale: verifica schema, auth, e validazione.
"""
import pytest
from pydantic import ValidationError

from backend.models.schemas import (
    FindingCategory,
    FindingCreate,
    FindingSeverity,
    JobCreate,
    SourceVM,
    TokenRequest,
)


# ── Schema validation tests ──

class TestFindingCreate:
    def test_valid_finding(self):
        f = FindingCreate(
            source_vm=SourceVM.vm1,
            source_tool="bbot",
            category=FindingCategory.infrastructure,
            severity=FindingSeverity.high,
            target_ref="example.com",
            raw_data={"ip": "1.2.3.4"},
        )
        assert f.source_vm == SourceVM.vm1
        assert f.category == FindingCategory.infrastructure

    def test_invalid_category(self):
        with pytest.raises(ValidationError):
            FindingCreate(
                source_vm=SourceVM.vm1,
                source_tool="bbot",
                category="nonexistent",
                target_ref="example.com",
            )

    def test_source_tool_injection(self):
        with pytest.raises(ValidationError):
            FindingCreate(
                source_vm=SourceVM.vm1,
                source_tool="bbot; rm -rf /",
                category=FindingCategory.social,
                target_ref="example.com",
            )

    def test_source_tool_valid_chars(self):
        f = FindingCreate(
            source_vm=SourceVM.vm1,
            source_tool="the-harvester_v2.0",
            category=FindingCategory.social,
            target_ref="example.com",
        )
        assert f.source_tool == "the-harvester_v2.0"

    def test_empty_target_ref(self):
        with pytest.raises(ValidationError):
            FindingCreate(
                source_vm=SourceVM.vm1,
                source_tool="bbot",
                category=FindingCategory.infrastructure,
                target_ref="",
            )

    def test_all_categories(self):
        for cat in FindingCategory:
            f = FindingCreate(
                source_vm=SourceVM.vm1,
                source_tool="test",
                category=cat,
                target_ref="target",
            )
            assert f.category == cat

    def test_deepweb_category(self):
        f = FindingCreate(
            source_vm=SourceVM.vm2,
            source_tool="torch",
            category=FindingCategory.deepweb,
            severity=FindingSeverity.high,
            target_ref="onionsite.onion",
        )
        assert f.category == FindingCategory.deepweb

    def test_threat_actor_category(self):
        f = FindingCreate(
            source_vm=SourceVM.vm2,
            source_tool="tor_crawler",
            category=FindingCategory.threat_actor,
            target_ref="actor_alias",
        )
        assert f.category == FindingCategory.threat_actor

    def test_telegram_category(self):
        f = FindingCreate(
            source_vm=SourceVM.vm3,
            source_tool="telethon",
            category=FindingCategory.telegram,
            target_ref="channel_name",
        )
        assert f.category == FindingCategory.telegram


class TestJobCreate:
    def test_valid_job(self):
        j = JobCreate(
            tool="bbot",
            source_vm=SourceVM.vm1,
            target_ref="example.com",
        )
        assert j.tool == "bbot"

    def test_empty_tool(self):
        with pytest.raises(ValidationError):
            JobCreate(tool="", source_vm=SourceVM.vm1)


class TestTokenRequest:
    def test_empty_username(self):
        with pytest.raises(ValidationError):
            TokenRequest(username="", password="secret")

    def test_empty_password(self):
        with pytest.raises(ValidationError):
            TokenRequest(username="admin", password="")

    def test_valid(self):
        t = TokenRequest(username="admin", password="secret123")
        assert t.username == "admin"
