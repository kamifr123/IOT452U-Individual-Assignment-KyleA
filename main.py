"""
main.py

Console demonstration of the Digital ID platform.
Walks through the key system scenarios described in the brief:
  1. Central authority creates and manages identities
  2. Status lifecycle management (active, suspended, revoked)
  3. Business rule enforcement (immutable fields, revoked ID updates)
  4. Authorisation enforcement (wrong org type rejected)
  5. Consuming organisation verifications (basic, tax, driving licence)
  6. Audit log review

Run with: python main.py
"""

from datetime import datetime, timedelta, timezone

from audit.audit_log import AuditLog
from auth.authorisation import OrganisationType, AuthorisationError
from models.digital_id import IDStatus
from services.identity_manager import IdentityManager, DuplicateIdentityError, IdentityNotFoundError
from services.identity_consumer import IdentityConsumer


def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def main():
    # ------------------------------------------------------------------ #
    # Setup — shared audit log, manager, consumer
    # ------------------------------------------------------------------ #
    audit_log = AuditLog()
    manager = IdentityManager(audit_log)
    consumer = IdentityConsumer(manager, audit_log)
    ca = OrganisationType.CENTRAL_AUTHORITY

    # ------------------------------------------------------------------ #
    # 1. Creating Digital IDs
    # ------------------------------------------------------------------ #
    section("1. Creating Digital IDs")

    id1 = manager.create_identity(
        actor=ca,
        national_id="GB-001",
        date_of_birth="1985-04-12",
        name="Alice Mensah",
        address="10 Elm Street, London",
        email="alice@example.com",
    )
    print(f"  Created: {id1}")

    id2 = manager.create_identity(
        actor=ca,
        national_id="GB-002",
        date_of_birth="1990-07-23",
        name="Ben Okafor",
        address="5 Oak Avenue, Manchester",
        email="ben@example.com",
    )
    print(f"  Created: {id2}")

    # Duplicate creation is rejected
    print("\n  Attempting duplicate creation (GB-001):")
    try:
        manager.create_identity(ca, "GB-001", "1985-04-12", "Alice M", "London", "a@b.com")
    except DuplicateIdentityError as e:
        print(f"  REJECTED: {e}")

    # ------------------------------------------------------------------ #
    # 2. Updating mutable attributes
    # ------------------------------------------------------------------ #
    section("2. Updating Mutable Attributes")

    manager.update_identity(ca, "GB-001", "address", "22 New Road, Birmingham")
    print(f"  Updated address: {manager.get_identity('GB-001').address}")

    # Immutable field rejected
    print("\n  Attempting to update immutable field (date_of_birth):")
    try:
        manager.update_identity(ca, "GB-001", "date_of_birth", "2000-01-01")
    except AttributeError as e:
        print(f"  REJECTED: {e}")

    # ------------------------------------------------------------------ #
    # 3. Status lifecycle
    # ------------------------------------------------------------------ #
    section("3. Status Lifecycle")

    manager.change_status(ca, "GB-001", IDStatus.SUSPENDED)
    print(f"  GB-001 status: {manager.get_identity('GB-001').status.value}")

    manager.change_status(ca, "GB-001", IDStatus.ACTIVE)
    print(f"  GB-001 reinstated: {manager.get_identity('GB-001').status.value}")

    manager.change_status(ca, "GB-002", IDStatus.REVOKED)
    print(f"  GB-002 revoked: {manager.get_identity('GB-002').status.value}")

    # Repeated status is idempotent (no error)
    print("\n  Applying ACTIVE status to already-ACTIVE GB-001 (idempotent):")
    manager.change_status(ca, "GB-001", IDStatus.ACTIVE)
    print(f"  GB-001 status unchanged: {manager.get_identity('GB-001').status.value}")

    # Cannot change a revoked ID
    print("\n  Attempting to reactivate revoked GB-002:")
    try:
        manager.change_status(ca, "GB-002", IDStatus.ACTIVE)
    except PermissionError as e:
        print(f"  REJECTED: {e}")

    # Cannot update a revoked ID
    print("\n  Attempting to update revoked GB-002:")
    try:
        manager.update_identity(ca, "GB-002", "name", "New Name")
    except PermissionError as e:
        print(f"  REJECTED: {e}")

    # ------------------------------------------------------------------ #
    # 4. Authorisation enforcement
    # ------------------------------------------------------------------ #
    section("4. Authorisation Enforcement")

    print("  Bank attempting to create an identity:")
    try:
        manager.create_identity(
            OrganisationType.BANK, "GB-003", "1992-01-01", "Test", "Addr", "t@t.com"
        )
    except AuthorisationError as e:
        print(f"  REJECTED: {e}")

    print("\n  Employer attempting a tax verification:")
    try:
        consumer.verify_tax(
            OrganisationType.EMPLOYER, "GB-001",
             datetime.now(timezone.utc) - timedelta(days=30),  datetime.now(timezone.utc)
        )
    except AuthorisationError as e:
        print(f"  REJECTED: {e}")

    # ------------------------------------------------------------------ #
    # 5. Consuming organisation verifications
    # ------------------------------------------------------------------ #
    section("5. Identity Verification by Consuming Organisations")

    # Basic verification (employer) — active ID
    result = consumer.verify_basic(OrganisationType.EMPLOYER, "GB-001")
    print(f"  Employer verifies GB-001 (active): {result}")

    # Basic verification — revoked ID
    result = consumer.verify_basic(OrganisationType.BANK, "GB-002")
    print(f"  Bank verifies GB-002 (revoked): {result}")

    # Basic verification — non-existent ID
    result = consumer.verify_basic(OrganisationType.EMPLOYER, "GB-999")
    print(f"  Employer verifies GB-999 (not found): {result}")

    # Tax authority — create fresh ID that was suspended during a period
    section("  Tax Authority Verification Detail")
    id3 = manager.create_identity(ca, "GB-003", "1978-03-01",
                                   "Carol Diaz", "8 Pine Rd, Leeds", "carol@example.com")
    # Suspend and reinstate FIRST, then define the period around it
    manager.change_status(ca, "GB-003", IDStatus.SUSPENDED)
    manager.change_status(ca, "GB-003", IDStatus.ACTIVE)

    # Reporting period brackets the suspension that just happened
    period_start =  datetime.now(timezone.utc) - timedelta(seconds=5)
    period_end =  datetime.now(timezone.utc) + timedelta(days=1)

    result = consumer.verify_tax(
        OrganisationType.TAX_AUTHORITY, "GB-003", period_start, period_end
    )
    print(f"  Tax check GB-003 (was suspended in period): {result}")

    # ID with no suspension in period
    id4 = manager.create_identity(ca, "GB-004", "1995-11-15",
                                   "David Nwosu", "3 Maple Close, Bristol", "david@example.com")
    result = consumer.verify_tax(
        OrganisationType.TAX_AUTHORITY, "GB-004", period_start, period_end
    )
    print(f"  Tax check GB-004 (clean record): {result}")

    # Driving licence — no restriction
    result = consumer.verify_driving_licence(
        OrganisationType.DRIVING_LICENCE_AUTHORITY, "GB-001", restriction_flag=False
    )
    print(f"\n  Driving licence GB-001 (no restriction): {result}")

    # Driving licence — restriction in place
    result = consumer.verify_driving_licence(
        OrganisationType.DRIVING_LICENCE_AUTHORITY, "GB-001", restriction_flag=True
    )
    print(f"  Driving licence GB-001 (restriction): {result}")

    # ------------------------------------------------------------------ #
    # 6. Audit log
    # ------------------------------------------------------------------ #
    section("6. Audit Log")
    audit_log.display()

    print("\n  Audit entries for GB-001 only:")
    for entry in audit_log.get_by_id("GB-001"):
        print(f"    {entry['timestamp']} | {entry['action']} | {entry.get('detail','')}")


if __name__ == "__main__":
    main()
