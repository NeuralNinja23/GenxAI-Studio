# app/runtime/transaction_engine.py
"""
V4 Transaction Engine — Stage 1: Freeze Runtime

Coordinates transaction boundaries, integrity hashes, and rollbacks
for every projection cycle.

Transaction lifecycle:
    PENDING → (oracle checks) → COMMITTED
                              → ROLLED_BACK  (on any hard oracle failure)
                              → FAILED       (on engine error)

Integrity hash chain:
    Every committed transaction includes:
        - SHA-256 hash of the previous committed transaction (prev_tx_hash)
        - SHA-256 hash of its own record (tx_hash)
    This forms a tamper-evident structural integrity chain across all commits.

Laws:
    - A transaction CANNOT commit if any hard oracle failed
    - A transaction CANNOT commit without a verified evidence key set
    - Rollback is always total — never partial
    - Only execution_kernel.py may initiate transactions
    - Cognitive faculties are permanently prohibited from calling this module
"""

import hashlib
import json
import uuid
from typing import Any, Dict, List, Optional

from app.core.time import utc_now

from app.core.logging import log
from app.models.runtime_models import (
    MutationTier,
    RuntimeTransaction,
    TransactionStatus,
)
from app.runtime.execution_contracts import ExecutionContracts


class TransactionCommitError(Exception):
    """Raised when a transaction cannot be committed."""


class TransactionRollbackError(Exception):
    """Raised when a rollback fails."""


class TransactionEngine:
    """
    Manages the atomic transaction lifecycle for projection cycles.

    Each projection cycle has exactly one RuntimeTransaction.
    The engine is called by the execution kernel — never by cognitive code.
    """

    # ──────────────────────────────────────────────────────────
    # Begin transaction
    # ──────────────────────────────────────────────────────────

    @staticmethod
    async def begin(
        project_id: str,
        lease_id: str,
        mutation_tier: MutationTier,
        snapshot_id: str,
    ) -> RuntimeTransaction:
        """
        Begin a new transaction for a projection cycle.

        Args:
            project_id:    Project being mutated.
            lease_id:      Active execution lease ID.
            mutation_tier: Tier of the mutation being applied.
            snapshot_id:   Pre-cycle snapshot ID to roll back to on failure.

        Returns:
            A PENDING RuntimeTransaction document.
        """
        tx = RuntimeTransaction(
            project_id=project_id,
            lease_id=lease_id,
            mutation_tier=mutation_tier,
            snapshot_id=snapshot_id,
            status=TransactionStatus.PENDING,
        )
        await tx.insert()
        log("TX", f"📋 Transaction {tx.tx_id} PENDING for {project_id} (tier={mutation_tier.name})")
        return tx

    # ──────────────────────────────────────────────────────────
    # Record writes during the cycle
    # ──────────────────────────────────────────────────────────

    @staticmethod
    async def record_writes(
        tx: RuntimeTransaction,
        files_written: List[str],
        files_deleted: Optional[List[str]] = None,
        pre_topology_hash: Optional[str] = None,
        pre_ast_hash: Optional[str] = None,
        pre_filesystem_hash: Optional[str] = None,
    ) -> None:
        """
        Record the files written and pre-cycle hashes on a pending transaction.

        Called by the execution kernel as it writes files during the cycle.
        """
        tx.files_written = files_written
        tx.files_deleted = files_deleted or []
        tx.pre_topology_hash = pre_topology_hash
        tx.pre_ast_hash = pre_ast_hash
        tx.pre_filesystem_hash = pre_filesystem_hash
        await tx.save()

    # ──────────────────────────────────────────────────────────
    # Commit
    # ──────────────────────────────────────────────────────────

    @staticmethod
    async def commit(
        tx: RuntimeTransaction,
        oracle_results: Dict[str, Any],
        oracle_evidence_keys: List[str],
        post_topology_hash: Optional[str] = None,
        post_ast_hash: Optional[str] = None,
        post_filesystem_hash: Optional[str] = None,
    ) -> RuntimeTransaction:
        """
        Attempt to commit a transaction after all oracles have run.

        Commit is BLOCKED if:
            - Any required hard oracle failed
            - oracle_evidence_keys is empty (no verified evidence)
            - Transaction is not in PENDING status

        On success:
            - Computes integrity hashes
            - Chains to previous committed transaction
            - Sets status to COMMITTED

        Args:
            tx:                    The transaction to commit.
            oracle_results:        Dict of oracle_name → result.
            oracle_evidence_keys:  Evidence keys from EvidenceRegistry.
            post_topology_hash:    Hash of topology after writes.
            post_ast_hash:         Hash of AST state after writes.
            post_filesystem_hash:  Hash of filesystem after writes.

        Returns:
            The committed RuntimeTransaction.

        Raises:
            TransactionCommitError: If any oracle failed or evidence is missing.
        """
        if tx.status != TransactionStatus.PENDING:
            raise TransactionCommitError(
                f"Cannot commit transaction {tx.tx_id}: status is {tx.status}, expected PENDING"
            )

        # ── Oracle contract check ─────────────────────────────
        contract_result = ExecutionContracts.verify_pre_commit(oracle_results, tx.mutation_tier)
        if not contract_result.passed:
            violations_str = "; ".join(v.detail for v in contract_result.violations)
            raise TransactionCommitError(
                f"Transaction {tx.tx_id} commit BLOCKED — oracle contract failed: {violations_str}"
            )

        # ── Evidence requirement ──────────────────────────────
        if not oracle_evidence_keys:
            raise TransactionCommitError(
                f"Transaction {tx.tx_id} commit BLOCKED — no oracle evidence keys provided. "
                f"Cannot claim success without verified evidence."
            )

        # ── Compute post-cycle hashes ─────────────────────────
        tx.post_topology_hash = post_topology_hash
        tx.post_ast_hash = post_ast_hash
        tx.post_filesystem_hash = post_filesystem_hash
        tx.oracle_results = oracle_results
        tx.oracle_evidence_keys = oracle_evidence_keys

        # ── Hash chain ────────────────────────────────────────
        prev_tx_hash = await _get_last_committed_tx_hash(tx.project_id, tx.tx_id)
        tx.prev_tx_hash = prev_tx_hash
        tx.tx_hash = _compute_tx_hash(tx, prev_tx_hash)

        # ── Commit ────────────────────────────────────────────
        tx.status = TransactionStatus.COMMITTED
        tx.committed_at = utc_now()
        await tx.save()

        log("TX", f"✅ Transaction {tx.tx_id} COMMITTED for {tx.project_id} "
                  f"(files={len(tx.files_written)}, hash={tx.tx_hash[:12]}...)")
        return tx

    # ──────────────────────────────────────────────────────────
    # Rollback
    # ──────────────────────────────────────────────────────────

    @staticmethod
    async def rollback(
        tx: RuntimeTransaction,
        reason: str,
    ) -> RuntimeTransaction:
        """
        Roll back a transaction.

        The transaction engine records the rollback; the actual filesystem
        restoration is performed by the execution kernel via SnapshotManager.

        Args:
            tx:     The transaction to roll back.
            reason: Why the rollback was triggered.

        Returns:
            The rolled-back RuntimeTransaction.
        """
        if tx.status not in (TransactionStatus.PENDING, TransactionStatus.FAILED):
            log("TX", f"⚠️ Attempted rollback on transaction {tx.tx_id} "
                      f"with status {tx.status} — skipping")
            return tx

        tx.status = TransactionStatus.ROLLED_BACK
        tx.rolled_back_at = utc_now()
        tx.error = reason
        await tx.save()

        log("TX", f"↩️ Transaction {tx.tx_id} ROLLED_BACK for {tx.project_id}: {reason[:120]}")
        return tx

    # ──────────────────────────────────────────────────────────
    # Mark failed
    # ──────────────────────────────────────────────────────────

    @staticmethod
    async def mark_failed(tx: RuntimeTransaction, error: str) -> RuntimeTransaction:
        """Mark a transaction as FAILED (engine error, not oracle failure)."""
        tx.status = TransactionStatus.FAILED
        tx.error = error
        await tx.save()
        log("TX", f"❌ Transaction {tx.tx_id} FAILED: {error[:120]}")
        return tx

    # ──────────────────────────────────────────────────────────
    # Query helpers
    # ──────────────────────────────────────────────────────────

    @staticmethod
    async def get_pending_transactions(project_id: str) -> List[RuntimeTransaction]:
        """Return all pending transactions for a project (should be 0 or 1)."""
        return await RuntimeTransaction.find(
            RuntimeTransaction.project_id == project_id,
            RuntimeTransaction.status == TransactionStatus.PENDING,
        ).to_list()

    @staticmethod
    async def get_transaction_history(
        project_id: str,
        limit: int = 20,
    ) -> List[RuntimeTransaction]:
        """Return recent transaction history for a project."""
        return await RuntimeTransaction.find(
            RuntimeTransaction.project_id == project_id,
        ).sort(-RuntimeTransaction.started_at).to_list(limit)


