"""
services/identity_consumer.py

Handles identity verification and lookup requests from consuming organisations.
Each organisation type receives a response appropriate to its role:

  - Basic verification (employer, bank, etc.): valid / not valid only
  - Tax authority: active + not suspended during reporting period
  - Driving licence authority: active + no temporary restriction flag

Consuming organisations cannot access management operations.
All verification requests are recorded in the audit log.
"""

from datetime import datetime, timezone
from models.digital_id import IDStatus
from auth.authorisation import OrganisationType, authorise
from audit.audit_log import AuditLog
from services.identity_manager import IdentityManager, IdentityNotFoundError


class IdentityConsumer:
    """
    Provides identity verification and lookup services to consuming organisations.
    Separated from IdentityManager to enforce the distinct capability boundary
    described in the system requirements.
    """

    def __init__(self, identity_manager: IdentityManager, audit_log: AuditLog):
        self._manager = identity_manager
        self._audit_log = audit_log

    def verify_basic(self, actor: OrganisationType, national_id: str) -> dict:
        """
        Basic verification for employers, banks, and similar organisations.
        Returns only whether the Digital ID is currently valid (Active).
        No additional attributes or history are exposed.
        """
        authorise(actor, "verify_basic")
        self._audit_log.record(
            action="VERIFY_BASIC",
            national_id=national_id,
            actor=actor.value,
        )
        try:
            identity = self._manager.get_identity(national_id)
            is_valid = identity.status == IDStatus.ACTIVE
        except IdentityNotFoundError:
            is_valid = False

        return {"national_id": national_id, "valid": is_valid}

    def verify_tax(self, actor: OrganisationType, national_id: str,
                   period_start: datetime, period_end: datetime) -> dict:
        """
        Tax authority verification.
        Confirms the Digital ID exists, is currently Active, and was not
        suspended at any point during the specified reporting period.
        """
        authorise(actor, "verify_tax")
        self._audit_log.record(
            action="VERIFY_TAX",
            national_id=national_id,
            actor=actor.value,
            detail=f"period={period_start.date()} to {period_end.date()}",
        )
        try:
            identity = self._manager.get_identity(national_id)
        except IdentityNotFoundError:
            return {"national_id": national_id, "eligible": False,
                    "reason": "Identity not found."}

        if identity.status != IDStatus.ACTIVE:
            return {"national_id": national_id, "eligible": False,
                    "reason": f"Identity is {identity.status.value}."}

        if identity.was_suspended_during(period_start, period_end):
            return {"national_id": national_id, "eligible": False,
                    "reason": "Identity was suspended during the reporting period."}

        return {"national_id": national_id, "eligible": True, "reason": "Identity is eligible."}

    def verify_driving_licence(self, actor: OrganisationType, national_id: str,
                                restriction_flag: bool = False) -> dict:
        """
        Driving licence authority verification.
        Confirms the identity is Active and that no temporary restriction is in place.
        The restriction_flag would be set externally based on domain-specific rules.
        """
        authorise(actor, "verify_driving_licence")
        self._audit_log.record(
            action="VERIFY_DRIVING_LICENCE",
            national_id=national_id,
            actor=actor.value,
            detail=f"restriction_flag={restriction_flag}",
        )
        try:
            identity = self._manager.get_identity(national_id)
        except IdentityNotFoundError:
            return {"national_id": national_id, "eligible": False,
                    "reason": "Identity not found."}

        if identity.status != IDStatus.ACTIVE:
            return {"national_id": national_id, "eligible": False,
                    "reason": f"Identity is {identity.status.value}."}

        if restriction_flag:
            return {"national_id": national_id, "eligible": False,
                    "reason": "Identity is subject to a temporary restriction."}

        return {"national_id": national_id, "eligible": True,
                "reason": "Identity is eligible for licence issuance."}
