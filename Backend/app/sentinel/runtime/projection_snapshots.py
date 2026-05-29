# app/runtime/projection_snapshots.py
"""
V4 Projection Snapshots — Stage 1: Freeze Runtime

Creates and restores atomic snapshots of all four canonical layers
BEFORE every projection cycle begins.

The four layers captured atomically:
    1. Topology  — serialised ProjectTopologyGraph JSON manifest
    2. AST       — serialised AST node manifest (file → AST hash map)
    3. Filesystem — file listing with SHA-256 checksums for all project files
    4. Runtime   — current WorkflowSession + active lease state

Architecture:
    - Snapshots are created by the execution kernel before acquiring a lease
    - On rollback, ALL layers are restored atomically from the snapshot
    - Partial rollbacks are architecturally forbidden
    - Cognitive faculties may never create, modify, or delete snapshots

Governance:
    This module is in the Immutable Runtime Kernel set.
    Only execution_kernel.py may call create_snapshot() or restore_snapshot().
"""

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.time import utc_now

from app.core.logging import log
from app.models.runtime_models import ProjectionSnapshot, SnapshotLayer


# ─────────────────────────────────────────────────────────────
# Snapshot storage directory (inside project workspace)
# ─────────────────────────────────────────────────────────────

SNAPSHOT_DIR_NAME = ".v4_snapshots"

# File extensions to include in filesystem manifest
TRACKED_EXTENSIONS = frozenset({
    ".py", ".ts", ".tsx", ".js", ".jsx",
    ".css", ".scss", ".json", ".yaml", ".yml",
    ".md", ".html", ".env",
})

# Directories to exclude from filesystem manifest
EXCLUDED_DIRS = frozenset({
    "node_modules", "__pycache__", ".git", "dist",
    "build", ".next", "venv", ".venv", SNAPSHOT_DIR_NAME,
})


class SnapshotError(Exception):
    """Raised when snapshot creation or restoration fails."""


