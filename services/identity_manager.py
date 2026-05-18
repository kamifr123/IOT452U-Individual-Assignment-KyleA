"""
services/identity_manager.py

Handles all identity management operations on behalf of the central authority:
  - Creating new Digital IDs
  - Updating permitted (mutable) attributes
  - Changing identity status (Active, Suspended, Revoked)

All operations validate authorisation before execution and are recorded
in the audit log. Management operations are restricted to the central authority.
"""

from models.digital_id import DigitalID, IDStatus
from auth.authorisation import OrganisationType, authorise
from audit.audit_log import AuditLog


class IdentityNotFoundError(Exception):
    """Raised when a Digital ID does not exist in the registry."""
    pass


class DuplicateIdentityError(Exception):
    """Raised when attempting to create a Digital ID that already exists."""
    pass


class IdentityManager:
    """
    Manages the lifecycle of Digital IDs.
    Acts as the sole point of identity creation, modification, and status change.
    """

    def __init__(self, audit_log: AuditLog):
        self._registry: dict[str, DigitalID] = {}
        self._audit_log = audit_log

    def create_identity(self, actor: OrganisationType, national_id: str,
                        date_of_birth: str, name: str,
                        address: str, email: str) -> DigitalID:
        """
        Creates a new Digital ID. Only the central authority may do this.
        Raises DuplicateIdentityError if the national_id already exists.
        """
        authorise(actor, "create")

        if national_id in self._registry:
            raise DuplicateIdentityError(
                f"A Digital ID with national_id '{national_id}' already exists."
            )

        identity = DigitalID(
            national_id=national_id,
            date_of_birth=date_of_birth,
            name=name,
            address=address,
            email=email,
        )
        self._registry[national_id] = identity
        self._audit_log.record(
            action="IDENTITY_CREATED",
            national_id=national_id,
            actor=actor.value,
            detail=f"name={name}",
        )
        return identity

    def update_identity(self, actor: OrganisationType, national_id: str,
                        attribute: str, value: str) -> None:
        """
        Updates a mutable attribute of an existing Digital ID.
        Revoked IDs cannot be updated. Immutable fields are rejected.
        """
        authorise(actor, "update")
        identity = self._get_or_raise(national_id)
        identity.update_attribute(attribute, value)
        self._audit_log.record(
            action="IDENTITY_UPDATED",
            national_id=national_id,
            actor=actor.value,
            detail=f"{attribute}={value}",
        )

    def change_status(self, actor: OrganisationType, national_id: str,
                      new_status: IDStatus) -> None:
        """
        Changes the status of a Digital ID.
        Revoked IDs cannot be changed. Repeated applications are idempotent.
        """
        authorise(actor, "change_status")
        identity = self._get_or_raise(national_id)
        previous = identity.status
        identity.change_status(new_status)
        self._audit_log.record(
            action="STATUS_CHANGED",
            national_id=national_id,
            actor=actor.value,
            detail=f"{previous.value} -> {new_status.value}",
        )

    def get_identity(self, national_id: str) -> DigitalID:
        """Returns a Digital ID by national_id, or raises IdentityNotFoundError."""
        return self._get_or_raise(national_id)

    def _get_or_raise(self, national_id: str) -> DigitalID:
        if national_id not in self._registry:
            raise IdentityNotFoundError(
                f"No Digital ID found for national_id '{national_id}'."
            )
        return self._registry[national_id]
