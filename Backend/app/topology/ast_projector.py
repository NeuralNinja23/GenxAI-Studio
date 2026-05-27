# app/topology/ast_projector.py
"""
V4 AST Projector — Stage 3: AST Pipeline

The SOLE authorized filesystem writer in the entire refactored V4 runtime.
Bypassing this projector is an absolute governance violation.
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional

from app.core.logging import log
from app.topology.ast_generator import ASTFile, ASTGenerator
from app.topology.ast_validator import ASTValidator
from app.topology.topology_version_manager import TopologyVersionManager

class ASTProjector:
    """
    Syntactic Projection Medium.
    Ensures all filesystem realities are controlled, validated, and recorded projections.
    """

    @classmethod
    async def project(cls, cycle_ctx) -> Dict[str, Any]:
        """
        Main kernel entry point for AST projection.
        Takes ProjectionCycleContext, reads topology, compiles ASTFiles,
        validates them, and projects them to the sandbox filesystem.
        """
        project_id = cycle_ctx.project_id
        project_path = Path(cycle_ctx.project_path)

        log("PROJECTOR", f"📡 Initiating AST projection cycle for project {project_id}")

        # Fetch active topology graph from MongoDB
        graph = await TopologyVersionManager.get_active_topology(project_id)
        if not graph:
            # Fallback to topology compiler from directive if not persisted yet
            # For Stage 3 tests or scaffold integration, we will handle fallback
            from app.models.directive import IntentField
            intent = await IntentField.find_one({"project_id": project_id})
            if intent:
                from app.topology.topology_compiler import TopologyCompiler
                graph = TopologyCompiler.compile_intent(project_id, intent)
                await TopologyVersionManager.commit_topology(project_id, graph, author="kernel")
            else:
                log("PROJECTOR", f"⚠️ No active topology or intent found for {project_id}. Nothing to project.")
                return {"files_written": [], "files_deleted": []}

        # Generate structured ASTFile configurations from topology graph
        ast_files = ASTGenerator.generate(graph)
        
        files_written = []
        files_deleted = []

        # Project files to filesystem
        for rel_path, ast_file in ast_files.items():
            full_path = project_path / rel_path
            
            # 1. Deterministic Validation
            val_result = ASTValidator.validate_file(ast_file)
            if not val_result.get("passed"):
                raise ValueError(f"AST validation failure for '{rel_path}': {val_result.get('errors')}")

            # Ensure parent directory exists
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Render structured ASTFile to source code
            rendered_code = ast_file.render()

            # 2. Filesystem Write (ASTProjector is the SOLE permitted writer)
            with open(full_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(rendered_code)

            log("PROJECTOR", f"💾 Projected syntax tree to: {rel_path} (integrity={ast_file.integrity_hash[:8]})")
            files_written.append(rel_path)

        # Write AST Manifest (.genx_ast_manifest.json) to secure the projection boundary
        ast_manifest_path = project_path / ".genx_ast_manifest.json"
        manifest_payload = {
            "project_id": project_id,
            "topology": graph.serialize(),
            "projections": {rel: af.integrity_hash for rel, af in ast_files.items()}
        }
        
        import json
        with open(ast_manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_payload, f, indent=2)

        return {
            "files_written": files_written,
            "files_deleted": files_deleted
        }
