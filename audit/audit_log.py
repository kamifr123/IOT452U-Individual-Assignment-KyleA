"""
audit/audit_log.py

Records all key system actions: identity creation, updates, status changes,
and verification requests. Provides a simple queryable log.
"""

from datetime import datetime, timezone


class AuditLog:
    """
    A simple in-memory audit log.
    Each entry records who did what, to which identity, and when.
    """

    def __init__(self):
        self._entries: list[dict] = []

    def record(self, action: str, national_id: str, actor: str, detail: str = "") -> None:
        """Appends a new audit entry."""
        entry = {
            "timestamp":  datetime.now(timezone.utc).isoformat(),
            "action": action,
            "national_id": national_id,
            "actor": actor,
            "detail": detail,
        }
        self._entries.append(entry)

    def get_all(self) -> list[dict]:
        """Returns all audit entries."""
        return list(self._entries)

    def get_by_id(self, national_id: str) -> list[dict]:
        """Returns all audit entries related to a specific Digital ID."""
        return [e for e in self._entries if e["national_id"] == national_id]

    def display(self) -> None:
        """Prints the audit log to the console in a readable format."""
        if not self._entries:
            print("  [Audit Log is empty]")
            return
        for entry in self._entries:
            print(f"  [{entry['timestamp']}] {entry['action']} | "
                  f"ID: {entry['national_id']} | Actor: {entry['actor']}"
                  + (f" | {entry['detail']}" if entry["detail"] else ""))
