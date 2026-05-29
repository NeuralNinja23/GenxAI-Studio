# app/runtime/leases.py
"""
V4 Execution Lease System — Stage 1: Freeze Runtime

Provides distributed execution locks to prevent split-brain states
where two projection cycles operate on the same project simultaneously.

Architecture:
    - One project = at most one active lease at a time
    - Leases have a TTL and are renewed by a heartbeat loop
    - Expired leases can be stolen (acquired by a new holder)
    - The execution kernel is the ONLY code that may acquire/release leases
    - Cognitive faculties are permanently prohibited from touching leases

Governance invariant:
    No code outside execution_kernel.py may call acquire_lease() or
    release_lease(). Import of this module by cognitive modules is a
    Tier 5 Forbidden Mutation and must be blocked by the Constraint Engine.
"""

import asyncio
import hashlib
import uuid
from datetime import timedelta
from typing import Optional

from app.core.time import utc_now

from app.core.logging import log
from app.models.runtime_models import ExecutionLease, LeaseStatus


# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────

DEFAULT_LEASE_TTL_SECONDS: int = 300        # 5 minutes
HEARTBEAT_INTERVAL_SECONDS: int = 60        # Renew every 60s
LEASE_STEAL_GRACE_SECONDS: int = 10         # Extra buffer before stealing


class LeaseAcquisitionError(Exception):
    """Raised when a lease cannot be acquired."""


class LeaseExpiredError(Exception):
    """Raised when an operation is attempted on an expired lease."""


class LeaseOwnershipError(Exception):
    """Raised when a non-owner attempts to act on a lease."""


# ─────────────────────────────────────────────────────────────
# Core Lease Manager
# ─────────────────────────────────────────────────────────────

