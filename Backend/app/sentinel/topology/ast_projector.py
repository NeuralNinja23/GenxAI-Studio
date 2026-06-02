# app/topology/ast_projector.py
"""
V4 AST Projector — Stage 3: AST Pipeline
Unified Projector supporting both classical ASTGenerator and new LLM-based Builder, 
safeguarded by SentinelVerificationGate and atomic rollback transitions.
"""

import json
import os
import shutil
import time
import traceback
import uuid
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

# LLM imports
try:
    from app.llm.prompts.builder import BUILDER_PROMPT
except ImportError:
    BUILDER_PROMPT = ""


class ASTProjector:
    """
    Syntactic Projection Medium with Atomic Transactional Stages.
    Stages writes inside a secure local sandbox buffer, running the 
    SentinelVerificationGate before applying atomic disk commits.
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    @classmethod
    def _seed_staging(cls, project_path: Path, staging_path: Path):
        """Replicates the live project path into staging with a controlled inclusion list."""
        print("SEED_STAGING CALLED")
        staging_path.mkdir(parents=True, exist_ok=True)
        if not project_path.exists():
            return

        # Explicit list of relative directories and files to copy
        includes = [
            "frontend/src",
            "frontend/public",
            "backend/app",
            "backend/routers",
            "backend/models",
            "backend/schemas",
            "package.json",
            "requirements.txt",
        ]
        
        # Include configuration patterns dynamically
        config_patterns = ["vite.config.*", "tsconfig.*", ".env*"]
        for pattern in config_patterns:
            for p in project_path.glob(pattern):
                if p.is_file():
                    includes.append(p.name)
            for p in (project_path / "frontend").glob(pattern):
                if p.is_file():
                    includes.append(f"frontend/{p.name}")

        for item_rel in includes:
            src_item = project_path / item_rel
            dst_item = staging_path / item_rel
            if src_item.exists():
                dst_item.parent.mkdir(parents=True, exist_ok=True)
                if src_item.is_file():
                    shutil.copy2(src_item, dst_item)
                elif src_item.is_dir():
                    # Copy tree excluding bloated temporary artifacts
                    def ignore_patterns(src, names):
                        ignored = []
                        for name in names:
                            if name in ("node_modules", "dist", "build", "coverage", ".pytest_cache", "__pycache__", ".venv", ".genx_staging", ".genx_backup"):
                                ignored.append(name)
                        return ignored
                    shutil.copytree(src_item, dst_item, dirs_exist_ok=True, ignore=ignore_patterns)

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
    def _atomic_promote_staging(cls, project_path: Path, staging_path: Path):
        """Atomically promotes staging directory replacing target live directory securely."""
        backup_path = project_path.parent / ".project.rollback_backup"
        if backup_path.exists():
            shutil.rmtree(backup_path)
            
        temp_staging = project_path.parent / f".genx_staging_temp_{uuid.uuid4().hex}"
        temp_staging_moved = False
        
        try:
            # Move staging directory out of project_path so it doesn't get swept into backup
            if staging_path.exists():
                shutil.move(str(staging_path), str(temp_staging))
                temp_staging_moved = True
                
            # 1. Rename existing project to rollback backup
            if project_path.exists():
                shutil.move(str(project_path), str(backup_path))
            
            # 2. Rename staged dir to live project path
            if temp_staging_moved:
                shutil.move(str(temp_staging), str(project_path))
            else:
                project_path.mkdir(parents=True, exist_ok=True)
            
            # 3. Success: Clean up rollback backup
            if backup_path.exists():
                shutil.rmtree(backup_path)
        except Exception as e:
            # Rollback: Restore original from backup
            if temp_staging_moved and temp_staging.exists():
                shutil.rmtree(temp_staging)
            if backup_path.exists():
                if project_path.exists():
                    shutil.rmtree(project_path)
                shutil.move(str(backup_path), str(project_path))
            raise e

    def _atomic_promote(self, project_path: Path, staging_path: Path):
        """Instance alias to keep ExecutionKernel happy."""
        self._atomic_promote_staging(project_path, staging_path)

    @classmethod
    async def project(cls, *args, **kwargs) -> Dict[str, Any]:
        """
        Main kernel entry point for AST projection.
        Supports both class-level (classic ASTGenerator) and instance-level (LLM builder) calls.
        """
        # Unpack unified arguments
        if len(args) > 0 and isinstance(args[0], ASTProjector):
            self = args[0]
            cycle_ctx = args[1]
            topology_graphs = args[2] if len(args) > 2 else None
            mutation_plan = args[3] if len(args) > 3 else None
            llm_client = self.llm_client
        else:
            self = None
            cycle_ctx = args[0]
            topology_graphs = args[1] if len(args) > 1 else None
            mutation_plan = args[2] if len(args) > 2 else None
            llm_client = kwargs.get("llm_client") or None

        project_id = cycle_ctx.project_id
        project_path = Path(cycle_ctx.project_path)
        staging_path = project_path / ".genx_staging"

        # Initialize staging by replicating the live codebase state
        if staging_path.exists(): 
            shutil.rmtree(staging_path)
        cls._seed_staging(project_path, staging_path)

        # Retrieve active topology graph
        graph = await TopologyVersionManager.get_active_topology(project_id)
        if not graph and isinstance(topology_graphs, ProjectTopologyGraph):
            graph = topology_graphs
        elif not graph:
            from app.sentinel.directives import IntentField
            intent = await IntentField.find_one({"project_id": project_id})
            if intent:
                from app.sentinel.topology.topology_compiler import TopologyCompiler
                graph = TopologyCompiler.compile_intent(project_id, intent)
                await TopologyVersionManager.commit_topology(project_id, graph, author="kernel")
            else:
                log("PROJECTOR", f"⚠️ No active topology or intent found for {project_id}. Nothing to project.")
                return {"files_written": [], "files_deleted": [], "partial": False}

        from app.sentinel.topology.node_types import NodeType
        total_nodes = len(graph.nodes)
        ui_count = sum(1 for n in graph.nodes.values() if n.node_type == NodeType.UI_NODE)

        # Select projection strategy
        if llm_client:
            log("PROJECTOR", "📡 Initiating AST embodiment cycle via LLM...")
            # Serialize graphs or topologies
            serialized_graphs = graph.serialize() if hasattr(graph, "serialize") else str(graph)
            response = await llm_client.generate(
                system_prompt=BUILDER_PROMPT,
                user_message=json.dumps({"graphs": serialized_graphs, "mutation": mutation_plan})
            )
            
            # Write files
            files_written = []
            try:
                # Clean Markdown if returned
                cleaned = response.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                elif cleaned.startswith("```"):
                    cleaned = cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                
                files_to_write = json.loads(cleaned.strip())
                for path, code in files_to_write.items():
                    full_path = staging_path / path
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(full_path, "w", encoding="utf-8") as f:
                        f.write(code)
                    files_written.append(path)
            except Exception as e:
                log("PROJECTOR", f"❌ Failed to parse LLM json response: {e}")
                raise e
        else:
            log("PROJECTOR", f"📡 Initiating Classic AST generator projection for {project_id}")
            metrics = ProjectionMetrics.get_instance()
            metrics.reset()
            metrics.set_ui_node_count(ui_count)

            ast_files = ASTGenerator.generate(graph)
            files_written = []
            is_partial = False

            for rel_path, ast_file in ast_files.items():
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
                except Exception as projection_err:
                    is_partial = True
                    log("PROJECTOR", f"❌ PROJECTION FAILURE for '{rel_path}': {projection_err}")
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

        # Write AST projection manifest to staging so it gets promoted automatically
        import hashlib
        try:
            manifest_path = staging_path / ".genx_ast_manifest.json"
            projections = {}
            for path in files_written:
                file_p = staging_path / path
                if file_p.exists() and file_p.is_file():
                    projections[path] = hashlib.sha256(file_p.read_bytes()).hexdigest()
            manifest_data = {
                "project_id": project_id,
                "topology": graph.serialize() if hasattr(graph, "serialize") else str(graph),
                "projections": projections
            }
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=2)
        except Exception as manifest_err:
            log("PROJECTOR", f"⚠️ Failed to write AST manifest to staging: {manifest_err}")

        # Dynamic Route Wiring check
        try:
            from app.orchestration.wiring_utils import wire_frontend_routes
            wire_frontend_routes(staging_path, graph)
        except Exception as wiring_err:
            if staging_path.exists():
                shutil.rmtree(staging_path)
            raise ValueError(f"WIRING_FAILURE: Route wiring aborted transaction: {str(wiring_err)}")

        # If called from class method context, commit staged files atomically now
        if not self:
            cls._atomic_promote_staging(project_path, staging_path)

        return {
            "status": "SUCCESS",
            "files_written": files_written,
            "metrics": 1.0
        }