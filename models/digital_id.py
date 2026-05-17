"""
models/digital_id.py

Defines the DigitalID entity and its associated status values.
Immutable attributes (national_id, date_of_birth) cannot be changed after creation.
Mutable attributes (name, address, email) may be updated by the central authority only.
"""

from enum import Enum
from datetime import datetime, timezone


class IDStatus(Enum):
    """Represents the lifecycle status of a Digital ID."""
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"


# Attributes that can never be changed after creation
IMMUTABLE_ATTRIBUTES = {"national_id", "date_of_birth"}

# Attributes the central authority is permitted to update
MUTABLE_ATTRIBUTES = {"name", "address", "email"}


class DigitalID:
    """
    Represents a single Digital ID within the federated ecosystem.

    Each identity has a unique national_id, a set of attributes,
    a current status, and a record of when it was created/updated.
    """

    def __init__(self, national_id: str, date_of_birth: str, name: str,
                 address: str, email: str):
        if not all([national_id, date_of_birth, name, address, email]):
            raise ValueError("All fields are required to create a Digital ID.")

        # Immutable core identity fields
        self._national_id = national_id
        self._date_of_birth = date_of_birth

        # Mutable attributes
        self.name = name
        self.address = address
        self.email = email

        # Lifecycle state
        self.status = IDStatus.ACTIVE
        self.created_at =  datetime.now(timezone.utc)
        self.updated_at =  datetime.now(timezone.utc)

        # Tracks periods during which the ID was suspended (list of dicts)
        self.suspension_periods: list[dict] = []

    @property
    def national_id(self) -> str:
        return self._national_id

    @property
    def date_of_birth(self) -> str:
        return self._date_of_birth

    def update_attribute(self, attribute: str, value: str) -> None:
        """
        Updates a mutable attribute. Raises errors for immutable fields
        or if the ID is revoked (revoked IDs cannot be modified).
        """
        if attribute in IMMUTABLE_ATTRIBUTES:
            raise AttributeError(f"'{attribute}' is immutable and cannot be changed.")
        if attribute not in MUTABLE_ATTRIBUTES:
            raise AttributeError(f"'{attribute}' is not a recognised updatable attribute.")
        if self.status == IDStatus.REVOKED:
            raise PermissionError("Cannot update a revoked Digital ID.")
        setattr(self, attribute, value)
        self.updated_at =  datetime.now(timezone.utc)

    def change_status(self, new_status: IDStatus) -> None:
        """
        Applies a status transition. Revoked IDs cannot be reactivated.
        Repeated status applications are handled deterministically (no error, no change).
        """
        if self.status == IDStatus.REVOKED:
            raise PermissionError("A revoked Digital ID cannot have its status changed.")
        if self.status == new_status:
            # Idempotent — already in the desired state, nothing to do
            return

        # Track suspension windows for tax authority checks
        if new_status == IDStatus.SUSPENDED:
            self.suspension_periods.append({"suspended_at":  datetime.now(timezone.utc), "reinstated_at": None})
        elif new_status == IDStatus.ACTIVE and self.status == IDStatus.SUSPENDED:
            if self.suspension_periods and self.suspension_periods[-1]["reinstated_at"] is None:
                self.suspension_periods[-1]["reinstated_at"] =  datetime.now(timezone.utc)

        self.status = new_status
        self.updated_at =  datetime.now(timezone.utc)

    def was_suspended_during(self, start: datetime, end: datetime) -> bool:
        """
        Returns True if this ID was suspended at any point during the given period.
        Used by the tax authority verification check.
        """
        for period in self.suspension_periods:
            suspended_at = period["suspended_at"]
            reinstated_at = period["reinstated_at"] or  datetime.now(timezone.utc)
            # Check for overlap between suspension window and reporting period
            if suspended_at < end and reinstated_at > start:
                return True
        return False

    def __repr__(self) -> str:
        return (f"DigitalID(national_id={self._national_id}, "
                f"name={self.name}, status={self.status.value})")
