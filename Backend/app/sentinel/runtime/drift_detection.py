# app/runtime/drift_detection.py
"""
V4 Drift Detection — Stage 1: Freeze Runtime

Detects when the filesystem state diverges from the canonical AST
projection state — i.e., when files have been manually modified
outside the AST Projector pipeline.

Core law:
    Filesystem state is NEVER authoritative.
    Only the ProjectTopologyGraph → AST chain defines truth.
    Any filesystem deviation triggers one of three responses:
        1. INVALIDATE — mark the affected topology nodes as stale
        2. RECONSTRUCT — rebuild topology from AST manifests + logs
        3. ROLLBACK — restore pre-cycle snapshot (most severe drift)

Architecture:
    Drift detection runs:
        a. At the start of every projection cycle (pre-cycle check)
        b. Optionally on a polling interval (continuous monitoring)

    Detection uses the filesystem manifest from the most recent
    ProjectionSnapshot as the baseline — not the live DB state.

Governance:
    This module is in the Immutable Runtime Kernel set.
    Cognitive faculties may NOT call detect_drift() directly.
    Only execution_kernel.py and runtime_projection_validator.py
    may invoke drift detection.
"""

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set

from app.core.logging import log
from app.sentinel.runtime.projection_snapshots import (
    EXCLUDED_DIRS,
    TRACKED_EXTENSIONS,
    SnapshotManager,
)


# ─────────────────────────────────────────────────────────────
# Drift severity and response
# ─────────────────────────────────────────────────────────────

class DriftSeverity(str, Enum):
    CLEAN     = "clean"        # No drift detected
    MINOR     = "minor"        # New files added (non-tracked extensions)
    MODERATE  = "moderate"     # Tracked files added or deleted
    SEVERE    = "severe"       # Tracked files modified (content changed)
    CRITICAL  = "critical"     # Substrate / kernel files modified


class DriftResponse(str, Enum):
    NONE         = "none"         # No action required
    WARN         = "warn"         # Log warning, continue
    INVALIDATE   = "invalidate"   # Mark topology nodes as stale
    RECONSTRUCT  = "reconstruct"  # Trigger topology reconstruction
    ROLLBACK     = "rollback"     # Restore snapshot immediately


# ─────────────────────────────────────────────────────────────
# Drift result
# ─────────────────────────────────────────────────────────────

@dataclass
class DriftReport:
    severity: DriftSeverity
    recommended_response: DriftResponse
    modified_files: List[str] = field(default_factory=list)
    added_files: List[str] = field(default_factory=list)
    deleted_files: List[str] = field(default_factory=list)
    substrate_violations: List[str] = field(default_factory=list)
    snapshot_id: Optional[str] = None
    baseline_hash: Optional[str] = None
    current_hash: Optional[str] = None

    @property
    def is_clean(self) -> bool:
        return self.severity == DriftSeverity.CLEAN

    @property
    def total_deviations(self) -> int:
        return len(self.modified_files) + len(self.added_files) + len(self.deleted_files)

    def summary(self) -> str:
        if self.is_clean:
            return "No drift detected."
        return (
            f"Drift [{self.severity.value}]: "
            f"{len(self.modified_files)} modified, "
            f"{len(self.added_files)} added, "
            f"{len(self.deleted_files)} deleted. "
            f"Response: {self.recommended_response.value}"
        )


# ─────────────────────────────────────────────────────────────
# Substrate / kernel paths (CRITICAL if modified)
# ─────────────────────────────────────────────────────────────

CRITICAL_PATH_SEGMENTS: frozenset[str] = frozenset({
    "execution_kernel",
    "transaction_engine",
    "leases",
    "projection_snapshots",
    "drift_detection",
    "execution_contracts",
    "substrate_manager",
    "runtime_projection_validator",
})


# ─────────────────────────────────────────────────────────────
# Drift Detector
# ─────────────────────────────────────────────────────────────