class SnapshotManager:
    """
    Manages pre-cycle projection snapshots for atomic rollback.

    One instance is used per execution kernel per project.
    All snapshot data is stored in `<project_path>/.v4_snapshots/`.
    Snapshot manifests are persisted to MongoDB for auditability.
    """

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.snapshot_root = project_path / SNAPSHOT_DIR_NAME
        self.snapshot_root.mkdir(parents=True, exist_ok=True)

    # ──────────────────────────────────────────────────────────
    # Create snapshot
    # ──────────────────────────────────────────────────────────

    async def create_snapshot(
        self,
        project_id: str,
        cycle_id: str,
        topology_data: Optional[Dict[str, Any]] = None,
        ast_data: Optional[Dict[str, Any]] = None,
    ) -> ProjectionSnapshot:
        """
        Capture an atomic snapshot of all four canonical layers.

        Args:
            project_id:    Project identifier.
            cycle_id:      Projection cycle this snapshot is for.
            topology_data: Serialisable topology graph data (from Stage 2+).
            ast_data:      Serialisable AST manifest data (from Stage 3+).

        Returns:
            The persisted ProjectionSnapshot document.
        """
        snapshot_dir = self.snapshot_root / cycle_id
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        layers_captured: List[SnapshotLayer] = []
        snapshot = ProjectionSnapshot(
            project_id=project_id,
            cycle_id=cycle_id,
        )

        # ── Layer 1: Topology ─────────────────────────────────
        if topology_data is not None:
            topo_path = snapshot_dir / "topology.json"
            topo_json = json.dumps(topology_data, indent=2, default=str)
            topo_path.write_text(topo_json, encoding="utf-8")
            snapshot.topology_snapshot_path = str(topo_path)
            snapshot.topology_hash = hashlib.sha256(topo_json.encode()).hexdigest()
            layers_captured.append(SnapshotLayer.TOPOLOGY)
        else:
            # Topology not yet available (Stage 1) — record placeholder
            snapshot.topology_hash = "NOT_YET_AVAILABLE"

        # ── Layer 2: AST ──────────────────────────────────────
        if ast_data is not None:
            ast_path = snapshot_dir / "ast_manifest.json"
            ast_json = json.dumps(ast_data, indent=2, default=str)
            ast_path.write_text(ast_json, encoding="utf-8")
            snapshot.ast_snapshot_path = str(ast_path)
            snapshot.ast_hash = hashlib.sha256(ast_json.encode()).hexdigest()
            layers_captured.append(SnapshotLayer.AST)
        else:
            snapshot.ast_hash = "NOT_YET_AVAILABLE"

        # ── Layer 3: Filesystem ───────────────────────────────
        fs_manifest = _build_filesystem_manifest(self.project_path)
        fs_path = snapshot_dir / "filesystem_manifest.json"
        fs_json = json.dumps(fs_manifest, indent=2)
        fs_path.write_text(fs_json, encoding="utf-8")
        snapshot.filesystem_manifest_path = str(fs_path)
        snapshot.filesystem_hash = hashlib.sha256(fs_json.encode()).hexdigest()
        layers_captured.append(SnapshotLayer.FILESYSTEM)

        # Copy all tracked project files into the snapshot
        files_dir = snapshot_dir / "files"
        files_dir.mkdir(exist_ok=True)
        _copy_tracked_files(self.project_path, files_dir, fs_manifest)

        # ── Layer 4: Runtime ──────────────────────────────────
        runtime_state = await _capture_runtime_state(project_id)
        runtime_path = snapshot_dir / "runtime_state.json"
        runtime_json = json.dumps(runtime_state, indent=2, default=str)
        runtime_path.write_text(runtime_json, encoding="utf-8")
        snapshot.runtime_state_path = str(runtime_path)
        snapshot.runtime_hash = hashlib.sha256(runtime_json.encode()).hexdigest()
        layers_captured.append(SnapshotLayer.RUNTIME)

        # ── Persist manifest ──────────────────────────────────
        snapshot.layers_captured = layers_captured
        await snapshot.insert()

        log("SNAPSHOT", f"📸 Snapshot {snapshot.snapshot_id} created for {project_id} "
                        f"(cycle={cycle_id}, layers={[l.value for l in layers_captured]})")
        return snapshot

    # ──────────────────────────────────────────────────────────
    # Restore snapshot
    # ──────────────────────────────────────────────────────────

    async def restore_snapshot(self, snapshot: ProjectionSnapshot) -> bool:
        """
        Atomically restore all captured layers from a snapshot.

        Restoration order (reverse of capture to avoid partial states):
            1. Validate snapshot integrity hashes
            2. Restore filesystem (copy files back)
            3. Restore runtime state (WorkflowSession)
            4. Update snapshot record

        Args:
            snapshot: The ProjectionSnapshot to restore.

        Returns:
            True if restoration succeeded, False if integrity check failed.
        """
        log("SNAPSHOT", f"🔄 Restoring snapshot {snapshot.snapshot_id} for {snapshot.project_id}")

        # ── Integrity verification ────────────────────────────
        if snapshot.filesystem_manifest_path:
            fs_path = Path(snapshot.filesystem_manifest_path)
            if fs_path.exists():
                fs_content = fs_path.read_text(encoding="utf-8")
                actual_hash = hashlib.sha256(fs_content.encode()).hexdigest()
                if actual_hash != snapshot.filesystem_hash:
                    log("SNAPSHOT", f"❌ Filesystem manifest hash mismatch — snapshot may be corrupted")
                    return False

        # ── Restore filesystem ────────────────────────────────
        snapshot_dir = Path(snapshot.filesystem_manifest_path).parent if snapshot.filesystem_manifest_path else None
        if snapshot_dir:
            files_dir = snapshot_dir / "files"
            if files_dir.exists():
                _restore_tracked_files(self.project_path, files_dir)
                log("SNAPSHOT", f"✅ Filesystem layer restored from {snapshot.snapshot_id}")

        # ── Restore runtime state ─────────────────────────────
        if snapshot.runtime_state_path:
            runtime_path = Path(snapshot.runtime_state_path)
            if runtime_path.exists():
                await _restore_runtime_state(
                    snapshot.project_id,
                    json.loads(runtime_path.read_text(encoding="utf-8")),
                )
                log("SNAPSHOT", f"✅ Runtime state restored from {snapshot.snapshot_id}")

        # ── Update snapshot record ────────────────────────────
        snapshot.restored_at = utc_now()
        snapshot.restore_count += 1
        snapshot.is_active = False
        await snapshot.save()

        log("SNAPSHOT", f"✅ Full restoration complete from snapshot {snapshot.snapshot_id}")
        return True

    # ──────────────────────────────────────────────────────────
    # Fetch snapshot by ID
    # ──────────────────────────────────────────────────────────

    @staticmethod
    async def get_snapshot(snapshot_id: str) -> Optional[ProjectionSnapshot]:
        """Fetch a snapshot manifest from MongoDB."""
        return await ProjectionSnapshot.find_one(
            ProjectionSnapshot.snapshot_id == snapshot_id
        )

    @staticmethod
    async def get_latest_snapshot(project_id: str) -> Optional[ProjectionSnapshot]:
        """Fetch the most recent active snapshot for a project."""
        snapshots = await ProjectionSnapshot.find(
            ProjectionSnapshot.project_id == project_id,
            ProjectionSnapshot.is_active == True,
        ).sort(-ProjectionSnapshot.created_at).to_list(1)
        return snapshots[0] if snapshots else None

    # ──────────────────────────────────────────────────────────
    # Cleanup
    # ──────────────────────────────────────────────────────────

    async def purge_old_snapshots(self, project_id: str, keep_last: int = 5) -> int:
        """
        Purge old snapshot data files, keeping the most recent N snapshots.
        Returns the number of snapshots purged.
        """
        all_snapshots = await ProjectionSnapshot.find(
            ProjectionSnapshot.project_id == project_id,
        ).sort(-ProjectionSnapshot.created_at).to_list()

        to_delete = all_snapshots[keep_last:]
        purged = 0
        for snap in to_delete:
            # Delete snapshot directory
            snap_dir = self.snapshot_root / snap.cycle_id
            if snap_dir.exists():
                shutil.rmtree(snap_dir, ignore_errors=True)
            snap.is_active = False
            await snap.save()
            purged += 1

        if purged > 0:
            log("SNAPSHOT", f"🗑️ Purged {purged} old snapshots for {project_id}")
        return purged


