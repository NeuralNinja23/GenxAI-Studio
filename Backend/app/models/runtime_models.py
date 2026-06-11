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
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from beanie import Document, Indexed
from pydantic import Field
import uuid
import numpy as np

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
    """V4 mutation classification tiers."""
    COSMETIC        = 1   # Spacing, typography, design alignment
    STRUCTURAL_UI   = 2   # Component hierarchies, layout panels
    BEHAVIORAL      = 3   # Workflow logic, state propagation, API flows
    TOPOLOGY        = 4   # Route introductions, schema relationships
    AST_EMISSION    = 5   # Targeted re-emission of generated code files
    FILE_BODY       = 6   # Direct file body replacement within a scope
    WORKSPACE_REPAIR = 7  # Full workspace re-emission (last resort)
    FORBIDDEN       = 8   # Runtime kernel, oracle hierarchy, transactions (BLOCKED)


class RepairScope(str, Enum):
    """Scope of targeted re-emission in Atlas repair mode."""
    COMPONENT = "COMPONENT"   # Single target file only
    MODULE    = "MODULE"      # All files in the target file's directory
    FEATURE   = "FEATURE"     # Files matching the feature area / package structure
    WORKSPACE = "WORKSPACE"   # Entire workspace (last resort)


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

    # Routing and taxonomy telemetry fields (derived at runtime, not stored as enum objects)
    primary_failure_category: Optional[str] = None
    active_failure_categories: List[str] = Field(default_factory=list)
    routing_decision: Optional[str] = None
    routing_reason: Optional[str] = None
    search_outcome: Optional[str] = None

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


# ─────────────────────────────────────────────────────────────
# Phase 5: Atlas Repair Faculty — Supporting Types
# ─────────────────────────────────────────────────────────────

class RepairExhaustedSignal:
    """
    Typed signal emitted by the execution kernel when all repair scopes
    (COMPONENT → MODULE → FEATURE → WORKSPACE) have been exhausted without
    achieving oracle improvement.

    This is NOT an exception and does NOT trigger Ω directly.
    The runtime receives this signal and decides independently:
        - Escalate MutationTier (if a higher tier is available), OR
        - Evaluate Ω = Converged(H) AND NoValidImprovementExists
    """
    def __init__(self, project_id: str, cycle_id: str, final_oracle: float):
        self.project_id = project_id
        self.cycle_id = cycle_id
        self.final_oracle = final_oracle

    def __repr__(self) -> str:
        return (
            f"RepairExhaustedSignal("
            f"project={self.project_id[:8]}, "
            f"oracle={self.final_oracle:.2f})"
        )


@dataclass
class RepairContext:
    """
    Scoped context passed to AtlasFaculty.

    Atlas reasons only over this context — never the full workspace.
    affected_files are inferred from FailureFingerprint.file_path fields;
    Atlas never touches files not referenced in the active failure set.

    oracle_before is the current weighted loss score Atlas is trying to reduce.
    Without this, Atlas repairs blind — it cannot calibrate instruction urgency.
    """
    affected_files:       List[Path]    # Inferred from failure traces; validated to exist
    failure_fingerprints: List[Any]     # List[FailureFingerprint] — Any to avoid circular import
    state_fingerprint:    np.ndarray    # Φ — state-level fingerprint, not per-failure
    goals:                List[str]
    oracle_before:        float         # Σ(weight_i × count_i) of current failures


@dataclass
class RepairIntent:
    """
    Declarative repair proposal from AtlasFaculty.

    Atlas owns: target_file + instruction ONLY.
    Scope is a kernel search-control concern — it is NOT part of RepairIntent.
    The kernel resolves scope from ProjectionCycleContext.current_repair_scope.
    """
    target_file:  Path
    instruction:  str    # Natural-language repair instruction for the LLM


@dataclass
class RepairOutcome:
    """
    Logged after every repair attempt (accepted or rejected).

    This is the raw signal for future adaptive repair learning.
    scope_used is the effective_scope resolved by the kernel (not proposed by Atlas).
    """
    repair_intent:   RepairIntent
    scope_used:      RepairScope    # Effective scope resolved by kernel, not Atlas
    oracle_before:   float
    oracle_after:    float
    accepted:        bool
    cycle_id:        str
    timestamp:       datetime = field(default_factory=utc_now)
