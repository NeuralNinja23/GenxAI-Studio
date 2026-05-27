# app/substrate/substrate_manager.py
"""
V4 Substrate Manager — Stage 1: Freeze Runtime

Manages the Stable Execution Substrate: the deterministic, immutable
foundation of React/Vite, Tailwind, FastAPI, Docker, and Database
structures that underpin every generated project.

Architecture:
    - Substrate is INSTANTIATED once at workspace creation
    - Configuration hashes are LOCKED into SubstrateManifest immediately
    - Any attempt to modify locked substrate files triggers a
      Tier 5 Forbidden Mutation block in the Constraint Engine

Laws:
    - Framework substrates are never touched by cognitive faculties
    - LLMs may NOT modify package.json, vite.config.ts, tailwind.config.js,
      requirements.txt, or docker-compose.yml
    - Substrate integrity is verified at the start of every projection cycle
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.time import utc_now

from app.core.logging import log
from app.models.runtime_models import SubstrateManifest


# ─────────────────────────────────────────────────────────────
# Locked substrate file registry
# Each path is relative to the project root
# ─────────────────────────────────────────────────────────────

LOCKED_SUBSTRATE_FILES: list[str] = [
    "frontend/package.json",
    "frontend/vite.config.ts",
    "frontend/tailwind.config.js",
    "frontend/tsconfig.json",
    "frontend/tsconfig.node.json",
    "backend/requirements.txt",
    "backend/Dockerfile",
    "frontend/Dockerfile",
    "docker-compose.yml",
]

# Files that are NEVER writeable by any faculty (absolute prohibitions)
FORBIDDEN_WRITE_TARGETS: frozenset[str] = frozenset(LOCKED_SUBSTRATE_FILES)


class SubstrateIntegrityError(Exception):
    """Raised when a locked substrate file has been modified outside the kernel."""


class SubstrateManager:
    """
    Stable Execution Substrate manager.

    Responsibilities:
        1. Scan and hash substrate files at workspace creation (lock)
        2. Verify substrate integrity at the start of each projection cycle
        3. Block Tier 5 mutations targeting locked substrate paths
    """

    # ──────────────────────────────────────────────────────────
    # Lock substrate at workspace creation
    # ──────────────────────────────────────────────────────────

    @staticmethod
    async def lock_substrate(
        project_id: str,
        project_path: Path,
        framework_versions: Optional[Dict[str, str]] = None,
    ) -> SubstrateManifest:
        """
        Record and lock the stable execution substrate for a project.

        Called exactly ONCE by the execution kernel after scaffolding completes.
        Computes SHA-256 hashes of all locked substrate files and persists
        the manifest to MongoDB.

        Args:
            project_id:          Project identifier.
            project_path:        Absolute path to the project workspace.
            framework_versions:  Optional dict of framework versions to record.

        Returns:
            The locked SubstrateManifest document.
        """
        # Check if already locked
        existing = await SubstrateManifest.find_one(
            SubstrateManifest.project_id == project_id
        )
        if existing and existing.is_locked:
            log("SUBSTRATE", f"⚠️ Substrate for {project_id} already locked — returning existing manifest")
            return existing

        hashes: Dict[str, str] = {}
        substrate_config: Dict[str, Any] = {}

        for rel_path in LOCKED_SUBSTRATE_FILES:
            full_path = project_path / rel_path
            if full_path.exists():
                content = full_path.read_bytes()
                hashes[rel_path] = hashlib.sha256(content).hexdigest()

                # Extract version info from package.json
                if rel_path.endswith("package.json"):
                    try:
                        pkg = json.loads(content.decode("utf-8"))
                        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                        substrate_config["package_json_deps"] = deps
                    except Exception:
                        pass
            else:
                hashes[rel_path] = "MISSING"

        fv = framework_versions or {}

        manifest = SubstrateManifest(
            project_id=project_id,
            react_version=fv.get("react"),
            vite_version=fv.get("vite"),
            tailwind_version=fv.get("tailwind"),
            fastapi_version=fv.get("fastapi"),
            python_version=fv.get("python"),
            package_json_hash=hashes.get("frontend/package.json"),
            vite_config_hash=hashes.get("frontend/vite.config.ts"),
            tailwind_config_hash=hashes.get("frontend/tailwind.config.js"),
            requirements_hash=hashes.get("backend/requirements.txt"),
            docker_compose_hash=hashes.get("docker-compose.yml"),
            substrate_config={**substrate_config, "file_hashes": hashes},
            is_locked=True,
            locked_at=utc_now(),
        )

        if existing:
            existing.is_locked = True
            existing.locked_at = manifest.locked_at
            existing.substrate_config = manifest.substrate_config
            existing.package_json_hash = manifest.package_json_hash
            existing.vite_config_hash = manifest.vite_config_hash
            existing.tailwind_config_hash = manifest.tailwind_config_hash
            existing.requirements_hash = manifest.requirements_hash
            existing.docker_compose_hash = manifest.docker_compose_hash
            await existing.save()
            log("SUBSTRATE", f"🔒 Substrate LOCKED for {project_id} ({len(hashes)} files hashed)")
            return existing

        await manifest.insert()
        log("SUBSTRATE", f"🔒 Substrate LOCKED for {project_id} ({len(hashes)} files hashed)")
        return manifest

    # ──────────────────────────────────────────────────────────
    # Verify integrity before each projection cycle
    # ──────────────────────────────────────────────────────────

    @staticmethod
    async def verify_integrity(
        project_id: str,
        project_path: Path,
    ) -> tuple[bool, list[str]]:
        """
        Verify that no locked substrate file has been modified.

        Called by the execution kernel at the start of each projection cycle.

        Returns:
            (is_clean: bool, violations: list[str])
            violations is empty when is_clean is True.
        """
        manifest = await SubstrateManifest.find_one(
            SubstrateManifest.project_id == project_id
        )

        if manifest is None or not manifest.is_locked:
            # No manifest yet — substrate not locked, skip check
            return True, []

        stored_hashes: Dict[str, str] = manifest.substrate_config.get("file_hashes", {})
        violations: list[str] = []

        for rel_path in LOCKED_SUBSTRATE_FILES:
            stored_hash = stored_hashes.get(rel_path)
            if stored_hash == "MISSING":
                continue  # Was missing at lock time; still expect it missing or accept

            full_path = project_path / rel_path
            if not full_path.exists():
                if stored_hash and stored_hash != "MISSING":
                    violations.append(f"DELETED: {rel_path}")
                continue

            current_hash = hashlib.sha256(full_path.read_bytes()).hexdigest()
            if current_hash != stored_hash:
                violations.append(f"MODIFIED: {rel_path}")

        if violations:
            log("SUBSTRATE", f"⛔ Substrate integrity violation for {project_id}: {violations}")
        else:
            log("SUBSTRATE", f"✅ Substrate integrity verified for {project_id}")

        return len(violations) == 0, violations

    # ──────────────────────────────────────────────────────────
    # Mutation guard (called by Constraint Engine)
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def is_forbidden_write_target(relative_path: str) -> bool:
        """
        Returns True if the path is a locked substrate file.

        The Constraint Engine calls this before any AST projection write.
        If True, the mutation is Tier 5 (FORBIDDEN) and must be blocked.
        """
        # Normalize path separators
        normalized = relative_path.replace("\\", "/")
        return normalized in FORBIDDEN_WRITE_TARGETS

    # ──────────────────────────────────────────────────────────
    # Retrieve manifest
    # ──────────────────────────────────────────────────────────

    @staticmethod
    async def get_manifest(project_id: str) -> Optional[SubstrateManifest]:
        """Retrieve the substrate manifest for a project."""
        return await SubstrateManifest.find_one(
            SubstrateManifest.project_id == project_id
        )