class LeaseManager:
    """
    Manages execution leases for projection cycle locking.

    One LeaseManager instance exists per execution kernel instance.
    The kernel calls acquire() before every projection cycle and
    release() after commit or rollback.
    """

    def __init__(self, kernel_id: Optional[str] = None):
        # Unique ID for this kernel instance
        self.kernel_id: str = kernel_id or str(uuid.uuid4())
        self._heartbeat_tasks: dict[str, asyncio.Task] = {}

    # ──────────────────────────────────────────────────────────
    # Acquire
    # ──────────────────────────────────────────────────────────

    async def acquire(
        self,
        project_id: str,
        cycle_id: str,
        ttl_seconds: int = DEFAULT_LEASE_TTL_SECONDS,
    ) -> ExecutionLease:
        """
        Acquire an exclusive execution lease for a project.

        Blocks if another active non-expired lease exists.
        Steals the lease if the holder has expired.

        Args:
            project_id: Project being locked.
            cycle_id:   Projection cycle requesting the lock.
            ttl_seconds: Lease time-to-live in seconds.

        Returns:
            The acquired ExecutionLease document.

        Raises:
            LeaseAcquisitionError: If an active non-expired lease exists.
        """
        now = utc_now()
        expires_at = now + timedelta(seconds=ttl_seconds)

        # Check for existing active lease
        existing = await ExecutionLease.find_one(
            ExecutionLease.project_id == project_id,
            ExecutionLease.status == LeaseStatus.ACTIVE,
        )

        if existing is not None:
            if existing.expires_at > now:
                raise LeaseAcquisitionError(
                    f"Active lease held by {existing.holder_id} "
                    f"for project {project_id} (expires {existing.expires_at.isoformat()}). "
                    f"Cannot acquire until expired or released."
                )

            # Existing lease is expired — steal it
            log("LEASE", f"⚠️ Stealing expired lease {existing.lease_id} for {project_id}")
            existing.status = LeaseStatus.STOLEN
            existing.released_at = now
            await existing.save()

        # Create new lease
        lease = ExecutionLease(
            project_id=project_id,
            holder_id=self.kernel_id,
            status=LeaseStatus.ACTIVE,
            acquired_at=now,
            expires_at=expires_at,
            cycle_id=cycle_id,
        )
        await lease.insert()

        log("LEASE", f"✅ Acquired lease {lease.lease_id} for {project_id} (TTL={ttl_seconds}s)")

        # Start heartbeat
        task = asyncio.create_task(
            self._heartbeat(lease.lease_id, project_id, ttl_seconds),
            name=f"lease_heartbeat_{project_id}",
        )
        self._heartbeat_tasks[lease.lease_id] = task

        return lease

    # ──────────────────────────────────────────────────────────
    # Release
    # ──────────────────────────────────────────────────────────

    async def release(self, lease: ExecutionLease) -> None:
        """
        Release an execution lease.

        Args:
            lease: The lease to release.

        Raises:
            LeaseOwnershipError: If the caller is not the lease holder.
            LeaseExpiredError:   If the lease has already expired.
        """
        if lease.holder_id != self.kernel_id:
            raise LeaseOwnershipError(
                f"Cannot release lease {lease.lease_id}: "
                f"held by {lease.holder_id}, not {self.kernel_id}"
            )

        now = utc_now()
        if lease.status != LeaseStatus.ACTIVE:
            log("LEASE", f"⚠️ Attempted to release non-active lease {lease.lease_id} (status={lease.status})")
            return

        lease.status = LeaseStatus.RELEASED
        lease.released_at = now
        await lease.save()

        # Cancel heartbeat
        task = self._heartbeat_tasks.pop(lease.lease_id, None)
        if task and not task.done():
            task.cancel()

        log("LEASE", f"🔓 Released lease {lease.lease_id} for {lease.project_id}")

    # ──────────────────────────────────────────────────────────
    # Verify ownership (called before each kernel operation)
    # ──────────────────────────────────────────────────────────

    async def verify_ownership(self, lease: ExecutionLease) -> bool:
        """
        Verify that this kernel still holds the lease and it has not expired.

        Should be called at critical kernel checkpoints (before each file write,
        before each oracle invocation, before commit).

        Returns True if ownership is valid, False otherwise.
        """
        now = utc_now()

        # Re-fetch from DB to catch external changes
        fresh = await ExecutionLease.get(lease.id)
        if fresh is None:
            log("LEASE", f"❌ Lease {lease.lease_id} no longer exists in DB")
            return False

        if fresh.status != LeaseStatus.ACTIVE:
            log("LEASE", f"❌ Lease {lease.lease_id} is no longer ACTIVE (status={fresh.status})")
            return False

        if fresh.holder_id != self.kernel_id:
            log("LEASE", f"❌ Lease {lease.lease_id} stolen by {fresh.holder_id}")
            return False

        if fresh.expires_at <= now:
            log("LEASE", f"❌ Lease {lease.lease_id} has expired")
            return False

        return True

    # ──────────────────────────────────────────────────────────
    # Heartbeat (internal)
    # ──────────────────────────────────────────────────────────

    async def _heartbeat(
        self,
        lease_id: str,
        project_id: str,
        ttl_seconds: int,
    ) -> None:
        """Periodically renew the lease TTL to prevent expiry during long cycles."""
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)

                lease = await ExecutionLease.find_one(
                    ExecutionLease.lease_id == lease_id,
                    ExecutionLease.holder_id == self.kernel_id,
                )

                if lease is None or lease.status != LeaseStatus.ACTIVE:
                    log("LEASE", f"⚠️ Heartbeat stopping — lease {lease_id} gone or inactive")
                    break

                new_expiry = utc_now() + timedelta(seconds=ttl_seconds)
                lease.expires_at = new_expiry
                await lease.save()
                log("LEASE", f"💓 Lease {lease_id} renewed (expires {new_expiry.isoformat()})")

        except asyncio.CancelledError:
            pass  # Normal on release

    # ──────────────────────────────────────────────────────────
    # Utility
    # ──────────────────────────────────────────────────────────

    async def get_active_lease(self, project_id: str) -> Optional[ExecutionLease]:
        """Return the active lease for a project, or None."""
        now = utc_now()
        lease = await ExecutionLease.find_one(
            ExecutionLease.project_id == project_id,
            ExecutionLease.status == LeaseStatus.ACTIVE,
        )
        if lease and lease.expires_at <= now:
            # Mark as expired in DB
            lease.status = LeaseStatus.EXPIRED
            await lease.save()
            return None
        return lease

    async def release_all_for_project(self, project_id: str) -> int:
        """Emergency: release all active leases for a project. Returns count released."""
        now = utc_now()
        leases = await ExecutionLease.find(
            ExecutionLease.project_id == project_id,
            ExecutionLease.status == LeaseStatus.ACTIVE,
        ).to_list()

        count = 0
        for lease in leases:
            lease.status = LeaseStatus.RELEASED
            lease.released_at = now
            await lease.save()
            task = self._heartbeat_tasks.pop(lease.lease_id, None)
            if task and not task.done():
                task.cancel()
            count += 1

        if count > 0:
            log("LEASE", f"⚠️ Emergency released {count} lease(s) for {project_id}")
        return count


# ─────────────────────────────────────────────────────────────
# Lease integrity hash
# ─────────────────────────────────────────────────────────────

def compute_lease_hash(lease: ExecutionLease) -> str:
    """
    Compute a deterministic hash of a lease record.
    Used for tamper-detection in transaction chains.
    """
    raw = (
        f"{lease.lease_id}:{lease.project_id}:{lease.holder_id}:"
        f"{lease.acquired_at.isoformat()}:{lease.expires_at.isoformat()}"
    )
    return hashlib.sha256(raw.encode()).hexdigest()
