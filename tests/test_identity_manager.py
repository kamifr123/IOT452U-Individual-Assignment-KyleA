"""
tests/test_identity_manager.py

Unit tests for the IdentityManager service.
Covers: creation, duplicate rejection, mutable updates, immutable field rejection,
status transitions, idempotency, and revocation rules.
"""

import pytest
from audit.audit_log import AuditLog
from auth.authorisation import OrganisationType, AuthorisationError
from models.digital_id import IDStatus
from services.identity_manager import (
    IdentityManager,
    DuplicateIdentityError,
    IdentityNotFoundError,
)

CA = OrganisationType.CENTRAL_AUTHORITY


@pytest.fixture
def manager():
    """Provides a fresh IdentityManager with a clean audit log for each test."""
    return IdentityManager(AuditLog())


@pytest.fixture
def manager_with_active_id(manager):
    """Provides a manager that already contains one active Digital ID (GB-001)."""
    manager.create_identity(CA, "GB-001", "1985-04-12",
                            "Alice Mensah", "10 Elm St, London", "alice@example.com")
    return manager


# ------------------------------------------------------------------ #
# Creation
# ------------------------------------------------------------------ #

class TestCreateIdentity:
    def test_create_valid_identity_succeeds(self, manager):
        identity = manager.create_identity(
            CA, "GB-001", "1985-04-12", "Alice Mensah", "London", "alice@example.com"
        )
        assert identity.national_id == "GB-001"
        assert identity.status == IDStatus.ACTIVE

    def test_new_identity_is_active_by_default(self, manager):
        identity = manager.create_identity(
            CA, "GB-002", "1990-01-01", "Ben Okafor", "Manchester", "ben@example.com"
        )
        assert identity.status == IDStatus.ACTIVE

    def test_duplicate_identity_raises_error(self, manager_with_active_id):
        with pytest.raises(DuplicateIdentityError):
            manager_with_active_id.create_identity(
                CA, "GB-001", "1985-04-12", "Alice M", "London", "a@b.com"
            )

    def test_non_central_authority_cannot_create(self, manager):
        with pytest.raises(AuthorisationError):
            manager.create_identity(
                OrganisationType.BANK, "GB-010", "1992-01-01",
                "Test User", "Somewhere", "t@t.com"
            )

    def test_creation_is_recorded_in_audit_log(self, manager):
        audit = AuditLog()
        mgr = IdentityManager(audit)
        mgr.create_identity(CA, "GB-005", "2000-01-01", "Test", "Addr", "t@t.com")
        entries = audit.get_by_id("GB-005")
        assert len(entries) == 1
        assert entries[0]["action"] == "IDENTITY_CREATED"


# ------------------------------------------------------------------ #
# Updates
# ------------------------------------------------------------------ #

class TestUpdateIdentity:
    def test_update_mutable_attribute_succeeds(self, manager_with_active_id):
        manager_with_active_id.update_identity(CA, "GB-001", "address", "New Address")
        identity = manager_with_active_id.get_identity("GB-001")
        assert identity.address == "New Address"

    def test_update_immutable_field_raises_error(self, manager_with_active_id):
        with pytest.raises(AttributeError):
            manager_with_active_id.update_identity(CA, "GB-001", "date_of_birth", "2000-01-01")

    def test_update_unknown_field_raises_error(self, manager_with_active_id):
        with pytest.raises(AttributeError):
            manager_with_active_id.update_identity(CA, "GB-001", "favourite_colour", "blue")

    def test_update_revoked_identity_raises_error(self, manager_with_active_id):
        manager_with_active_id.change_status(CA, "GB-001", IDStatus.REVOKED)
        with pytest.raises(PermissionError):
            manager_with_active_id.update_identity(CA, "GB-001", "name", "New Name")

    def test_non_central_authority_cannot_update(self, manager_with_active_id):
        with pytest.raises(AuthorisationError):
            manager_with_active_id.update_identity(
                OrganisationType.EMPLOYER, "GB-001", "name", "Hacker"
            )

    def test_update_non_existent_identity_raises_error(self, manager):
        with pytest.raises(IdentityNotFoundError):
            manager.update_identity(CA, "GB-999", "name", "Ghost")


# ------------------------------------------------------------------ #
# Status management
# ------------------------------------------------------------------ #

class TestStatusManagement:
    def test_suspend_active_identity(self, manager_with_active_id):
        manager_with_active_id.change_status(CA, "GB-001", IDStatus.SUSPENDED)
        assert manager_with_active_id.get_identity("GB-001").status == IDStatus.SUSPENDED

    def test_reinstate_suspended_identity(self, manager_with_active_id):
        manager_with_active_id.change_status(CA, "GB-001", IDStatus.SUSPENDED)
        manager_with_active_id.change_status(CA, "GB-001", IDStatus.ACTIVE)
        assert manager_with_active_id.get_identity("GB-001").status == IDStatus.ACTIVE

    def test_revoke_identity(self, manager_with_active_id):
        manager_with_active_id.change_status(CA, "GB-001", IDStatus.REVOKED)
        assert manager_with_active_id.get_identity("GB-001").status == IDStatus.REVOKED

    def test_cannot_change_status_of_revoked_identity(self, manager_with_active_id):
        manager_with_active_id.change_status(CA, "GB-001", IDStatus.REVOKED)
        with pytest.raises(PermissionError):
            manager_with_active_id.change_status(CA, "GB-001", IDStatus.ACTIVE)

    def test_repeated_status_application_is_idempotent(self, manager_with_active_id):
        """Applying the same status twice should not raise an error."""
        manager_with_active_id.change_status(CA, "GB-001", IDStatus.ACTIVE)
        identity = manager_with_active_id.get_identity("GB-001")
        assert identity.status == IDStatus.ACTIVE

    def test_non_central_authority_cannot_change_status(self, manager_with_active_id):
        with pytest.raises(AuthorisationError):
            manager_with_active_id.change_status(
                OrganisationType.TAX_AUTHORITY, "GB-001", IDStatus.SUSPENDED
            )
