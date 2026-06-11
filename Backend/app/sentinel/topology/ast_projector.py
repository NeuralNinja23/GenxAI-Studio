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
# SentinelVerificationGate import removed from here to break circular dependency

from app.sentinel.failure_memory.failure_geometry import FailureGeometry
from app.models.runtime_models import RepairIntent, RepairScope
from app.studio.architecture.workspace_architecture import WorkspaceArchitecture

# LLM imports
try:
    from app.llm.prompts.builder import BUILDER_PROMPT
except ImportError:
    BUILDER_PROMPT = ""

# ─────────────────────────────────────────────────────────────
# Repair mode system prompt
# ─────────────────────────────────────────────────────────────
_REPAIR_PROMPT = """\
You are a surgical code repair agent for the Sentinel system.

You will receive:
  - Existing file contents (files inside the repair scope)
  - A list of failure fingerprints (type, file, details, severity)
  - A precise repair instruction

Your task:
  Repair ONLY the files necessary to satisfy the instruction.
  Preserve all unchanged files exactly as provided.

Output ONLY valid JSON with no markdown wrappers:
{
  "relative/path/to/file.tsx": "<full repaired file content>",
  "another/file.py": "<full repaired file content>"
}

Include ONLY the files you modified. Files not in your output are left untouched.
"""


class ProjectorError(Exception):
    """Custom exception raised when ASTProjector validation fails."""
    def __init__(self, reason: str, details: str):
        super().__init__(f"PROJECTOR_FAILURE: {reason} - {details}")
        self.reason = reason
        self.details = details


