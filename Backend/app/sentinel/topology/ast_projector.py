# app/topology/ast_projector.py
"""
V4 AST Projector — Stage 3: AST Pipeline
Decides atomic transaction bounds and coordinates S-0 SentinelVerificationGate.
"""

import json
import os
import time
import shutil
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional

from app.core.logging import log
from app.sentinel.topology.ast_generator import ASTFile, ASTGenerator
from app.sentinel.topology.ast_validator import ASTValidator
from app.sentinel.topology.topology_version_manager import TopologyVersionManager
from app.sentinel.topology.projection_metrics import ProjectionMetrics
from app.sentinel.failure_memory.failure_recorder import record_failure, FailureType, Severity
from app.sentinel.verification.verification_gate import SentinelVerificationGate, FailureFingerprint
from app.sentinel.failure_memory.failure_geometry import FailureGeometry


class ASTProjector:
    """
    Syntactic Projection Medium with Atomic Transactional Stages.
    Stages writes inside a secure local sandbox buffer, running the 
    SentinelVerificationGate before applying atomic disk commits.
    """

    @classmethod
    def _generate_error_placeholder(cls, rel_path: str, component_name: str, error: Exception) -> str:
        safe_error = str(error).replace("'", "\\'").replace('"', '\\"').replace("\n", " ")
        return (
            f"import React from 'react';\n\n"
            f"export default function {component_name}() {{\n"
            f"  return (\n"
            f"    <div style={{{{\n"
            f"      margin: '24px',\n"
            f"      padding: '24px',\n"
            f"      borderRadius: '12px',\n"
            f"      border: '1px solid rgba(239, 68, 68, 0.3)',\n"
            f"      color: '#f1f5f9',\n"
            f"    }}}}>\n"
            f"      <h2>Projection Error: {component_name}</h2>\n"
            f"      <pre>{safe_error[:500]}</pre>\n"
            f"    </div>\n"
            f"  );\n"
            f"}}\n"
        )

    @classmethod
    async def project(cls, cycle_ctx) -> Dict[str, Any]:
        metrics = ProjectionMetrics.get_instance()
        metrics.reset()

        project_id = cycle_ctx.project_id
        project_path = Path(cycle_ctx.project_path)
        staging_path = project_path / ".genx_staging"

        log("PROJECTOR", f"📡 Initiating AST projection cycle for project {project_id}")

        graph = await TopologyVersionManager.get_active_topology(project_id)
        if not graph:
            from app.sentinel.directives import IntentField
            intent = await IntentField.find_one({"project_id": project_id})
            if intent:
                from app.sentinel.topology.topology_compiler import TopologyCompiler
                graph = TopologyCompiler.compile_intent(project_id, intent)
                await TopologyVersionManager.commit_topology(project_id, graph, author="kernel")
            else:
                log("PROJECTOR", f"⚠️ No active topology or intent found for {project_id}. Nothing to project.")
                return {"files_written": [], "files_deleted": [], "partial": False, "metrics": metrics.summary()}

        from app.sentinel.topology.node_types import NodeType
        total_nodes = len(graph.nodes)
        ui_count = sum(1 for n in graph.nodes.values() if n.node_type == NodeType.UI_NODE)
        metrics.set_ui_node_count(ui_count)

        ast_files = ASTGenerator.generate(graph)

        # ─────────────────────────────────────────────────────────────
        # S-0.10: Atomic Transaction Staging Bounds
        # ─────────────────────────────────────────────────────────────
        if staging_path.exists():
            shutil.rmtree(staging_path)
        staging_path.mkdir(parents=True, exist_ok=True)

        files_written: List[str] = []
        failed_files: List[Dict[str, str]] = []
        is_partial = False

        for rel_path, ast_file in ast_files.items():
            metrics.record_projection_attempt(rel_path)
            
            # Staged destination file
            staged_file_path = staging_path / rel_path

            try:
                val_result = ASTValidator.validate_file(ast_file)
                if not val_result.get("passed"):
                    raise ValueError(f"AST validation failure: {'; '.join(val_result.get('errors', []))}")

                staged_file_path.parent.mkdir(parents=True, exist_ok=True)
                rendered_code = ast_file.render()

                with open(staged_file_path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(rendered_code)

                files_written.append(rel_path)
                metrics.record_projection_success(rel_path)

            except Exception as projection_err:
                is_partial = True
                tb_str = traceback.format_exc()
                log("PROJECTOR", f"❌ PROJECTION FAILURE for '{rel_path}': {projection_err}")
                metrics.record_projection_failure(rel_path, projection_err)

                failed_files.append({
                    "file": rel_path,
                    "error_class": type(projection_err).__name__,
                    "error": str(projection_err),
                    "traceback": tb_str,
                })

                if rel_path.endswith((".tsx", ".jsx")):
                    try:
                        comp_name = Path(rel_path).stem
                        placeholder_code = cls._generate_error_placeholder(rel_path, comp_name, projection_err)
                        staged_file_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(staged_file_path, "w", encoding="utf-8", newline="\n") as f:
                            f.write(placeholder_code)
                        files_written.append(rel_path)
                    except Exception:
                        pass

        # Copy existing workspace static seed to staging so we can test route wiring
        frontend_src = project_path / "Frontend"
        if not frontend_src.exists():
            frontend_src = project_path / "frontend"
        if frontend_src.exists():
            staged_frontend = staging_path / frontend_src.name
            if staged_frontend.exists():
                shutil.rmtree(staged_frontend)
            shutil.copytree(frontend_src, staged_frontend, dirs_exist_ok=True)

        backend_src = project_path / "Backend"
        if not backend_src.exists():
            backend_src = project_path / "backend"
        if backend_src.exists():
            staged_backend = staging_path / backend_src.name
            if staged_backend.exists():
                shutil.rmtree(staged_backend)
            shutil.copytree(backend_src, staged_backend, dirs_exist_ok=True)

        # ─────────────────────────────────────────────────────────────
        # S-0.7: Dynamic Route Wiring Hardening & Fatal Abort
        # ─────────────────────────────────────────────────────────────
        try:
            from app.orchestration.wiring_utils import wire_frontend_routes
            wire_frontend_routes(staging_path, graph)
        except Exception as wiring_err:
            shutil.rmtree(staging_path)
            # Record fat wiring error to failure memory immediately
            fg = FailureGeometry()
            vector = fg.encode_failure(
                node_count=total_nodes,
                error_class="WIRING_FAILURE",
                ui_node_count=ui_count
            )
            fg.insert_failure(
                failure_id=f"wiring_fail_{int(time.time())}",
                vector=vector,
                error_class="WIRING_FAILURE",
                cycle_id=project_id,
                details=f"Wiring Exception: {str(wiring_err)}",
                verification_stage="Dynamic Route Wiring"
            )
            raise ValueError(f"WIRING_FAILURE: Route wiring aborted transaction: {str(wiring_err)}")

        # ─────────────────────────────────────────────────────────────
        # Sentinel Verification Gate Checks
        # ─────────────────────────────────────────────────────────────
        verification = SentinelVerificationGate.verify(staging_path, graph)
        
        # ─────────────────────────────────────────────────────────────
        # S-0.11: Survival Metrics Reporting
        # ─────────────────────────────────────────────────────────────
        final_metrics = metrics.summary()
        final_metrics["dependency_survival"] = verification.dependency_survival
        final_metrics["schema_survival"] = verification.schema_survival
        final_metrics["state_binding_survival"] = verification.state_binding_survival
        final_metrics["build_survival"] = verification.build_survival
        final_metrics["runtime_survival"] = verification.runtime_survival
        final_metrics["visual_survival"] = verification.visual_survival
        final_metrics["topology_survival"] = verification.topology_survival

        if verification.recommendation == "REJECT":
            # Record each validation failure as FailureFingerprint to SQLite repulsion memory
            fg = FailureGeometry()
            for fail in verification.failures:
                vector = fg.encode_failure(
                    node_count=total_nodes,
                    error_class=fail.failure_type,
                    ui_node_count=ui_count
                )
                fg.insert_failure(
                    failure_id=f"verif_fail_{uuid_hex()}_{int(time.time())}",
                    vector=vector,
                    error_class=fail.failure_type,
                    cycle_id=project_id,
                    details=fail.details,
                    verification_stage=fail.stage,
                    error_field=fail.field,
                    error_file=fail.file,
                    error_component=fail.component
                )
            
            # Rollback: Clean up staged modifications safely
            shutil.rmtree(staging_path)
            raise ValueError(
                f"TRANSACTION_ROLLBACK_FAILURE: Verification Gate REJECTED the staged projection "
                f"with classification '{verification.failure_classification}'. Check sentinel_memory.db."
            )

        # ─────────────────────────────────────────────────────────────
        # Atomic Transaction Commit: Apply staged modifications to project files
        # ─────────────────────────────────────────────────────────────
        try:
            # Copy all staged files except temp directory
            for item in staging_path.iterdir():
                dest = project_path / item.name
                if item.is_dir():
                    shutil.copytree(item, dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, dest)
            
            shutil.rmtree(staging_path)
        except Exception as commit_err:
            raise RuntimeError(f"TRANSACTION_ROLLBACK_FAILURE: Atomic disk commit write error: {commit_err}")

        log("PROJECTOR", "✅ TRANSACTION COMMITTED: Staged codebase verified and merged atomically.")

        # Write final manifest
        try:
            ast_manifest_path = project_path / ".genx_ast_manifest.json"
            manifest_payload = {
                "project_id": project_id,
                "topology": graph.serialize(),
                "projections": {rel: af.integrity_hash for rel, af in ast_files.items()},
                "partial": is_partial,
                "metrics": final_metrics,
            }
            with open(ast_manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest_payload, f, indent=2)
        except Exception:
            pass

        log(
            "PROJECTOR",
            f"📊 Cycle Metrics: "
            f"dependency_survival={final_metrics['dependency_survival']*100}% "
            f"schema_survival={final_metrics['schema_survival']*100}% "
            f"state_binding_survival={final_metrics['state_binding_survival']*100}% "
            f"build_survival={final_metrics['build_survival']*100}% "
            f"runtime_survival={final_metrics['runtime_survival']*100}% "
            f"visual_survival={final_metrics['visual_survival']*100}% "
            f"topology_survival={final_metrics['topology_survival']*100}%"
        )

        return {
            "files_written": files_written,
            "files_deleted": [],
            "partial": is_partial,
            "failed_files": failed_files,
            "metrics": final_metrics,
        }


def uuid_hex() -> str:
    import uuid
    return uuid.uuid4().hex[:6]
