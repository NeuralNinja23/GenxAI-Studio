# app/runtime/runtime_projection_validator.py
"""
V4 Runtime Projection Validator — Stage 5: Runtime Synchronization

The Sensory Grounding Cortex of ArborMind.
Continuously verifies parity between AST projection manifest, actual disk files,
and database topology graphs to assert physical alignment.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import hashlib
from pydantic import BaseModel

from app.core.logging import log
from app.runtime.drift_detection import DriftSeverity, DriftResponse
from app.topology.topology_version_manager import TopologyVersionManager

class ParityReport(BaseModel):
    congruence_score: float
    severity: DriftSeverity
    recommended_response: DriftResponse
    mismatched_files: List[str] = []
    missing_files: List[str] = []
    extra_files: List[str] = []
    topology_hash_aligned: bool = True
    manifest_present: bool = True


class RuntimeProjectionValidator:
    """
    Sensory Grounding Cortex continuously checking filesystem congruence
    against active AST projections and database canonical graphs.
    """

    @classmethod
    async def validate_parity(cls, project_id: str, project_path: Path) -> ParityReport:
        log("SENSORY_CORTEX", f"👁️ Scanning filesystem parity and grounding congruence for {project_id}")

        manifest_path = project_path / ".genx_ast_manifest.json"
        if not manifest_path.exists():
            log("SENSORY_CORTEX", f"⚠️ Grounding manifest missing on disk: {manifest_path}")
            return ParityReport(
                congruence_score=0.0,
                severity=DriftSeverity.SEVERE,
                recommended_response=DriftResponse.RECONSTRUCT,
                manifest_present=False,
                topology_hash_aligned=False
            )

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
        except Exception as err:
            log("SENSORY_CORTEX", f"❌ Failed to parse grounding manifest: {err}")
            return ParityReport(
                congruence_score=0.0,
                severity=DriftSeverity.SEVERE,
                recommended_response=DriftResponse.RECONSTRUCT,
                manifest_present=False,
                topology_hash_aligned=False
            )

        projections: Dict[str, str] = manifest_data.get("projections", {})
        if not projections:
            log("SENSORY_CORTEX", "ℹ️ Grounding manifest has zero file projections registered.")
            return ParityReport(
                congruence_score=1.0,
                severity=DriftSeverity.CLEAN,
                recommended_response=DriftResponse.NONE,
                manifest_present=True,
                topology_hash_aligned=True
            )

        mismatched_files = []
        missing_files = []
        extra_files = []
        matched_count = 0

        # Scan each projected file listed in manifest
        for rel_path, expected_hash in projections.items():
            full_path = project_path / rel_path
            if not full_path.exists():
                missing_files.append(rel_path)
                continue

            try:
                content = full_path.read_bytes()
                actual_hash = hashlib.sha256(content).hexdigest()
                if actual_hash == expected_hash:
                    matched_count += 1
                else:
                    mismatched_files.append(rel_path)
            except Exception as read_err:
                log("SENSORY_CORTEX", f"⚠️ Error reading {rel_path} for sensory check: {read_err}")
                mismatched_files.append(rel_path)

        # Look for extra tracked files that weren't projected but are present
        from app.runtime.projection_snapshots import TRACKED_EXTENSIONS, EXCLUDED_DIRS
        for p in project_path.rglob("*"):
            if not p.is_file():
                continue
            if any(excl in p.parts for excl in EXCLUDED_DIRS):
                continue
            if p.suffix.lower() not in TRACKED_EXTENSIONS:
                continue
            
            rel_str = str(p.relative_to(project_path)).replace("\\", "/")
            if rel_str == ".genx_ast_manifest.json":
                continue
            if rel_str not in projections:
                extra_files.append(rel_str)

        # Calculate congruence score
        total_tracked_files = len(projections)
        congruence_score = matched_count / total_tracked_files if total_tracked_files > 0 else 1.0

        # Check topology graph hash alignment with DB canonical topology graph
        topology_hash_aligned = True
        db_graph = await TopologyVersionManager.get_active_topology(project_id)
        if db_graph:
            manifest_graph_hash = manifest_data.get("topology", {}).get("graph_hash")
            if manifest_graph_hash != db_graph.graph_hash:
                log("SENSORY_CORTEX", f"⚠️ Topology split-brain: manifest graph hash {manifest_graph_hash} != active graph hash {db_graph.graph_hash}")
                topology_hash_aligned = False
        else:
            log("SENSORY_CORTEX", f"⚠️ No database topology found for {project_id} during sensory scan.")
            topology_hash_aligned = False

        # Classify drift severity
        severity = DriftSeverity.CLEAN
        if not topology_hash_aligned:
            severity = DriftSeverity.SEVERE
        elif mismatched_files or missing_files:
            severity = DriftSeverity.SEVERE
        elif extra_files:
            severity = DriftSeverity.MODERATE

        # Map to recommended drift response
        recommended_response = DriftResponse.NONE
        if severity == DriftSeverity.SEVERE:
            recommended_response = DriftResponse.RECONSTRUCT
        elif severity == DriftSeverity.MODERATE:
            recommended_response = DriftResponse.INVALIDATE

        # If any substrate config files (e.g. package.json, requirements.txt, docker-compose) are modified/missing, elevate to CRITICAL/rollback
        critical_changed = False
        from app.runtime.drift_detection import CRITICAL_PATH_SEGMENTS
        all_issues = mismatched_files + missing_files
        for issue in all_issues:
            if any(seg in issue for seg in CRITICAL_PATH_SEGMENTS) or "package.json" in issue or "requirements.txt" in issue or "docker-compose" in issue:
                critical_changed = True
                break
        
        if critical_changed:
            severity = DriftSeverity.CRITICAL
            recommended_response = DriftResponse.ROLLBACK

        report = ParityReport(
            congruence_score=congruence_score,
            severity=severity,
            recommended_response=recommended_response,
            mismatched_files=mismatched_files,
            missing_files=missing_files,
            extra_files=extra_files,
            topology_hash_aligned=topology_hash_aligned,
            manifest_present=True
        )

        log("SENSORY_CORTEX", f"👁️ Congruence check finished: score={congruence_score:.2f}, severity={severity.value}, response={recommended_response.value}")
        return report
