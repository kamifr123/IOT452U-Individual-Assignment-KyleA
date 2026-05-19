"""
auth/authorisation.py

Defines the roles within the Digital ID ecosystem and enforces
organisation-level authorisation before any operation is performed.

Only the CENTRAL_AUTHORITY may manage identities.
Consuming organisations may only perform verification and lookup operations.
"""

from enum import Enum


class OrganisationType(Enum):
    """All recognised participant types in the Digital ID ecosystem."""
    CENTRAL_AUTHORITY = "CENTRAL_AUTHORITY"
    TAX_AUTHORITY = "TAX_AUTHORITY"
    DRIVING_LICENCE_AUTHORITY = "DRIVING_LICENCE_AUTHORITY"
    EMPLOYER = "EMPLOYER"
    BANK = "BANK"
    WELFARE_SERVICE = "WELFARE_SERVICE"
    IMMIGRATION_BODY = "IMMIGRATION_BODY"
    LOCAL_AUTHORITY = "LOCAL_AUTHORITY"


# Operations reserved exclusively for the central authority
MANAGEMENT_OPERATIONS = {"create", "update", "change_status"}

# Operations available to consuming organisations
CONSUMPTION_OPERATIONS = {"verify_basic", "verify_tax", "verify_driving_licence"}

# Which consuming organisations may perform which operations
ORGANISATION_PERMISSIONS: dict[OrganisationType, set[str]] = {
    OrganisationType.CENTRAL_AUTHORITY: MANAGEMENT_OPERATIONS | CONSUMPTION_OPERATIONS,
    OrganisationType.TAX_AUTHORITY: {"verify_tax"},
    OrganisationType.DRIVING_LICENCE_AUTHORITY: {"verify_driving_licence"},
    OrganisationType.EMPLOYER: {"verify_basic"},
    OrganisationType.BANK: {"verify_basic"},
    OrganisationType.WELFARE_SERVICE: {"verify_basic"},
    OrganisationType.IMMIGRATION_BODY: {"verify_basic"},
    OrganisationType.LOCAL_AUTHORITY: {"verify_basic"},
}


class AuthorisationError(Exception):
    """Raised when an organisation attempts an operation it is not permitted to perform."""
    pass


def authorise(org_type: OrganisationType, operation: str) -> None:
    """
    Checks whether the given organisation type is permitted to perform
    the requested operation. Raises AuthorisationError if not.
    """
    permitted = ORGANISATION_PERMISSIONS.get(org_type, set())
    if operation not in permitted:
        raise AuthorisationError(
            f"'{org_type.value}' is not authorised to perform '{operation}'."
        )