# ─────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────

async def _get_last_committed_tx_hash(project_id: str, exclude_tx_id: str) -> Optional[str]:
    """Get the tx_hash of the most recent committed transaction (for hash chain)."""
    txs = await RuntimeTransaction.find(
        RuntimeTransaction.project_id == project_id,
        RuntimeTransaction.status == TransactionStatus.COMMITTED,
        RuntimeTransaction.tx_id != exclude_tx_id,
    ).sort(-RuntimeTransaction.committed_at).to_list(1)

    if txs:
        return txs[0].tx_hash
    return None


def _compute_tx_hash(tx: RuntimeTransaction, prev_tx_hash: Optional[str]) -> str:
    """
    Compute a deterministic integrity hash for a transaction record.
    Chains to the previous committed transaction hash.
    """
    record = {
        "tx_id": tx.tx_id,
        "project_id": tx.project_id,
        "lease_id": tx.lease_id,
        "mutation_tier": tx.mutation_tier.value,
        "snapshot_id": tx.snapshot_id,
        "files_written": sorted(tx.files_written),
        "files_deleted": sorted(tx.files_deleted),
        "post_topology_hash": tx.post_topology_hash,
        "post_ast_hash": tx.post_ast_hash,
        "post_filesystem_hash": tx.post_filesystem_hash,
        "oracle_evidence_keys": sorted(tx.oracle_evidence_keys),
        "prev_tx_hash": prev_tx_hash or "GENESIS",
    }
    raw = json.dumps(record, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()