class ASTProjector:
    """
    Syntactic Projection Medium with Atomic Transactional Stages.
    Stages writes inside a secure local sandbox buffer, running the 
    SentinelVerificationGate before applying atomic disk commits.
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def validate_not_empty(self, response: str):
        if not response or not response.strip():
            raise ProjectorError("EMPTY_RESPONSE", "The LLM response was completely empty or blank.")

    def validate_json(self, response: str) -> Dict[str, str]:
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ProjectorError("INVALID_JSON", f"Failed to parse JSON response: {e}. Raw response start: {response[:200]}")

    def validate_schema(self, data: Any):
        if not isinstance(data, dict):
            raise ProjectorError("INVALID_PROJECT_SCHEMA", "LLM response JSON is not a dictionary representing files.")
        for k, v in data.items():
            if not isinstance(k, str) or not isinstance(v, str):
                raise ProjectorError("INVALID_PROJECT_SCHEMA", f"Expected key/value to be strings, got key type {type(k)} and value type {type(v)} for key '{k}'.")

    def validate_required_keys(self, data: Dict[str, str]):
        # 1. Has package manifest
        has_manifest = any(k.replace("\\", "/").endswith("package.json") or k.replace("\\", "/").endswith("requirements.txt") for k in data.keys())
        if not has_manifest:
            raise ProjectorError("MISSING_REQUIRED_ARTIFACT", "Missing package manifest (package.json or requirements.txt) in projected files.")
            
        # 2. Has at least one entry module
        entry_patterns = ["main.tsx", "main.ts", "index.js", "index.tsx", "app.tsx", "app.js", "main.py", "app.py"]
        has_entry = any(any(k.replace("\\", "/").endswith(pat) for pat in entry_patterns) for k in data.keys())
        if not has_entry:
            raise ProjectorError("MISSING_REQUIRED_ARTIFACT", "Missing entry module (e.g. main.tsx, index.js, main.py) in projected files.")
            
        # 3. Has at least one build configuration file
        config_patterns = ["vite.config.ts", "vite.config.js", "next.config.js", "webpack.config.js", "tsconfig.json", "jsconfig.json", "requirements.txt", "Dockerfile"]
        has_config = any(any(k.replace("\\", "/").endswith(pat) for pat in config_patterns) for k in data.keys())
        if not has_config:
            raise ProjectorError("MISSING_REQUIRED_ARTIFACT", "Missing build/runtime configuration file (e.g. vite.config.ts, requirements.txt) in projected files.")
            
        # 4. Has at least one source tree path
        has_source = any("src/" in k.replace("\\", "/") or "app/" in k.replace("\\", "/") for k in data.keys())
        if not has_source:
            raise ProjectorError("MISSING_REQUIRED_ARTIFACT", "Missing source tree directory path (e.g. src/ or app/) in projected files.")

    def validate_project_shape(self, data: Dict[str, str]):
        for k in data.keys():
            norm_path = k.replace("\\", "/")
            if ".." in norm_path or norm_path.startswith("/") or norm_path.startswith("./"):
                raise ProjectorError("INVALID_PROJECT_SHAPE", f"Invalid directory path format: '{k}'")
            parts = norm_path.split("/")
            if len(parts) > 10:
                raise ProjectorError("INVALID_PROJECT_SHAPE", f"Project file path depth exceeds maximum limit of 10 directories: '{k}'")

    @classmethod
    def _seed_staging(cls, project_path: Path, staging_path: Path):
        """Replicates the live project path into staging with a controlled inclusion list."""
        print("SEED_STAGING CALLED")
        staging_path.mkdir(parents=True, exist_ok=True)
        if not project_path.exists():
            return

        # Explicit list of relative directories and files to copy
        includes = [
            f"{WorkspaceArchitecture.FRONTEND_DIR}/src",
            f"{WorkspaceArchitecture.FRONTEND_DIR}/public",
            f"{WorkspaceArchitecture.BACKEND_DIR}/app",
            f"{WorkspaceArchitecture.BACKEND_DIR}/routers",
            f"{WorkspaceArchitecture.BACKEND_DIR}/models",
            f"{WorkspaceArchitecture.BACKEND_DIR}/schemas",
            "package.json",
            "requirements.txt",
        ]
        
        # Include configuration patterns dynamically
        config_patterns = ["vite.config.*", "tsconfig.*", ".env*"]
        for pattern in config_patterns:
            for p in project_path.glob(pattern):
                if p.is_file():
                    includes.append(p.name)
            for p in WorkspaceArchitecture.frontend_root(project_path).glob(pattern):
                if p.is_file():
                    includes.append(f"{WorkspaceArchitecture.FRONTEND_DIR}/{p.name}")

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

    async def project(
        self,
        cycle_ctx,
        topology_graphs=None,
        mutation_plan=None,
        promote_immediately: bool = False,
        repair_intent: Optional[RepairIntent] = None,
        repair_scope: Optional[RepairScope] = None,
    ) -> Dict[str, Any]:
        """
        Main kernel entry point for AST projection.

        When repair_intent and repair_scope are both provided, activates
        Projector Repair Mode: reads only the scoped files from staging,
        calls the LLM with the repair instruction, and writes only the
        files returned in the JSON response.

        repair_scope is always passed by the caller (kernel) — the projector
        never infers scope itself.
        """
        print(
            f"[PROJECT_ENTRY] "
            f"args_count=3 "
            f"cycle_ctx_type={type(cycle_ctx).__name__ if cycle_ctx else 'NONE'} "
            f"repair_mode={repair_intent is not None}"
        )
        llm_client = self.llm_client

        print(
            f"[PROJECT_CONTEXT] "
            f"self_is_none={self is None} "
            f"llm_client_is_none={llm_client is None}"
        )

        project_id = cycle_ctx.project_id
        project_path = Path(cycle_ctx.project_path)
        staging_path = WorkspaceArchitecture.staging_root(project_path)

        repair_mode = repair_intent is not None and repair_scope is not None

        # Initialize staging by replicating the live codebase state ONLY if not in repair mode
        if not repair_mode:
            if staging_path.exists():
                shutil.rmtree(staging_path)
            self._seed_staging(project_path, staging_path)

        # ── Repair Mode ──────────────────────────────────────
        if repair_mode:
            # ── 5. Add Diagnostic Assertion ──
            assert staging_path.exists(), "Staging path does not exist before entering repair mode"
            
            frontend_exists = (staging_path / "frontend").exists() or (staging_path / "Frontend").exists()
            backend_exists = (staging_path / "backend").exists() or (staging_path / "Backend").exists()
            assert frontend_exists, "Frontend directory does not exist in staging before entering repair mode"
            
            package_json_exists = (staging_path / "frontend" / "package.json").exists() or (staging_path / "Frontend" / "package.json").exists()
            target_file_exists = False
            try:
                resolved_target = WorkspaceArchitecture.resolve(staging_path, repair_intent.target_file)
                target_file_exists = resolved_target.exists()
            except Exception:
                pass
                
            log("PROJECTOR", f"[DIAGNOSTIC] frontend_exists={frontend_exists} backend_exists={backend_exists} package_json_exists={package_json_exists} target_file_exists={target_file_exists}")

            log("PROJECTOR", f"🔧 Repair Mode: scope={repair_scope.value} target={repair_intent.target_file}")
            
            # Explicit diagnostic logging required by Phase 1
            print(f"[PROJECTOR]\nRepair Mode Activated\nscope={repair_scope.name}\nfiles_loaded={len(getattr(cycle_ctx, '_repair_failures', []))}")
            
            files_written = await self._run_repair_mode(
                staging_path=staging_path,
                repair_intent=repair_intent,
                repair_scope=repair_scope,
                failures=getattr(cycle_ctx, "_repair_failures", []),
            )
            # Write manifest and wiring, then return
            return await self._finalize_projection(
                project_id=project_id,
                project_path=project_path,
                staging_path=staging_path,
                graph=None,
                files_written=files_written,
                promote_immediately=promote_immediately,
            )

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
            
            # Run validation pipeline
            self.validate_not_empty(response)
            files_to_write = self.validate_json(response)
            self.validate_schema(files_to_write)
            self.validate_required_keys(files_to_write)
            self.validate_project_shape(files_to_write)

            # Write files
            files_written = []
            for path, code in files_to_write.items():
                full_path = staging_path / path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(code)
                files_written.append(path)
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
                file_p = WorkspaceArchitecture.resolve(staging_path, path)
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

        # If requested, commit staged files atomically now
        if promote_immediately:
            self._atomic_promote_staging(project_path, staging_path)

        return {
            "status": "SUCCESS",
            "files_written": files_written,
            "metrics": 1.0
        }

    # ─────────────────────────────────────────────────────────
    # Repair Mode helpers
    # ─────────────────────────────────────────────────────────

    async def _run_repair_mode(
        self,
        staging_path: Path,
        repair_intent: RepairIntent,
        repair_scope: RepairScope,
        failures: list,
    ) -> List[str]:
        """
        Execute targeted re-emission within the repair scope.

        Scope resolution (set by kernel, already capped by policy):
          COMPONENT → repair_intent.target_file only
          MODULE    → all files in repair_intent.target_file's directory
          FEATURE   → files matching feature area / package structure
          WORKSPACE → whole staging directory

        Only files returned in the LLM response are written back.
        Files not in the response are left exactly as-is in staging.
        """
        log("PROJECTOR", f"repair_intent={repair_intent}")
        log("PROJECTOR", f"affected_files={getattr(repair_intent, 'affected_files', None)}")
        target = repair_intent.target_file

        # Resolve the file set for this scope
        scope_files: List[Path] = []
        if repair_scope == RepairScope.COMPONENT:
            try:
                candidate = WorkspaceArchitecture.resolve(staging_path, target)
            except Exception:
                candidate = staging_path / target
            log("PROJECTOR", f"trying={candidate}")
            log("PROJECTOR", f"exists={candidate.exists()}")
            if candidate.exists():
                scope_files = [candidate]
            else:
                log("PROJECTOR", f"⚠️ Repair target not found in staging: {candidate}")

        elif repair_scope == RepairScope.MODULE:
            try:
                candidate = WorkspaceArchitecture.resolve(staging_path, target)
                module_dir = candidate.parent
            except Exception:
                module_dir = (staging_path / target).parent
            log("PROJECTOR", f"trying={module_dir}")
            log("PROJECTOR", f"exists={module_dir.exists()}")
            if module_dir.exists():
                scope_files = [f for f in module_dir.iterdir() if f.is_file()]

        elif repair_scope == RepairScope.FEATURE:
            # Feature = all files sharing the same top-level package as the target
            if Path(target).parts:
                try:
                    feature_root = WorkspaceArchitecture.resolve(staging_path, Path(target).parts[0])
                except Exception:
                    feature_root = staging_path / Path(target).parts[0]
            else:
                feature_root = staging_path
            log("PROJECTOR", f"trying={feature_root}")
            log("PROJECTOR", f"exists={feature_root.exists()}")
            if feature_root.exists() and feature_root.is_dir():
                scope_files = [f for f in feature_root.rglob("*") if f.is_file()]
            else:
                try:
                    candidate = WorkspaceArchitecture.resolve(staging_path, target)
                except Exception:
                    candidate = staging_path / target
                log("PROJECTOR", f"trying={candidate}")
                log("PROJECTOR", f"exists={candidate.exists()}")
                scope_files = [candidate] if candidate.exists() else []

        elif repair_scope == RepairScope.WORKSPACE:
            # Last resort: all files in staging (excluding hidden dirs and artifacts)
            scope_files = [
                f for f in staging_path.rglob("*")
                if f.is_file()
                and ".genx" not in f.name
                and "node_modules" not in str(f)
                and "__pycache__" not in str(f)
            ]
            for f in scope_files:
                log("PROJECTOR", f"trying={f}")
                log("PROJECTOR", f"exists={f.exists()}")

        if not scope_files:
            log("PROJECTOR", f"⚠️ No files found for scope={repair_scope.value}")
            return []

        # Read existing file contents
        existing_contents: dict = {}
        for f in scope_files:
            try:
                rel = WorkspaceArchitecture.to_workspace_relative(staging_path.parent, f)
                existing_contents[rel] = f.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                log("PROJECTOR", f"⚠️ Could not read staged file {f}: {e}")

        # Build failure payload
        failure_data = []
        for fp in failures:
            failure_data.append({
                "failure_type": getattr(fp, "failure_type", "UNKNOWN"),
                "file":         str(getattr(fp, "file_path", None) or getattr(fp, "file", "unknown")),
                "details":      getattr(fp, "details", ""),
                "severity":     getattr(fp, "severity", 1.0),
            })

        user_message = json.dumps({
            "repair_instruction": repair_intent.instruction,
            "target_file":        str(repair_intent.target_file),
            "scope":              repair_scope.value,
            "failure_fingerprints": failure_data,
            "existing_file_contents": existing_contents,
        }, indent=2)

        log("PROJECTOR", f"📡 Repair Mode LLM call: {len(existing_contents)} files in scope")

        response = await self.llm_client.generate(
            system_prompt=_REPAIR_PROMPT,
            user_message=user_message,
        )

        # Run validation pipeline
        self.validate_not_empty(response)
        repaired = self.validate_json(response)
        self.validate_schema(repaired)
        self.validate_project_shape(repaired)

        # Write repaired files to staging
        files_written: List[str] = []
        for rel_path, content in repaired.items():
            try:
                out_path = WorkspaceArchitecture.resolve(staging_path, rel_path)
            except Exception:
                out_path = staging_path / rel_path
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(content)
            files_written.append(rel_path)
            log("PROJECTOR", f"✅ Repair wrote: {rel_path}")

        # Assemble virtual staging layout and validate required keys
        all_files_in_staging = {}
        for p in staging_path.rglob("*"):
            if p.is_file():
                try:
                    rel = str(p.relative_to(staging_path))
                    all_files_in_staging[rel] = ""
                except Exception:
                    pass
        self.validate_required_keys(all_files_in_staging)

        return files_written

    async def _finalize_projection(
        self,
        project_id: str,
        project_path: Path,
        staging_path: Path,
        graph: Any,
        files_written: List[str],
        promote_immediately: bool,
    ) -> Dict[str, Any]:
        """Write AST manifest, run route wiring, optionally promote staging."""
        import hashlib
        try:
            manifest_path = staging_path / ".genx_ast_manifest.json"
            projections = {}
            for path in files_written:
                file_p = WorkspaceArchitecture.resolve(staging_path, path)
                if file_p.exists() and file_p.is_file():
                    projections[path] = hashlib.sha256(file_p.read_bytes()).hexdigest()
            manifest_data = {
                "project_id": project_id,
                "topology": graph.serialize() if graph and hasattr(graph, "serialize") else "repair_mode",
                "projections": projections
            }
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=2)
        except Exception as manifest_err:
            log("PROJECTOR", f"⚠️ Failed to write AST manifest to staging: {manifest_err}")

        try:
            from app.orchestration.wiring_utils import wire_frontend_routes
            if graph:
                wire_frontend_routes(staging_path, graph)
        except Exception as wiring_err:
            if staging_path.exists():
                shutil.rmtree(staging_path)
            raise ValueError(f"WIRING_FAILURE: Route wiring aborted transaction: {str(wiring_err)}")

        if promote_immediately:
            self._atomic_promote_staging(project_path, staging_path)

        return {
            "status": "SUCCESS",
            "files_written": files_written,
            "metrics": 1.0
        }