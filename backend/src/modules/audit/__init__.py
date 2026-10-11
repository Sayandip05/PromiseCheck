"""Audit domain module public interface."""

from modules.audit.service import record_audit_event

__all__ = [
    "record_audit_event",
]
