"""
tests/test_identity_consumer.py

Unit tests for the IdentityConsumer service.
Covers: basic verification, tax authority checks, driving licence checks,
authorisation enforcement, and handling of non-existent identities.
"""

import pytest
from datetime import datetime, timedelta, timezone

from audit.audit_log import AuditLog
from auth.authorisation import OrganisationType, AuthorisationError
from models.digital_id import IDStatus
from services.identity_manager import IdentityManager
from services.identity_consumer import IdentityConsumer

CA = OrganisationType.CENTRAL_AUTHORITY


@pytest.fixture
def setup():
    """Provides a fresh manager and consumer with a single active identity (GB-001)."""
    audit = AuditLog()
    manager = IdentityManager(audit)
    consumer = IdentityConsumer(manager, audit)
    manager.create_identity(CA, "GB-001", "1985-04-12",
                            "Alice Mensah", "10 Elm St", "alice@example.com")
    return manager, consumer


# ------------------------------------------------------------------ #
# Basic verification
# ------------------------------------------------------------------ #

class TestBasicVerification:
    def test_active_identity_returns_valid(self, setup):
        _, consumer = setup
        result = consumer.verify_basic(OrganisationType.EMPLOYER, "GB-001")
        assert result["valid"] is True

    def test_revoked_identity_returns_invalid(self, setup):
        manager, consumer = setup
        manager.change_status(CA, "GB-001", IDStatus.REVOKED)
        result = consumer.verify_basic(OrganisationType.BANK, "GB-001")
        assert result["valid"] is False

    def test_suspended_identity_returns_invalid(self, setup):
        manager, consumer = setup
        manager.change_status(CA, "GB-001", IDStatus.SUSPENDED)
        result = consumer.verify_basic(OrganisationType.EMPLOYER, "GB-001")
        assert result["valid"] is False

    def test_nonexistent_identity_returns_invalid(self, setup):
        _, consumer = setup
        result = consumer.verify_basic(OrganisationType.EMPLOYER, "GB-999")
        assert result["valid"] is False

    def test_tax_authority_cannot_use_basic_verify(self, setup):
        _, consumer = setup
        with pytest.raises(AuthorisationError):
            consumer.verify_basic(OrganisationType.TAX_AUTHORITY, "GB-001")

    def test_basic_verify_is_recorded_in_audit_log(self, setup):
        manager, consumer = setup
        audit = AuditLog()
        mgr = IdentityManager(audit)
        cons = IdentityConsumer(mgr, audit)
        mgr.create_identity(CA, "GB-010", "1990-01-01", "Test", "Addr", "t@t.com")
        cons.verify_basic(OrganisationType.EMPLOYER, "GB-010")
        entries = audit.get_by_id("GB-010")
        actions = [e["action"] for e in entries]
        assert "VERIFY_BASIC" in actions


# ------------------------------------------------------------------ #
# Tax authority verification
# ------------------------------------------------------------------ #

class TestTaxVerification:
    def test_clean_active_identity_is_eligible(self, setup):
        _, consumer = setup
        start =  datetime.now(timezone.utc) - timedelta(days=60)
        end =  datetime.now(timezone.utc) - timedelta(days=10)
        result = consumer.verify_tax(OrganisationType.TAX_AUTHORITY, "GB-001", start, end)
        assert result["eligible"] is True

    def test_identity_suspended_during_period_is_ineligible(self, setup):
        manager, consumer = setup
        # Suspend and reinstate — the suspension overlaps the reporting window
        manager.change_status(CA, "GB-001", IDStatus.SUSPENDED)
        manager.change_status(CA, "GB-001", IDStatus.ACTIVE)
        start =  datetime.now(timezone.utc) - timedelta(days=5)
        end =  datetime.now(timezone.utc) + timedelta(days=1)
        result = consumer.verify_tax(OrganisationType.TAX_AUTHORITY, "GB-001", start, end)
        assert result["eligible"] is False

    def test_revoked_identity_is_ineligible_for_tax(self, setup):
        manager, consumer = setup
        manager.change_status(CA, "GB-001", IDStatus.REVOKED)
        start =  datetime.now(timezone.utc) - timedelta(days=30)
        end =  datetime.now(timezone.utc)
        result = consumer.verify_tax(OrganisationType.TAX_AUTHORITY, "GB-001", start, end)
        assert result["eligible"] is False

    def test_nonexistent_identity_is_ineligible_for_tax(self, setup):
        _, consumer = setup
        start =  datetime.now(timezone.utc) - timedelta(days=30)
        end =  datetime.now(timezone.utc)
        result = consumer.verify_tax(OrganisationType.TAX_AUTHORITY, "GB-999", start, end)
        assert result["eligible"] is False

    def test_employer_cannot_perform_tax_verification(self, setup):
        _, consumer = setup
        with pytest.raises(AuthorisationError):
            consumer.verify_tax(OrganisationType.EMPLOYER, "GB-001",
                                 datetime.now(timezone.utc) - timedelta(days=30),  datetime.now(timezone.utc))


# ------------------------------------------------------------------ #
# Driving licence verification
# ------------------------------------------------------------------ #

class TestDrivingLicenceVerification:
    def test_active_identity_no_restriction_is_eligible(self, setup):
        _, consumer = setup
        result = consumer.verify_driving_licence(
            OrganisationType.DRIVING_LICENCE_AUTHORITY, "GB-001", restriction_flag=False
        )
        assert result["eligible"] is True

    def test_active_identity_with_restriction_is_ineligible(self, setup):
        _, consumer = setup
        result = consumer.verify_driving_licence(
            OrganisationType.DRIVING_LICENCE_AUTHORITY, "GB-001", restriction_flag=True
        )
        assert result["eligible"] is False

    def test_suspended_identity_is_ineligible_for_licence(self, setup):
        manager, consumer = setup
        manager.change_status(CA, "GB-001", IDStatus.SUSPENDED)
        result = consumer.verify_driving_licence(
            OrganisationType.DRIVING_LICENCE_AUTHORITY, "GB-001"
        )
        assert result["eligible"] is False

    def test_nonexistent_identity_is_ineligible_for_licence(self, setup):
        _, consumer = setup
        result = consumer.verify_driving_licence(
            OrganisationType.DRIVING_LICENCE_AUTHORITY, "GB-999"
        )
        assert result["eligible"] is False

    def test_bank_cannot_perform_driving_licence_verification(self, setup):
        _, consumer = setup
        with pytest.raises(AuthorisationError):
            consumer.verify_driving_licence(OrganisationType.BANK, "GB-001")
