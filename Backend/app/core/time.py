# app/core/time.py
"""
V4 UTC Time Substrate Law — Global Time Authority

ALL V4 runtime systems MUST use utc_now() exclusively.

BANNED everywhere in:
    runtime, kernel, leases, transactions, topology lineage,
    synchronization, snapshots, reconstruction, substrate management.

    datetime.utcnow()    ← FORBIDDEN — produces naive datetime
    datetime.now()       ← FORBIDDEN — produces local naive datetime

ONLY allowed form:
    from app.core.time import utc_now
    utc_now()            ← Always returns timezone-aware UTC datetime

Why this matters:
    Time is now part of canonical V4 reality:
        - Transaction lineage ordering
        - Branch ancestry genealogy
        - Rollback ordering / snapshot windows
        - Lease expiry and heartbeat enforcement
        - Synchronization divergence windows
        - Convergence chronology
        - Runtime continuity across restarts

    Comparing naive vs aware datetimes raises TypeError in Python.
    One naive datetime anywhere in the kernel chain corrupts the
    entire transaction/lease/sync system.
"""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """
    Return the current UTC time as a timezone-aware datetime object.

    This is the ONLY authorised time source in V4 runtime systems.
    All comparisons, timestamps, TTL calculations, and lineage records
    MUST use this function exclusively.

    Returns:
        datetime: Current UTC time with tzinfo=timezone.utc
    """
    return datetime.now(timezone.utc)
