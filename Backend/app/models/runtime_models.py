# app/models/runtime_models.py
"""
V4 Runtime Persistence Models — Stage 1: Freeze Runtime

Beanie documents for the deterministic execution substrate.

Collections:
    execution_leases       — Distributed execution locks (prevents split-brain)
    runtime_transactions   — Transaction journal (commit/rollback record)
    projection_snapshots   — Pre-cycle snapshot manifests (rollback targets)
    substrate_manifests    — Locked framework config registry (immutable during execution)

These models are governed by the Immutable Runtime Kernel law:
    No cognitive faculty may write to or modify these collections.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from beanie import Document, Indexed
from pydantic import Field
import uuid

from app.core.time import utc_now


# ─────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────

class LeaseStatus(str, Enum):
    ACTIVE    = "active"
    RELEASED  = "released"
    EXPIRED   = "expired"
    STOLEN    = "stolen"       # Acquired after previous holder expired


class TransactionStatus(str, Enum):
    PENDING   = "pending"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED    = "failed"


class SnapshotLayer(str, Enum):
    TOPOLOGY  = "topology"
    AST       = "ast"
    FILESYSTEM = "filesystem"
    RUNTIME   = "runtime"


class MutationTier(int, Enum):
    """V4 mutation classification tiers (from implementation plan)."""
    COSMETIC    = 1   # Spacing, typography, design alignment
    STRUCTURAL_UI = 2  # Component hierarchies, layout panels
    BEHAVIORAL  = 3   # Workflow logic, state propagation, API flows
    TOPOLOGY    = 4   # Route introductions, schema relationships
    FORBIDDEN   = 5   # Runtime kernel, oracle hierarchy, transactions (BLOCKED)


# ─────────────────────────────────────────────────────────────
# 1. Execution Lease
# ─────────────────────────────────────────────────────────────

class ExecutionLease(Document):
    """
    Distributed execution lock preventing split-brain states.

    A lease MUST be acquired before any projection cycle begins.
    The execution kernel enforces lease ownership; no code outside
    the kernel may acquire, renew, or release leases.

    Governance: Immutable Runtime Kernel — cognitive faculties
    are permanently prohibited from touching this collection.
    """
    lease_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: Indexed(str)
    holder_id: str                     # Unique kernel instance ID
    status: LeaseStatus = LeaseStatus.ACTIVE
    acquired_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime               # TTL enforced by kernel heartbeat
    released_at: Optional[datetime] = None
    cycle_id: Optional[str] = None     # Associated projection cycle
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Settings:
        name = "execution_leases"


# ─────────────────────────────────────────────────────────────
# 2. Runtime Transaction
# ─────────────────────────────────────────────────────────────

class RuntimeTransaction(Document):
    """
    Transaction journal entry for every projection cycle.

    Each cycle is atomic: either all AST projections commit or
    the entire cycle rolls back to the pre-cycle snapshot.

    Hash chain: every committed transaction includes the hash of
    the previous committed transaction — forming a tamper-evident
    structural integrity chain.

    Governance: No cognitive faculty may initiate, commit, or
    roll back transactions. Exclusively managed by execution_kernel.py.
    """
    tx_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: Indexed(str)
    lease_id: str                          # Must match active lease
    status: TransactionStatus = TransactionStatus.PENDING
    mutation_tier: MutationTier            # Determines what is allowed
    snapshot_id: str                       # Pre-cycle snapshot to rollback to
    files_written: List[str] = Field(default_factory=list)
    files_deleted: List[str] = Field(default_factory=list)

    # Integrity hashes
    pre_topology_hash: Optional[str] = None
    post_topology_hash: Optional[str] = None
    pre_ast_hash: Optional[str] = None
    post_ast_hash: Optional[str] = None
    pre_filesystem_hash: Optional[str] = None
    post_filesystem_hash: Optional[str] = None
    prev_tx_hash: Optional[str] = None    # Hash chain link
    tx_hash: Optional[str] = None         # Hash of this transaction's record

    # Oracle evidence keys (must be present before commit)
    oracle_evidence_keys: List[str] = Field(default_factory=list)
    oracle_results: Dict[str, Any] = Field(default_factory=dict)

    started_at: datetime = Field(default_factory=utc_now)
    committed_at: Optional[datetime] = None
    rolled_back_at: Optional[datetime] = None
    error: Optional[str] = None

    class Settings:
        name = "runtime_transactions"


# ─────────────────────────────────────────────────────────────
# 3. Projection Snapshot
# ─────────────────────────────────────────────────────────────

class ProjectionSnapshot(Document):
    """
    Pre-cycle snapshot manifest.

    Before every projection cycle, the execution kernel captures
    atomic snapshots of all four canonical layers:
        topology → AST → filesystem → runtime

    On rollback, ALL layers are restored atomically from this manifest.
    Partial rollbacks are architecturally forbidden.

    Governance: Created exclusively by projection_snapshots.py.
    Cognitive faculties may never create or delete snapshots.
    """
    snapshot_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: Indexed(str)
    cycle_id: str                          # Projection cycle this was taken for
    tx_id: Optional[str] = None           # Transaction that consumed this snapshot

    # Layer hashes (used to verify restore fidelity)
    topology_hash: Optional[str] = None
    ast_hash: Optional[str] = None
    filesystem_hash: Optional[str] = None
    runtime_hash: Optional[str] = None

    # Storage references for each layer snapshot
    topology_snapshot_path: Optional[str] = None    # Serialised topology JSON path
    ast_snapshot_path: Optional[str] = None         # Serialised AST manifest path
    filesystem_manifest_path: Optional[str] = None  # File listing + checksums path
    runtime_state_path: Optional[str] = None        # Runtime state dump path

    # Metadata
    layers_captured: List[SnapshotLayer] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    restored_at: Optional[datetime] = None
    is_active: bool = True                 # False once superseded or consumed
    restore_count: int = 0

    class Settings:
        name = "projection_snapshots"


# ─────────────────────────────────────────────────────────────
# 4. Substrate Manifest
# ─────────────────────────────────────────────────────────────

class SubstrateManifest(Document):
    """
    Locked framework configuration registry.

    Records the stable execution substrate configuration
    (React/Vite, Tailwind, FastAPI, Docker, Database versions and
    configuration hashes) at workspace creation time.

    Once written, the substrate manifest is IMMUTABLE during execution.
    Any attempt by a cognitive faculty to modify these values is
    blocked by the Constraint Engine (Tier 5 — Forbidden Mutation).

    Governance: Written exclusively by substrate_manager.py at
    workspace initialisation. Never mutated thereafter.
    """
    manifest_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: Indexed(str, unique=True)

    # Framework versions (locked at scaffold time)
    react_version: Optional[str] = None
    vite_version: Optional[str] = None
    tailwind_version: Optional[str] = None
    fastapi_version: Optional[str] = None
    python_version: Optional[str] = None

    # Configuration integrity hashes (detect tampering)
    package_json_hash: Optional[str] = None
    vite_config_hash: Optional[str] = None
    tailwind_config_hash: Optional[str] = None
    requirements_hash: Optional[str] = None
    docker_compose_hash: Optional[str] = None

    # Substrate configuration (locked values)
    substrate_config: Dict[str, Any] = Field(default_factory=dict)

    # Lock status
    is_locked: bool = False               # True once all hashes are recorded
    locked_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "substrate_manifests"
