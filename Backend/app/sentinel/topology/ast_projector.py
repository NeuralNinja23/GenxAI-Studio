# app/topology/ast_projector.py
"""
V4 AST Projector — Stage 3: AST Pipeline

The SOLE authorized filesystem writer in the entire refactored V4 runtime.
Bypassing this projector is an absolute governance violation.

Phase 9 Upgrade: Graceful Partial Projection & Instrumentation Metrics
    - Per-file error isolation: broken UI components receive a design-compliant
      placeholder alert instead of aborting the entire projection cycle.
    - Full traceback diagnostics replace all silent exception patterns.
    - Real-time instrumentation metrics emitted to ProjectionMetrics singleton.
"""

import json
import os
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional

from app.core.logging import log
from app.sentinel.topology.ast_generator import ASTFile, ASTGenerator, ASTReactComponent, ASTImport
from app.sentinel.topology.ast_validator import ASTValidator
from app.sentinel.topology.topology_version_manager import TopologyVersionManager
from app.sentinel.topology.projection_metrics import ProjectionMetrics
from app.sentinel.failure_memory.failure_recorder import record_failure, FailureType, Severity


class ASTProjector:
    """
    Syntactic Projection Medium.
    Ensures all filesystem realities are controlled, validated, and recorded projections.

    Phase 9: Supports partial compilation — broken nodes are isolated into
    design-compliant error placeholders while healthy nodes are written to disk.
    """

    @classmethod
    def _generate_error_placeholder(cls, rel_path: str, component_name: str, error: Exception) -> str:
        """
        Generate a design-compliant React error placeholder component.

        Instead of defaulting the entire app to RootView.tsx, broken UI
        components are isolated with a clear diagnostic alert box that
        displays the error context and component name.
        """
        safe_error = str(error).replace("'", "\\'").replace('"', '\\"').replace("\n", " ")
        return (
            f"import React from 'react';\n\n"
            f"/**\n"
            f" * ⚠️ GenxAI V4 Projection Error Placeholder\n"
            f" *\n"
            f" * This component failed AST validation/projection and has been\n"
            f" * isolated to prevent cascading failures across the application.\n"
            f" *\n"
            f" * Source: {rel_path}\n"
            f" * Error:  {safe_error[:200]}\n"
            f" */\n"
            f"export default function {component_name}() {{\n"
            f"  return (\n"
            f"    <div style={{{{\n"
            f"      margin: '24px',\n"
            f"      padding: '24px',\n"
            f"      borderRadius: '12px',\n"
            f"      border: '1px solid rgba(239, 68, 68, 0.3)',\n"
            f"      background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.05), rgba(30, 30, 40, 0.95))',\n"
            f"      color: '#f1f5f9',\n"
            f"      fontFamily: 'system-ui, -apple-system, sans-serif',\n"
            f"    }}}}>\n"
            f"      <div style={{{{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}}}>\n"
            f"        <span style={{{{ fontSize: '28px' }}}}>⚠️</span>\n"
            f"        <div>\n"
            f"          <h2 style={{{{ margin: 0, fontSize: '18px', fontWeight: 700, color: '#fca5a5' }}}}>\n"
            f"            Projection Error: {component_name}\n"
            f"          </h2>\n"
            f"          <p style={{{{ margin: '4px 0 0', fontSize: '13px', color: '#94a3b8' }}}}>\n"
            f"            This component could not be compiled during the AST projection cycle.\n"
            f"          </p>\n"
            f"        </div>\n"
            f"      </div>\n"
            f"      <pre style={{{{\n"
            f"        padding: '16px',\n"
            f"        borderRadius: '8px',\n"
            f"        background: 'rgba(0,0,0,0.4)',\n"
            f"        fontSize: '12px',\n"
            f"        color: '#fbbf24',\n"
            f"        overflowX: 'auto',\n"
            f"        whiteSpace: 'pre-wrap',\n"
            f"        wordBreak: 'break-word',\n"
            f"      }}}}>\n"
            f"        {safe_error[:500]}\n"
            f"      </pre>\n"
            f"      <p style={{{{ fontSize: '11px', color: '#64748b', marginTop: '12px' }}}}>\n"
            f"        GenxAI V4 Cognitive Engine — Partial Projection Mode\n"
            f"      </p>\n"
            f"    </div>\n"
            f"  );\n"
            f"}}\n"
        )

    @classmethod
    async def project(cls, cycle_ctx) -> Dict[str, Any]:
        """
        Main kernel entry point for AST projection.

        Phase 9: Supports partial compilation. Individual file failures are
        caught, logged with full tracebacks, and replaced with error
        placeholders (for UI nodes) rather than aborting the entire cycle.
        """
        metrics = ProjectionMetrics.get_instance()
        metrics.reset()

        project_id = cycle_ctx.project_id
        project_path = Path(cycle_ctx.project_path)

        log("PROJECTOR", f"📡 Initiating AST projection cycle for project {project_id}")

        # Fetch active topology graph from MongoDB
        graph = await TopologyVersionManager.get_active_topology(project_id)
        if not graph:
            # Fallback to topology compiler from directive if not persisted yet
            # For Stage 3 tests or scaffold integration, we will handle fallback
            from app.sentinel.directives import IntentField
            intent = await IntentField.find_one({"project_id": project_id})
            if intent:
                from app.sentinel.topology.topology_compiler import TopologyCompiler
                graph = TopologyCompiler.compile_intent(project_id, intent)
                await TopologyVersionManager.commit_topology(project_id, graph, author="kernel")
            else:
                log("PROJECTOR", f"⚠️ No active topology or intent found for {project_id}. Nothing to project.")
                return {"files_written": [], "files_deleted": [], "partial": False, "metrics": metrics.summary()}

        # ── Record graph-level metrics ────────────────────────
        from app.sentinel.topology.node_types import NodeType
        total_nodes = len(graph.nodes)
        ui_count = sum(1 for n in graph.nodes.values() if n.node_type == NodeType.UI_NODE)
        metrics.set_ui_node_count(ui_count)

        # Generate structured ASTFile configurations from topology graph
        ast_files = ASTGenerator.generate(graph)

        files_written: List[str] = []
        files_deleted: List[str] = []
        failed_files: List[Dict[str, str]] = []
        is_partial = False

        # ── Per-file projection with error isolation ──────────
        for rel_path, ast_file in ast_files.items():
            metrics.record_projection_attempt(rel_path)

            # Track node-level attempts for all nodes contributing to this file
            for node_id, node in graph.nodes.items():
                comp_name = node.properties.get("component_name", "")
                entity_name = node.properties.get("entity_name", "")
                if comp_name and comp_name in rel_path:
                    metrics.record_node_attempt(node_id)
                elif entity_name and entity_name in rel_path:
                    metrics.record_node_attempt(node_id)

            full_path = project_path / rel_path

            try:
                # 1. Deterministic Validation
                val_result = ASTValidator.validate_file(ast_file)
                if not val_result.get("passed"):
                    validation_errors = val_result.get("errors", [])
                    error_detail = "; ".join(validation_errors)
                    raise ValueError(f"AST validation failure: {error_detail}")

                # Ensure parent directory exists
                full_path.parent.mkdir(parents=True, exist_ok=True)

                # Render structured ASTFile to source code
                rendered_code = ast_file.render()

                # 2. Filesystem Write (ASTProjector is the SOLE permitted writer)
                with open(full_path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(rendered_code)

                log("PROJECTOR", f"💾 Projected syntax tree to: {rel_path} (integrity={ast_file.integrity_hash[:8]})")
                files_written.append(rel_path)
                metrics.record_projection_success(rel_path)

                # Record node-level successes
                for node_id, node in graph.nodes.items():
                    comp_name = node.properties.get("component_name", "")
                    entity_name = node.properties.get("entity_name", "")
                    if comp_name and comp_name in rel_path:
                        metrics.record_node_success(node_id)
                    elif entity_name and entity_name in rel_path:
                        metrics.record_node_success(node_id)

            except Exception as projection_err:
                # ── Phase 9: Graceful partial compile ─────────
                is_partial = True
                tb_str = traceback.format_exc()

                log(
                    "PROJECTOR",
                    f"❌ PROJECTION FAILURE for '{rel_path}': "
                    f"{type(projection_err).__name__}: {projection_err}\n"
                    f"{'─' * 50}\n{tb_str}{'─' * 50}"
                )

                metrics.record_projection_failure(rel_path, projection_err)

                # ── Phase 6A: Record to failure memory ────────
                api_count = sum(1 for n in graph.nodes.values() if n.node_type.value == "API_NODE")
                record_failure(
                    FailureType.AST_FAILURE,
                    Severity.ERROR,
                    f"{type(projection_err).__name__}: {str(projection_err)[:200]}",
                    project_id=project_id,
                    component=rel_path,
                    node_type=type(projection_err).__name__,
                    tb=tb_str,
                    ui_nodes=ui_count,
                    api_nodes=api_count,
                )

                failed_files.append({
                    "file": rel_path,
                    "error_class": type(projection_err).__name__,
                    "error": str(projection_err),
                    "traceback": tb_str,
                })

                # If this is a UI component (.tsx), write an error placeholder
                # instead of leaving the file missing entirely
                if rel_path.endswith((".tsx", ".jsx")):
                    try:
                        # Extract component name from path
                        comp_name = Path(rel_path).stem
                        placeholder_code = cls._generate_error_placeholder(
                            rel_path, comp_name, projection_err
                        )
                        full_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(full_path, "w", encoding="utf-8", newline="\n") as f:
                            f.write(placeholder_code)

                        log(
                            "PROJECTOR",
                            f"🔶 Wrote error placeholder for: {rel_path} "
                            f"(component isolated, not suppressed)"
                        )
                        files_written.append(rel_path)
                    except Exception as placeholder_err:
                        log(
                            "PROJECTOR",
                            f"⛔ Failed to write placeholder for '{rel_path}': "
                            f"{type(placeholder_err).__name__}: {placeholder_err}\n"
                            f"{traceback.format_exc()}"
                        )

        # ── Log partial projection summary if any failures ────
        if is_partial:
            log(
                "PROJECTOR",
                f"🔶 PARTIAL PROJECTION: {len(files_written)}/{len(ast_files)} files written, "
                f"{len(failed_files)} failed. "
                f"Failed files: {[f['file'] for f in failed_files]}"
            )
        else:
            log(
                "PROJECTOR",
                f"✅ FULL PROJECTION: All {len(files_written)} files written successfully."
            )

        # ── Dynamically wire new UI component routes in App.jsx ──
        try:
            from app.orchestration.wiring_utils import wire_frontend_routes
            wire_frontend_routes(project_path, graph)
        except Exception as wiring_err:
            tb_str = traceback.format_exc()
            log(
                "PROJECTOR",
                f"⚠️ Failed to wire frontend routes: "
                f"{type(wiring_err).__name__}: {wiring_err}\n"
                f"{'─' * 50}\n{tb_str}{'─' * 50}"
            )

        # Write AST Manifest (.genx_ast_manifest.json) to secure the projection boundary
        try:
            ast_manifest_path = project_path / ".genx_ast_manifest.json"
            manifest_payload = {
                "project_id": project_id,
                "topology": graph.serialize(),
                "projections": {rel: af.integrity_hash for rel, af in ast_files.items()},
                "partial": is_partial,
                "metrics": metrics.summary(),
            }

            with open(ast_manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest_payload, f, indent=2)
        except Exception as manifest_err:
            log(
                "PROJECTOR",
                f"⚠️ Failed to write AST manifest: "
                f"{type(manifest_err).__name__}: {manifest_err}\n"
                f"{traceback.format_exc()}"
            )

        # ── Emit final metrics summary ────────────────────────
        final_metrics = metrics.summary()
        log(
            "PROJECTOR",
            f"📊 Cycle Metrics: "
            f"node_survival={final_metrics['node_survival_rate']}% "
            f"proj_survival={final_metrics['projection_survival_rate']}% "
            f"ui_nodes={final_metrics['ui_node_count']} "
            f"dropped={final_metrics['dropped_nodes']}"
        )

        return {
            "files_written": files_written,
            "files_deleted": files_deleted,
            "partial": is_partial,
            "failed_files": failed_files,
            "metrics": final_metrics,
        }