class DriftDetector:
    """
    Detects filesystem deviations from the canonical snapshot baseline.

    Called by the execution kernel before each projection cycle and
    by the runtime projection validator during continuous monitoring.
    """

    def __init__(self, project_path: Path):
        self.project_path = project_path

    # ──────────────────────────────────────────────────────────
    # Primary entry point
    # ──────────────────────────────────────────────────────────

    async def detect(
        self,
        project_id: str,
        baseline_snapshot_id: Optional[str] = None,
    ) -> DriftReport:
        """
        Compare current filesystem state against the snapshot baseline.

        Args:
            project_id:           Project being checked.
            baseline_snapshot_id: Snapshot to compare against.
                                  If None, uses the most recent active snapshot.

        Returns:
            DriftReport with severity classification and recommended response.
        """
        # ── Load baseline manifest ────────────────────────────
        baseline_manifest: Dict[str, str] = {}
        snapshot = None

        if baseline_snapshot_id:
            snapshot = await SnapshotManager.get_snapshot(baseline_snapshot_id)
        else:
            snapshot = await SnapshotManager.get_latest_snapshot(project_id)

        if snapshot and snapshot.filesystem_manifest_path:
            manifest_path = Path(snapshot.filesystem_manifest_path)
            if manifest_path.exists():
                import json
                try:
                    baseline_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                except Exception as e:
                    log("DRIFT", f"⚠️ Could not load baseline manifest: {e}")

        if not baseline_manifest:
            # No baseline — cannot detect drift (first cycle or no snapshots)
            log("DRIFT", f"ℹ️ No baseline snapshot for {project_id} — drift check skipped")
            return DriftReport(
                severity=DriftSeverity.CLEAN,
                recommended_response=DriftResponse.NONE,
                snapshot_id=snapshot.snapshot_id if snapshot else None,
            )

        # ── Scan current filesystem ───────────────────────────
        current_manifest = _scan_filesystem(self.project_path)

        # ── Compute diff ──────────────────────────────────────
        baseline_paths: Set[str] = set(baseline_manifest.keys())
        current_paths: Set[str] = set(current_manifest.keys())

        added = sorted(current_paths - baseline_paths)
        deleted = sorted(baseline_paths - current_paths)
        modified = []

        for path in baseline_paths & current_paths:
            if baseline_manifest[path] != current_manifest[path]:
                modified.append(path)

        modified.sort()

        # ── Check for substrate / kernel violations ───────────
        substrate_violations = _check_critical_paths(modified + added + deleted)

        # ── Classify severity ─────────────────────────────────
        severity = _classify_severity(modified, added, deleted, substrate_violations)
        response = _recommend_response(severity)

        # ── Build hashes for audit ────────────────────────────
        import json
        baseline_hash = hashlib.sha256(
            json.dumps(baseline_manifest, sort_keys=True).encode()
        ).hexdigest()
        current_hash = hashlib.sha256(
            json.dumps(current_manifest, sort_keys=True).encode()
        ).hexdigest()

        report = DriftReport(
            severity=severity,
            recommended_response=response,
            modified_files=modified,
            added_files=added,
            deleted_files=deleted,
            substrate_violations=substrate_violations,
            snapshot_id=snapshot.snapshot_id if snapshot else None,
            baseline_hash=baseline_hash,
            current_hash=current_hash,
        )

        _log_report(project_id, report)
        return report

    # ──────────────────────────────────────────────────────────
    # Quick hash comparison (lightweight, no manifest load)
    # ──────────────────────────────────────────────────────────

    def compute_current_filesystem_hash(self) -> str:
        """
        Compute a single hash representing the current filesystem state.
        Used by the transaction engine to record pre/post cycle hashes.
        """
        import json
        manifest = _scan_filesystem(self.project_path)
        return hashlib.sha256(
            json.dumps(manifest, sort_keys=True).encode()
        ).hexdigest()


# ─────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────

def _scan_filesystem(project_path: Path) -> Dict[str, str]:
    """Scan the project filesystem and return relative path → SHA-256 hash map."""
    manifest: Dict[str, str] = {}
    for file_path in project_path.rglob("*"):
        if not file_path.is_file():
            continue
        if any(excl in file_path.parts for excl in EXCLUDED_DIRS):
            continue
        if file_path.suffix.lower() not in TRACKED_EXTENSIONS:
            continue
        try:
            rel = str(file_path.relative_to(project_path)).replace("\\", "/")
            content = file_path.read_bytes()
            manifest[rel] = hashlib.sha256(content).hexdigest()
        except Exception:
            pass
    return manifest


def _check_critical_paths(affected_paths: List[str]) -> List[str]:
    """Identify any modified/added/deleted paths that are critical kernel files."""
    violations = []
    for path in affected_paths:
        for segment in CRITICAL_PATH_SEGMENTS:
            if segment in path:
                violations.append(path)
                break
    return violations


def _classify_severity(
    modified: List[str],
    added: List[str],
    deleted: List[str],
    substrate_violations: List[str],
) -> DriftSeverity:
    if substrate_violations:
        return DriftSeverity.CRITICAL
    if modified:
        return DriftSeverity.SEVERE
    if added or deleted:
        return DriftSeverity.MODERATE
    return DriftSeverity.CLEAN


def _recommend_response(severity: DriftSeverity) -> DriftResponse:
    return {
        DriftSeverity.CLEAN:    DriftResponse.NONE,
        DriftSeverity.MINOR:    DriftResponse.WARN,
        DriftSeverity.MODERATE: DriftResponse.INVALIDATE,
        DriftSeverity.SEVERE:   DriftResponse.RECONSTRUCT,
        DriftSeverity.CRITICAL: DriftResponse.ROLLBACK,
    }[severity]


def _log_report(project_id: str, report: DriftReport) -> None:
    if report.is_clean:
        log("DRIFT", f"✅ No drift for {project_id}")
    else:
        log("DRIFT", f"⚠️ {project_id}: {report.summary()}")
        if report.substrate_violations:
            log("DRIFT", f"   ⛔ CRITICAL — Substrate violations: {report.substrate_violations}")
        if report.modified_files:
            log("DRIFT", f"   📝 Modified: {report.modified_files[:5]}"
                         + ("..." if len(report.modified_files) > 5 else ""))
        if report.added_files:
            log("DRIFT", f"   ➕ Added: {report.added_files[:5]}"
                         + ("..." if len(report.added_files) > 5 else ""))
        if report.deleted_files:
            log("DRIFT", f"   ➖ Deleted: {report.deleted_files[:5]}"
                         + ("..." if len(report.deleted_files) > 5 else ""))