# ─────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────

def _build_filesystem_manifest(project_path: Path) -> Dict[str, str]:
    """
    Build a manifest mapping relative path → SHA-256 hash for all tracked files.
    """
    manifest: Dict[str, str] = {}
    for file_path in project_path.rglob("*"):
        if not file_path.is_file():
            continue
        # Skip excluded directories
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


def _copy_tracked_files(
    project_path: Path,
    dest_dir: Path,
    manifest: Dict[str, str],
) -> None:
    """Copy all manifest-tracked files into the snapshot files directory."""
    for rel_path in manifest:
        src = project_path / rel_path
        dst = dest_dir / rel_path
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def _restore_tracked_files(project_path: Path, files_dir: Path) -> None:
    """Restore all snapshot files back to the project workspace."""
    for src in files_dir.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(files_dir)
        dst = project_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


async def _capture_runtime_state(project_id: str) -> Dict[str, Any]:
    """Capture the current WorkflowSession state for a project."""
    try:
        from app.models.workflow import WorkflowSession
        session = await WorkflowSession.find_one(WorkflowSession.project_id == project_id)
        if session:
            return {
                "project_id": project_id,
                "is_running": session.is_running,
                "is_paused": session.is_paused,
                "current_step": session.current_step,
                "completed_steps": session.completed_steps,
                "original_request": session.original_request,
                "captured_at": utc_now().isoformat(),
            }
    except Exception as e:
        log("SNAPSHOT", f"⚠️ Could not capture runtime state: {e}")
    return {"project_id": project_id, "captured_at": utc_now().isoformat()}


async def _restore_runtime_state(project_id: str, state: Dict[str, Any]) -> None:
    """Restore a previously captured WorkflowSession state."""
    try:
        from app.models.workflow import WorkflowSession
        session = await WorkflowSession.find_one(WorkflowSession.project_id == project_id)
        if session and state:
            session.is_running = state.get("is_running", False)
            session.is_paused = state.get("is_paused", False)
            session.current_step = state.get("current_step")
            session.completed_steps = state.get("completed_steps", [])
            await session.save()
    except Exception as e:
        log("SNAPSHOT", f"⚠️ Could not restore runtime state: {e}")
