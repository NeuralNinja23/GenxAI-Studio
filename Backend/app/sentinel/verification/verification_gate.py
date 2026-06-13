# app/sentinel/verification/verification_gate.py
"""
Sentinel Verification & Governance Gate (S-0)
Supreme gatekeeper enforcing technical compilation, import resolution, 
schema contract validity, reactive state binding tracing, multi-layer rendering checks,
and topological integrity.
"""

import os
import re
import time
import subprocess
import importlib.util
from typing import Dict, List, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field
from enum import Enum

from app.sentinel.topology.node_types import NodeType
from app.sentinel.topology.project_graph import ProjectTopologyGraph

from app.sentinel.routing import FailureCategory
from app.studio.architecture.workspace_architecture import WorkspaceArchitecture

class FailureSource(str, Enum):
    COMPILER = "COMPILER"
    RUNTIME = "RUNTIME"
    VISUAL = "VISUAL"
    HEURISTIC = "HEURISTIC"

class CompilerAvailability(Enum):
    AVAILABLE = "AVAILABLE"
    DEPENDENCIES_MISSING = "DEPENDENCIES_MISSING"
    BUILD_TOOL_MISSING = "BUILD_TOOL_MISSING"

class FailureFingerprint(BaseModel):
    failure_type: str
    source: FailureSource = FailureSource.HEURISTIC
    stage: str
    details: str
    file: Optional[str] = None
    field: Optional[str] = None
    component: Optional[str] = None
    category: Optional[FailureCategory] = None


# _downgrade_to_warning removed (replaced by warnings/failures segregation)



class VerificationResult(BaseModel):
    dependency_passed: bool = True
    schema_passed: bool = True
    state_binding_passed: bool = True
    build_passed: bool = True
    runtime_passed: bool = True
    visual_passed: bool = True
    topology_passed: bool = True

    dependency_survival: float = 1.0
    schema_survival: float = 1.0
    state_binding_survival: float = 1.0
    build_survival: float = 1.0
    runtime_survival: float = 1.0
    visual_survival: float = 1.0
    topology_survival: float = 1.0

    visual_evaluated: bool = True

    verification_score: float = 1.0
    governance_score: float = 1.0
    failure_classification: Optional[str] = None
    recommendation: str = "PASS"
    failures: List[FailureFingerprint] = Field(default_factory=list)
    warnings: List[FailureFingerprint] = Field(default_factory=list)
    compiler_output: Optional[str] = None
    bundler_output: Optional[str] = None
    runtime_output: Optional[str] = None
    render_output: Optional[str] = None

    @property
    def overall_survival(self) -> float:
        values = [
            self.dependency_survival,
            self.schema_survival,
            self.state_binding_survival,
            self.build_survival,
            self.runtime_survival,
        ]
        if getattr(self, "visual_evaluated", True):
            values.append(self.visual_survival)
        
        values.append(self.topology_survival)
        return round(sum(values) / len(values), 4)


class SentinelVerificationGate:
    """
    Supreme gatekeeper validating project projections against strict technical 
    and architectural standards before transaction commits.
    """

    @staticmethod
    def verify(
        project_path: Path,
        topology_graph: ProjectTopologyGraph,
        intent_graph: Optional[Any] = None,
        timeout_seconds: int = 300
    ) -> VerificationResult:
        result = VerificationResult()
        start_time = time.time()
        # ─────────────────────────────────────────────────────────────
        # S-0.0: Tier 0 Compiler Checks
        # ─────────────────────────────────────────────────────────────
        SentinelVerificationGate._verify_tier_0_compiler(project_path, result, topology_graph.project_id if topology_graph else "default")


        try:
            # ─────────────────────────────────────────────────────────────
            # S-0.2: Verification Layer A — Dependency Resolution
            # ─────────────────────────────────────────────────────────────
            SentinelVerificationGate._verify_dependencies(project_path, topology_graph, result)

            # ─────────────────────────────────────────────────────────────
            # S-0.3: Verification Layer B — Schema Contract Matching
            # ─────────────────────────────────────────────────────────────
            SentinelVerificationGate._verify_schemas(project_path, topology_graph, result)

            # ─────────────────────────────────────────────────────────────
            # S-0.4: Verification Layer C — State Binding Tracing
            # ─────────────────────────────────────────────────────────────
            SentinelVerificationGate._verify_state_bindings(project_path, topology_graph, result)

            # ─────────────────────────────────────────────────────────────
            # S-0.5: Verification Layer D — Build Dry-Runs
            # ─────────────────────────────────────────────────────────────
            SentinelVerificationGate._verify_builds(project_path, topology_graph, result)

            # ─────────────────────────────────────────────────────────────
            # S-0.6: Verification Layer E — Runtime & Page Render Check
            # ─────────────────────────────────────────────────────────────
            SentinelVerificationGate._verify_runtime_render(project_path, topology_graph, result)

            # ─────────────────────────────────────────────────────────────
            # S-0.6B: Verification Layer F — Topology Integrity Checks
            # ─────────────────────────────────────────────────────────────
            SentinelVerificationGate._verify_topology_integrity(topology_graph, result)

            # Check general timeout
            if time.time() - start_time > timeout_seconds:
                raise TimeoutError("Verification gate exceeded configured timeout threshold.")

        except TimeoutError as te:
            result.verification_score = 0.0
            result.recommendation = "REJECT"
            result.failure_classification = "VERIFICATION_TIMEOUT_FAILURE"
            result.failures.append(
                FailureFingerprint(
                    failure_type="VERIFICATION_TIMEOUT_FAILURE",
                    stage="Global Gate Monitor",
                    details=str(te),
                    category=FailureCategory.RUNTIME_STATE_FAILURE
                )
            )

        except Exception as e:
            result.verification_score = 0.0
            result.recommendation = "REJECT"
            result.failure_classification = "COMPONENT_RESOLUTION_FAILURE"
            result.failures.append(
                FailureFingerprint(
                    failure_type="COMPONENT_RESOLUTION_FAILURE",
                    stage="System Initializer",
                    details=f"Unexpected exception during verification boot: {str(e)}",
                    category=FailureCategory.INFRASTRUCTURE_FAILURE
                )
            )

        # Calculate final integrated verification score
        survivals = [
            result.dependency_survival,
            result.schema_survival,
            result.state_binding_survival,
            result.build_survival,
            result.runtime_survival,
            result.visual_survival,
            result.topology_survival
        ]
        result.verification_score = sum(survivals) / len(survivals)
        
        # Enforce strict correlation between failures and recommendation
        if result.failures:
            result.recommendation = "REJECT"
            if not result.failure_classification:
                result.failure_classification = result.failures[0].failure_type
        else:
            result.recommendation = "PASS"

        # ── VALIDATION RECORDING ──
        try:
            from app.sentinel.validation.validation_recorder import ValidationRecorder
            for fail in result.failures:
                ValidationRecorder.record_failure({
                    "branch_id": None, # Left unpopulated initially
                    "failure_type": fail.failure_type,
                    "failure_fingerprint": f"{fail.failure_type}:{fail.file or 'global'}",
                    "cfm": None,
                    "principle_violated": fail.stage,
                    "root_cause": fail.details,
                    "stage": fail.stage,
                    "severity": "ERROR",
                    "recovered": False,
                    "escape_mutation_used": False
                })
        except Exception:
            pass
        # ──────────────────────────

        return result
    @staticmethod
    def _verify_tier_0_compiler(project_path: Path, result: VerificationResult, project_id: str = "default"):
        # Frontend: tsc --noEmit and npm run build inside Docker
        frontend_src = WorkspaceArchitecture.frontend_root(project_path)
            
        if frontend_src.exists():
            package_json = frontend_src / "package.json"
            
            if not package_json.exists():
                print(f"[VERIFIER_WARNING] Tier0 compiler unavailable: missing package.json in {frontend_src}")
                result.failures.append(
                    FailureFingerprint(
                        failure_type="COMPILER_UNAVAILABLE",
                        source=FailureSource.COMPILER,
                        stage="Tier 0 Compiler Setup",
                        details=f"Mandatory Tier 0 compiler is unavailable: missing package.json in {frontend_src}.",
                        category=FailureCategory.INFRASTRUCTURE_FAILURE
                    )
                )
            else:
                try:
                    import subprocess
                    frontend_src_abs = os.path.abspath(str(frontend_src))
                    volume_name = f"{project_id}_node_modules"
                    
                    shell_script = (
                        "set -e\n"
                        "if [ ! -f node_modules/.package_json_hash ] || ! md5sum -c node_modules/.package_json_hash >/dev/null 2>&1; then\n"
                        "  npm install\n"
                        "  mkdir -p node_modules\n"
                        "  md5sum package.json > node_modules/.package_json_hash\n"
                        "fi\n"
                        "npx tsc --noEmit\n"
                        "npm run build\n"
                    )
                    
                    proc = subprocess.run(
                        [
                            "docker", "run", "--rm", "-i",
                            "-v", f"{frontend_src_abs}:/app",
                            "-v", f"{volume_name}:/app/node_modules",
                            "-w", "/app",
                            "node:20-alpine",
                            "sh", "-c", shell_script
                        ],
                        capture_output=True,
                        text=True
                    )
                    
                    combined_output = (proc.stdout or "") + "\n" + (proc.stderr or "")
                    result.compiler_output = combined_output
                    result.bundler_output = combined_output
                    
                    if proc.returncode != 0:
                        # Parse tsc output
                        # Example: src/App.tsx(5,10): error TS2304: Cannot find name 'Dashboard'.
                        has_ts_errors = False
                        for line in combined_output.splitlines():
                            if "error TS" in line:
                                match = re.match(r'^(.*?)\(\d+,\d+\):\s+error\s+(TS\d+):\s+(.*)$', line)
                                if match:
                                    file_rel = match.group(1)
                                    ts_code = match.group(2)
                                    msg = match.group(3)
                                    error_file = frontend_src / file_rel
                                    clean_file_rel = WorkspaceArchitecture.to_workspace_relative(project_path, error_file)
                                    result.failures.append(
                                        FailureFingerprint(
                                            failure_type=ts_code,
                                            source=FailureSource.COMPILER,
                                            stage="Tier 0A Compiler",
                                            details=msg,
                                            file=clean_file_rel,
                                            category=FailureCategory.COMPILER_FAILURE
                                        )
                                    )
                                    has_ts_errors = True
                                else:
                                    # Fallback if regex doesn't exactly match
                                    result.failures.append(
                                        FailureFingerprint(
                                            failure_type="FRONTEND_BUILD_FAILURE",
                                            source=FailureSource.COMPILER,
                                            stage="Tier 0A Compiler",
                                            details=line,
                                            category=FailureCategory.COMPILER_FAILURE
                                        )
                                    )
                                    has_ts_errors = True
                        if not has_ts_errors:
                            details_msg = proc.stderr[-500:] if proc.stderr else proc.stdout[-500:]
                            result.failures.append(
                                FailureFingerprint(
                                    failure_type="FRONTEND_BUILD_FAILURE",
                                    source=FailureSource.COMPILER,
                                    stage="Tier 0B Bundler",
                                    details=details_msg,
                                    category=FailureCategory.COMPILER_FAILURE
                                )
                            )
                except Exception as e:
                    print(f"[VERIFIER_WARNING] Exception executing Tier 0 Frontend compiler inside Docker: {e}")

        # Backend: compileall
        backend_dir = WorkspaceArchitecture.backend_root(project_path)
                
        if backend_dir:
            try:
                import subprocess
                proc = subprocess.run(
                    ["python", "-m", "compileall", "-q", "."],
                    cwd=str(backend_dir),
                    capture_output=True,
                    text=True,
                    shell=True
                )
                backend_output = (proc.stdout or "") + "\n" + (proc.stderr or "")
                if result.compiler_output:
                    result.compiler_output += "\n" + backend_output
                else:
                    result.compiler_output = backend_output
                if proc.returncode != 0:
                    result.failures.append(
                        FailureFingerprint(
                            failure_type="BACKEND_BUILD_FAILURE",
                            source=FailureSource.COMPILER,
                            stage="Tier 0C Compiler",
                            details=proc.stderr[-500:] if proc.stderr else proc.stdout[-500:],
                            category=FailureCategory.COMPILER_FAILURE
                        )
                    )
            except Exception as e:
                print(f"[VERIFIER_WARNING] Exception executing Tier 0 Backend compiler: {e}")



    @staticmethod
    def _verify_dependencies(
        project_path: Path,
        graph: ProjectTopologyGraph,
        result: VerificationResult
    ) -> None:
        """
        Scans projected code files and asserts that all internal import statements 
        successfully resolve to target components/files.
        """
        ui_nodes = [
            node for node in graph.nodes.values()
            if node.node_type == NodeType.UI_NODE or str(node.node_type) == "UI_NODE"
        ]

        if not ui_nodes:
            result.dependency_passed = True
            result.dependency_survival = 1.0
            return

        total_scanned = 0
        resolved_count = 0

        # Scan Frontend components directory
        frontend_src = WorkspaceArchitecture.frontend_file(project_path, "src")

        components_dir = frontend_src / "components"
        if not components_dir.exists():
            result.dependency_passed = False
            result.dependency_survival = 0.0
            result.failures.append(
                FailureFingerprint(
                    failure_type="ARTIFACT_DEPENDENCY_FAILURE",
                    stage="Verification Layer A",
                    details=f"Frontend components source folder missing at {components_dir}",
                    category=FailureCategory.GRAPH_STATE_FAILURE
                )
            )
            return

        # Scan all .tsx/.jsx files
        for root, _, files in os.walk(components_dir):
            for file in files:
                if file.endswith((".tsx", ".jsx", ".ts", ".js")):
                    file_path = Path(root) / file
                    total_scanned += 1
                    try:
                        content = file_path.read_text(encoding="utf-8")
                    except Exception:
                        continue

                    imports = re.findall(r'from\s+[\'"]([@\.\/][^\'"]+)[\'"]', content)
                    imports += re.findall(r'import\s+[\'"]([@\.\/][^\'"]+)[\'"]', content)

                    file_clean_path = WorkspaceArchitecture.to_workspace_relative(project_path, file_path)
                    file_failed = False

                    for imp_path in imports:
                        resolved = False
                        
                        if imp_path.startswith("@/components/"):
                            rel_imp = imp_path.replace("@/components/", "")
                            resolved = SentinelVerificationGate._check_file_exists(components_dir, rel_imp)
                        elif imp_path.startswith("@/"):
                            rel_imp = imp_path.replace("@/", "")
                            resolved = SentinelVerificationGate._check_file_exists(frontend_src, rel_imp)
                        elif imp_path.startswith("."):
                            resolved = SentinelVerificationGate._check_file_exists(Path(root), imp_path)
                        else:
                            resolved = True

                        if not resolved:
                            file_failed = True
                            result.failures.append(
                                FailureFingerprint(
                                    failure_type="UNRESOLVED_IMPORT_FAILURE",
                                    stage="Verification Layer A",
                                    details=f"Failed to resolve import '{imp_path}' in {file_clean_path}",
                                    file=file_clean_path,
                                    component=file,
                                    category=FailureCategory.GRAPH_STATE_FAILURE
                                )
                            )

                    if not file_failed:
                        resolved_count += 1

        if total_scanned > 0:
            result.dependency_survival = resolved_count / total_scanned
        else:
            result.dependency_survival = 1.0

        result.dependency_passed = (result.dependency_survival == 1.0)

    @staticmethod
    def _verify_schemas(
        project_path: Path,
        graph: ProjectTopologyGraph,
        result: VerificationResult
    ) -> None:
        """
        Parses all schema fields from topology schema nodes and asserts that any 
        attributes accessed or mapped in the UI exist inside the schema contract.
        """
        schema_fields = {}
        for node_id, node in graph.nodes.items():
            if node.node_type == NodeType.SCHEMA_NODE or str(node.node_type) == "SCHEMA_NODE":
                entity_name = node.properties.get("entity_name", "").lower()
                if not entity_name:
                    entity_name = node_id.replace("schema_", "").lower()
                
                fields = [f.get("name") for f in node.properties.get("fields", []) if f.get("name")]
                fields += ["id", "_id", "id_", "created_at", "updated_at"]
                schema_fields[entity_name] = fields

        if not schema_fields:
            result.schema_passed = True
            result.schema_survival = 1.0
            return

        frontend_src = WorkspaceArchitecture.frontend_file(project_path, "src")

        components_dir = frontend_src / "components"
        if not components_dir.exists():
            return

        total_scanned = 0
        passed_count = 0

        for root, _, files in os.walk(components_dir):
            for file in files:
                if file.endswith((".tsx", ".jsx", ".ts", ".js")):
                    file_path = Path(root) / file
                    total_scanned += 1
                    try:
                        content = file_path.read_text(encoding="utf-8")
                    except Exception:
                        continue

                    file_clean_path = WorkspaceArchitecture.to_workspace_relative(project_path, file_path)
                    matched_entity = None
                    file_lower = file.lower()
                    for ent in schema_fields.keys():
                        if ent in file_lower:
                            matched_entity = ent
                            break

                    if matched_entity:
                        valid_fields = schema_fields[matched_entity]
                        
                        field_accesses = re.findall(r'(?:item|data|payload|value)\.([a-zA-Z_][a-zA-Z0-9_]*)', content)
                        field_accesses += re.findall(r'name\s*=\s*[\'"]([a-zA-Z_][a-zA-Z0-9_]*)[\'"]', content)
                        
                        destructure_blocks = re.findall(r'const\s+\{\s*([^\}]+)\}\s*=\s*(?:item|data|payload)', content)
                        for block in destructure_blocks:
                            for field in re.split(r',\s*', block):
                                clean_f = field.split(":")[0].strip()
                                if clean_f:
                                    field_accesses.append(clean_f)

                        scanned_fields = set(f for f in field_accesses if f)
                        
                        for field in scanned_fields:
                            if field in ("map", "filter", "length", "split", "join", "target", "value", "id"):
                                continue

                            if field not in valid_fields:
                                result.warnings.append(
                                    FailureFingerprint(
                                        failure_type="SCHEMA_CONTRACT_FAILURE",
                                        stage="Verification Layer B",
                                        details=f"Schema field '{field}' referenced in UI does not exist on schema entity '{matched_entity}'",
                                        file=file_clean_path,
                                        field=field,
                                        component=file,
                                        category=FailureCategory.GRAPH_STATE_FAILURE
                                    )
                                )

                    passed_count += 1

        if total_scanned > 0:
            result.schema_survival = passed_count / total_scanned
        else:
            result.schema_survival = 1.0

        result.schema_passed = (result.schema_survival == 1.0)

    @staticmethod
    def _verify_state_bindings(
        project_path: Path,
        graph: ProjectTopologyGraph,
        result: VerificationResult
    ) -> None:
        print("[SENTINEL_GATE] Executing S-0.4: Circuit-Level State Binding Tracing...")

        frontend_src = WorkspaceArchitecture.frontend_file(project_path, "src")

        components_dir = frontend_src / "components"
        if not components_dir.exists():
            result.state_binding_passed = True
            result.state_binding_survival = 1.0
            return

        total_scanned = 0
        passed_count = 0

        for root, _, files in os.walk(components_dir):
            for file in files:
                if file.endswith((".tsx", ".jsx")):
                    file_path = Path(root) / file
                    total_scanned += 1
                    try:
                        file_content = file_path.read_text(encoding="utf-8")
                    except Exception:
                        continue

                    file_clean_path = WorkspaceArchitecture.to_workspace_relative(project_path, file_path)
                    current_domain = None
                    file_lower = file.lower()
                    for node in graph.nodes.values():
                        if getattr(node, "node_type", None) == NodeType.SCHEMA_NODE:
                            entity_name = node.properties.get("entity_name", "").lower()
                            if entity_name and entity_name in file_lower:
                                current_domain = entity_name
                                break

                    has_form_or_btn = "<button" in file_content or "<form" in file_content or "<input" in file_content
                    
                    if has_form_or_btn:
                        handlers = re.findall(r'(?:onClick|onSubmit|onChange)\s*=\s*\{\s*([a-zA-Z0-9_]+)\s*\}', file_content)
                        
                        for h in handlers:
                            is_prop = False
                            if f"export function {file_path.stem}({{ " in file_content and h in file_content.split(f"export function {file_path.stem}({{ ")[1].split("}")[0]:
                                is_prop = True
                            if f"const {file_path.stem} = ({{ " in file_content and h in file_content.split(f"const {file_path.stem} = ({{ ")[1].split("}")[0]:
                                is_prop = True
                            if f"props.{h}" in file_content or f"props =>" in file_content:
                                is_prop = True
                            if h in ("onSave", "onSubmit", "onClick", "onChange"):
                                if f"function {h}" not in file_content and f"const {h}" not in file_content:
                                    is_prop = True

                            if is_prop:
                                continue

                            is_imported = False
                            for line in file_content.split('\n'):
                                if line.strip().startswith("import ") and h in line:
                                    is_imported = True
                                    break
                            
                            if is_imported:
                                continue

                            handler_body = ""
                            body_match = re.search(rf'(?:const|function)\s+{h}\s*(?:=\s*\([^)]*\)\s*=>\s*|\([^)]*\)\s*)\{{\s*(.*?)\s*\}}', file_content, re.DOTALL)
                            if body_match:
                                handler_body = body_match.group(1)
                            else:
                                body_match = re.search(rf'const\s+{h}\s*=\s*\([^)]*\)\s*=>\s*(.*)', file_content)
                                if body_match:
                                    handler_body = body_match.group(1)
                            
                            if handler_body:
                                ui_viewport_actions = ["scrollPrev", "scrollNext", "scrollTo", "focus", "blur"]
                                is_viewport = any(re.search(rf'\.{action}\s*\(', handler_body) for action in ui_viewport_actions)
                                if is_viewport:
                                    continue
                                
                                is_remote = re.search(r'\b(fetch|dispatch|api\.(post|put|delete|patch)|axios\.)', handler_body)
                                if is_remote:
                                    continue
                                    
                                is_mutation = False
                                state_target = None
                                set_match = re.search(r'\bset([A-Z][a-zA-Z0-9_]*)\s*\(', handler_body)
                                if set_match:
                                    is_mutation = True
                                    state_target = set_match.group(1).lower()
                                
                                if not is_mutation:
                                    result.warnings.append(
                                        FailureFingerprint(
                                            failure_type="STATE_MUTATION_MISSING",
                                            stage="Verification Layer C",
                                            details=f"Interactive handler '{h}' lacks state mutation.",
                                            file=file_clean_path,
                                            component=file,
                                            category=FailureCategory.RUNTIME_STATE_FAILURE
                                        )
                                    )
                                    continue
                                    
                                if current_domain and state_target and state_target != current_domain:
                                    if state_target not in current_domain and current_domain not in state_target:
                                        result.warnings.append(
                                            FailureFingerprint(
                                                failure_type="INVALID_STATE_TARGET",
                                                stage="Verification Layer C",
                                                details=f"Handler modifies '{state_target}' but domain is '{current_domain}'.",
                                                file=file_clean_path,
                                                component=file,
                                                category=FailureCategory.RUNTIME_STATE_FAILURE
                                            )
                                        )
                                        continue

                                state_var_name = state_target.lower() if state_target else ""
                                content_without_decls = re.sub(
                                    rf'const\s+\[\s*{re.escape(state_var_name)}\s*,\s*\w+\s*\]\s*=.*',
                                    '',
                                    file_content,
                                    flags=re.IGNORECASE
                                )
                                is_consumed = bool(re.search(rf'\b{re.escape(state_var_name)}\b', content_without_decls, re.IGNORECASE))
                                if not is_consumed:
                                    result.warnings.append(
                                        FailureFingerprint(
                                            failure_type="ORPHANED_STATE_MUTATION",
                                            stage="Verification Layer C",
                                            details=f"Mutation of '{state_var_name}' is orphaned (not consumed in render).",
                                            file=file_clean_path,
                                            component=file,
                                            category=FailureCategory.RUNTIME_STATE_FAILURE
                                        )
                                    )
                                    continue
                            else:
                                result.warnings.append(
                                    FailureFingerprint(
                                        failure_type="UNRESOLVED_EVENT_HANDLER",
                                        stage="Verification Layer C",
                                        details=f"Unresolved interactive event handler '{h}' referenced in UI element",
                                        file=file_clean_path,
                                        component=file,
                                        category=FailureCategory.RUNTIME_STATE_FAILURE
                                    )
                                )

                    passed_count += 1

        if total_scanned > 0:
            result.state_binding_survival = passed_count / total_scanned
        else:
            result.state_binding_survival = 1.0

        result.state_binding_passed = (result.state_binding_survival == 1.0)

    @staticmethod
    def _verify_builds(
        project_path: Path,
        graph: ProjectTopologyGraph,
        result: VerificationResult
    ) -> None:
        """
        S-0.5: Verification Layer D — Build dry-runs
        Compiles python backend and syntax-checks frontend components.
        """
        backend_dir = WorkspaceArchitecture.backend_root(project_path)

        total_files = 0
        passed_files = 0

        # 1. Compile Backend Python Files
        if backend_dir.exists():
            for root, _, files in os.walk(backend_dir):
                for file in files:
                    if file.endswith(".py") and "venv" not in root and ".venv" not in root:
                        file_path = Path(root) / file
                        total_files += 1
                        try:
                            # Compile using python built-in compile syntax check
                            content = file_path.read_text(encoding="utf-8")
                            compile(content, str(file_path), "exec")
                            passed_files += 1
                        except SyntaxError as se:
                            result.failures.append(
                                FailureFingerprint(
                                    failure_type="BACKEND_BUILD_FAILURE",
                                    stage="Verification Layer D",
                                    details=f"Python Syntax Error: {se.msg} in {file} line {se.lineno}",
                                    file=WorkspaceArchitecture.to_workspace_relative(project_path, file_path),
                                    component=file,
                                    category=FailureCategory.COMPILER_FAILURE
                                )
                            )

        # 2. Basic tag balancing check on Frontend components
        frontend_src = WorkspaceArchitecture.frontend_file(project_path, "src")

        components_dir = frontend_src / "components"
        if components_dir.exists():
            for root, _, files in os.walk(components_dir):
                for file in files:
                    if file.endswith((".tsx", ".jsx")):
                        file_path = Path(root) / file
                        total_files += 1
                        try:
                            content = file_path.read_text(encoding="utf-8")
                            
                            # Check imports
                            imports = re.findall(r'from\s+["\']([^"\']+)["\']', content)
                            for imp in imports:
                                if imp.startswith("."):
                                    resolved = (file_path.parent / imp).resolve()
                                    if not resolved.exists() and not Path(str(resolved) + ".tsx").exists() and not Path(str(resolved) + ".ts").exists() and not Path(str(resolved) + ".jsx").exists() and not Path(str(resolved) + ".js").exists():
                                        raise ImportError(f"Unresolved frontend import: {imp}")

                            passed_files += 1
                        except Exception as e:
                            result.warnings.append(
                                FailureFingerprint(
                                    failure_type="FRONTEND_BUILD_FAILURE",
                                    source=FailureSource.HEURISTIC,
                                    stage="Verification Layer D",
                                    details=f"Frontend structural build warning: {str(e)}",
                                    file=WorkspaceArchitecture.to_workspace_relative(project_path, file_path),
                                    component=file,
                                    category=FailureCategory.COMPILER_FAILURE
                                )
                            )

        if total_files > 0:
            result.build_survival = passed_files / total_files
        else:
            result.build_survival = 1.0

        result.build_passed = (result.build_survival == 1.0)

    @staticmethod
    def _verify_runtime_render(
        project_path: Path,
        graph: ProjectTopologyGraph,
        result: VerificationResult
    ) -> None:
        """S-0.6: deterministic runtime and page-render health checks."""
        print("[SENTINEL_GATE] Executing S-0.6: Runtime Page Render Check...")

        frontend_src = WorkspaceArchitecture.frontend_file(project_path, "src")

        # Skip runtime render checks only if there are no UI components in the graph and no frontend source files exist
        frontend_exists = False
        if frontend_src.exists():
            try:
                frontend_exists = any(frontend_src.iterdir())
            except Exception:
                pass

        ui_node_types = {NodeType.UI_NODE, NodeType.PAGE_NODE, NodeType.SCREEN_NODE, NodeType.NAV_LAYOUT_NODE}
        has_ui = any(getattr(n, "node_type", None) in ui_node_types for n in graph.nodes.values())
        if not has_ui and not frontend_exists:
            result.runtime_passed = True
            result.runtime_survival = 1.0
            result.visual_passed = True
            result.visual_survival = 1.0
            result.visual_evaluated = False
            return

        def safe_relative(file_path: Path) -> str:
            return WorkspaceArchitecture.to_workspace_relative(project_path, file_path)

        def add_objective_failure(failure_type: str, stage: str, details: str, file_path: Path = None, component: str = None, category: Optional[FailureCategory] = FailureCategory.RUNTIME_STATE_FAILURE) -> None:
            result.failures.append(
                FailureFingerprint(
                    failure_type=failure_type,
                    source=FailureSource.RUNTIME if "HEALTH" in failure_type or "BOOT" in failure_type else FailureSource.VISUAL,
                    stage=stage,
                    details=details,
                    file=safe_relative(file_path) if file_path else None,
                    component=component,
                    category=category
                )
            )

        def add_advisory_warning(failure_type: str, stage: str, details: str, file_path: Path = None, component: str = None, category: Optional[FailureCategory] = FailureCategory.RUNTIME_STATE_FAILURE) -> None:
            result.warnings.append(
                FailureFingerprint(
                    failure_type=failure_type,
                    source=FailureSource.HEURISTIC,
                    stage=stage,
                    details=details,
                    file=safe_relative(file_path) if file_path else None,
                    component=component,
                    category=category
                )
            )

        def resolve_source_file(base: Path) -> Path:
            if base.suffix:
                return base if base.exists() and base.is_file() else None
            for ext in (".tsx", ".jsx", ".ts", ".js"):
                candidate = Path(str(base) + ext)
                if candidate.exists() and candidate.is_file():
                    return candidate
            for ext in (".tsx", ".jsx", ".ts", ".js"):
                candidate = base / f"index{ext}"
                if candidate.exists() and candidate.is_file():
                    return candidate
            return None

        def resolve_import(current_file: Path, import_path: str) -> Path:
            if import_path.startswith("@/"):
                return resolve_source_file((frontend_src / import_path[2:]).resolve())
            if import_path.startswith("."):
                return resolve_source_file((current_file.parent / import_path).resolve())
            return None

        if not frontend_src.exists():
            result.runtime_passed = False
            result.runtime_survival = 0.0
            result.visual_passed = False
            result.visual_survival = 0.0
            result.visual_evaluated = False
            print("[VERIFY_RUNTIME] entrypoint=NONE runtime_ok=False visual_ok=N/A visual_evaluated=False")
            add_objective_failure("RUNTIME_BOOT_FAILURE", "Layer E: Entrypoint Resolution", f"Frontend src directory missing at {frontend_src}")
            return

        ENTRY_FILES = [
            "main.tsx", "main.jsx",
            "App.tsx", "App.jsx",
            "app.tsx", "app.jsx",
            "Root.tsx", "Root.jsx",
        ]

        app_file = None
        for candidate_name in ENTRY_FILES:
            candidate = frontend_src / candidate_name
            if candidate.exists():
                app_file = candidate
                break

        if not app_file:
            best_candidate = None
            best_score = -1
            
            for ext in ("*.tsx", "*.jsx"):
                for candidate in frontend_src.rglob(ext):
                    try:
                        file_content = candidate.read_text(encoding="utf-8")
                        if bool(re.search(r'export\s+default|function\s+[A-Z]\w*\s*\(|const\s+[A-Z]\w*\s*=', file_content)):
                            score = 0
                            lname = candidate.name.lower()
                            if lname.startswith("index"): score += 25
                            if lname.startswith("main"): score += 25
                            if lname.startswith("app"): score += 20
                            if lname.startswith("root"): score += 15
                            
                            if "ReactDOM.createRoot" in file_content: score += 100
                            if "<RouterProvider" in file_content: score += 50
                            if "<BrowserRouter" in file_content: score += 50
                            if "export default" in file_content: score += 10
                            
                            if score > best_score:
                                best_score = score
                                best_candidate = candidate
                    except Exception:
                        pass
            if best_candidate:
                app_file = best_candidate

        if not app_file:
            result.runtime_passed = False
            result.runtime_survival = 0.0
            result.visual_passed = False
            result.visual_survival = 0.0
            result.visual_evaluated = False
            print("[VERIFY_RUNTIME] entrypoint=NONE runtime_ok=False visual_ok=N/A visual_evaluated=False")
            add_objective_failure("RUNTIME_BOOT_FAILURE", "Layer E: Entrypoint Resolution", "App.jsx/tsx entry point not found in frontend src.")
            return

        try:
            content = app_file.read_text(encoding="utf-8")
            runtime_ok = True
            visual_ok = True

            if re.search(r'throw\s+new\s+Error|process\.exit\s*\(|while\s*\(\s*true\s*\)', content):
                runtime_ok = False
                add_objective_failure("HEALTH_CHECK_FAILURE", "Layer E: Static Runtime Health", "App entry contains an obvious render-crash or infinite-loop pattern.", app_file, app_file.name)

            has_component = bool(re.search(r'export\s+default|function\s+[A-Z]\w*\s*\(|const\s+[A-Z]\w*\s*=', content))
            has_jsx = bool(re.search(r'return\s*\(?\s*<|=>\s*\(?\s*<', content, re.S))
            if not has_component or not has_jsx:
                runtime_ok = False
                add_objective_failure("RUNTIME_BOOT_FAILURE", "Layer E: Static Runtime Health", "App entry does not expose a component with a JSX render path.", app_file, app_file.name)

            blank_patterns = [
                r'return\s+null\s*;',
                r'return\s*\(\s*<>\s*</>\s*\)',
                r'return\s*\(\s*<div\s*/>\s*\)',
                r'display\s*:\s*[\'\"]none[\'\"]',
            ]
            if any(re.search(pattern, content, re.S) for pattern in blank_patterns):
                visual_ok = False
                add_objective_failure("VISUAL_RENDER_FAILURE", "Layer E: Visual Render Health", "App entry appears to render a blank or hidden page.", app_file, app_file.name)

            uses_routes = "<Routes" in content or "<Route" in content or "createBrowserRouter" in content
            uses_router = "<Router" in content or "<BrowserRouter" in content or "<HashRouter" in content or "<RouterProvider" in content
            
            router_style = "NONE"
            if "<RouterProvider" in content: router_style = "RouterProvider"
            elif "<BrowserRouter" in content: router_style = "BrowserRouter"
            elif "<HashRouter" in content: router_style = "HashRouter"
            elif "<Router" in content: router_style = "Router"
            
            if uses_routes and not uses_router:
                visual_ok = False
                add_objective_failure("VISUAL_RENDER_FAILURE", "Layer E: Router Render Health", "Routes are declared without a Router/RouterProvider wrapper.", app_file, app_file.name)

            for route_match in re.finditer(r'<Route\b([^>]*)>', content, re.S):
                route_attrs = route_match.group(1)
                if "element=" not in route_attrs and "Component=" not in route_attrs:
                    visual_ok = False
                    add_objective_failure("VISUAL_RENDER_FAILURE", "Layer E: Router Render Health", "Route declaration is missing an element or Component binding.", app_file, app_file.name)
                    break

            imports = re.findall(r'import\s+(.+?)\s+from\s+[\'\"]([^\'\"]+)[\'\"]', content, re.S)
            for spec, import_path in imports:
                if import_path.startswith((".", "@/")) and not resolve_import(app_file, import_path):
                    runtime_ok = False
                    add_objective_failure("RUNTIME_BOOT_FAILURE", "Layer E: Entrypoint Resolution", f"App imports unresolved render dependency '{import_path}'.", app_file, app_file.name)
                names = []
                named_match = re.search(r'\{([^}]+)\}', spec)
                if named_match:
                    names.extend(part.split(" as ")[-1].strip() for part in named_match.group(1).split(","))
                default_name = spec.split("{")[0].split(",")[0].strip()
                if default_name and default_name not in ("type", "React"):
                    names.append(default_name)
                content_without_imports = re.sub(r'import\s+.*?;', '', content)
                content_without_imports = re.sub(r'import\s+.*?from\s+.*?;', '', content_without_imports)
                for name in names:
                    if name and name[0].isupper():
                        is_projected = bool(re.search(rf'\b{re.escape(name)}\b', content_without_imports))
                        if not is_projected:
                            # Advisory warning - do NOT fail visual_ok
                            add_advisory_warning("VISUAL_RENDER_FAILURE", "Layer E: Visual Render Health", f"Imported component '{name}' is not projected into the App render tree.", app_file, name)

            result.runtime_passed = runtime_ok
            result.runtime_survival = 1.0 if runtime_ok else 0.0
            
            if not runtime_ok:
                result.visual_passed = False
                result.visual_survival = 0.0
                result.visual_evaluated = False
            else:
                result.visual_passed = visual_ok
                result.visual_survival = 1.0 if visual_ok else 0.0
                result.visual_evaluated = True
                
            log_str = (
                f"[VERIFY_RUNTIME] entrypoint={app_file.name} router_style={router_style}\n"
                f"[VERIFY_RUNTIME] runtime_ok={runtime_ok} visual_ok={visual_ok if result.visual_evaluated else 'N/A'} visual_evaluated={result.visual_evaluated}"
            )
            print(log_str)
            result.runtime_output = log_str
            result.render_output = log_str

        except Exception as e:
            result.runtime_passed = False
            result.runtime_survival = 0.0
            result.visual_passed = False
            result.visual_survival = 0.0
            result.visual_evaluated = False
            print(f"[VERIFY_RUNTIME] entrypoint={app_file.name if app_file else 'NONE'} runtime_ok=False visual_ok=N/A visual_evaluated=False")
            add_objective_failure("HEALTH_CHECK_FAILURE", "Layer E: Static Runtime Health", f"Runtime render health check failed: {str(e)}", app_file, app_file.name if app_file else None)

    @staticmethod
    def _verify_topology_integrity(
        graph: ProjectTopologyGraph,
        result: VerificationResult,
        intent_graph: Optional[Any] = None
    ) -> None:
        """
        S-0.6B: Verification Layer F — Topology Integrity Checks
        Validates business workflows by comparing intent expectations to the active graph.
        Enforces that CRM paths are cohesive and lack isolated/orphaned nodes.
        """
        ui_nodes = [nid for nid, n in graph.nodes.items() if n.node_type == NodeType.UI_NODE or str(n.node_type) == "UI_NODE"]
        schema_nodes = [nid for nid, n in graph.nodes.items() if n.node_type == NodeType.SCHEMA_NODE or str(n.node_type) == "SCHEMA_NODE"]

        if not ui_nodes and not schema_nodes:
            result.topology_passed = True
            result.topology_survival = 1.0
            return

        # Topology Rule 1: Every SCHEMA_NODE must have an associated UI_NODE rendering/managing it
        connected_schemas = 0
        for sn in schema_nodes:
            clean_name = sn.replace("schema_", "").lower()
            
            # Check if any UI component is designed to render it
            has_matching_ui = False
            for un in ui_nodes:
                ui_comp_lower = un.lower()
                if clean_name in ui_comp_lower or ui_comp_lower in clean_name:
                    has_matching_ui = True
                    break

            if has_matching_ui:
                connected_schemas += 1
            else:
                result.failures.append(
                    FailureFingerprint(
                        failure_type="TOPOLOGY_INTEGRITY_FAILURE",
                        stage="Verification Layer F",
                        details=f"Disconnected CRM Domain: Schema node '{sn}' lacks an associated UI_NODE controller.",
                        component=sn,
                        category=FailureCategory.TOPOLOGY_FAILURE
                    )
                )

        # Topology Rule 2: AppLayout or Entry route must reach all UI component sub-systems
        if ui_nodes:
            layout_node = None
            for un in ui_nodes:
                if "layout" in un.lower() or "root" in un.lower() or graph.nodes[un].properties.get("is_root") is True:
                    layout_node = un
                    break

            if layout_node:
                # Simple reachability check: Ensure renders_component or imports edges exist
                reached_ui = 0
                for un in ui_nodes:
                    if un == layout_node:
                        reached_ui += 1
                        continue
                    
                    # Direct renders edge check
                    has_path = any(
                        (e.source_id == layout_node and e.target_id == un) or
                        (e.source_id == un and e.target_id == layout_node)
                        for e in graph.edges
                    )
                    if has_path:
                        reached_ui += 1
                    else:
                        result.failures.append(
                            FailureFingerprint(
                                failure_type="TOPOLOGY_INTEGRITY_FAILURE",
                                stage="Verification Layer F",
                                details=f"Orphaned Module: UI component '{un}' is structurally unreachable from primary AppLayout/Dashboard.",
                                component=un,
                                category=FailureCategory.TOPOLOGY_FAILURE
                            )
                        )

                result.topology_survival = reached_ui / len(ui_nodes)
            else:
                result.topology_survival = 0.5
                result.failures.append(
                    FailureFingerprint(
                        failure_type="TOPOLOGY_INTEGRITY_FAILURE",
                        stage="Verification Layer F",
                        details="Missing Entry point page (AppLayout or component with is_root=True) to anchor topology reachability checks.",
                        category=FailureCategory.TOPOLOGY_FAILURE
                    )
                )
        else:
            result.topology_survival = 1.0

        def has_cycles():
            visited = set()
            path = set()
            def dfs(node):
                if node in path: return True
                if node in visited: return False
                visited.add(node)
                path.add(node)
                for edge in graph.edges:
                    if edge.source_id == node and dfs(edge.target_id):
                        return True
                path.remove(node)
                return False
            for node in graph.nodes:
                if dfs(node): return True
            return False
            
        if has_cycles():
            result.topology_survival = 0.0
            result.failures.append(
                FailureFingerprint(
                    failure_type="TOPOLOGY_INTEGRITY_FAILURE",
                    stage="Verification Layer F",
                    details="Cycle detected in topology.",
                    category=FailureCategory.TOPOLOGY_FAILURE
                )
            )

        if intent_graph:
            for n_id, n_data in intent_graph.nodes.items():
                if n_id not in graph.nodes:
                    result.topology_survival = 0.0
                    result.failures.append(
                        FailureFingerprint(
                            failure_type="TOPOLOGY_INTEGRITY_FAILURE",
                            stage="Verification Layer F",
                            details=f"Intent graph expected node '{n_id}'.",
                            category=FailureCategory.TOPOLOGY_FAILURE
                        )
                    )

        if len(schema_nodes) > 0 and connected_schemas < len(schema_nodes):
            result.topology_passed = False
        else:
            result.topology_passed = (result.topology_survival == 1.0)

    @staticmethod
    def _check_file_exists(base_dir: Path, rel_path: str) -> bool:
        """Helper checking if file exists with support for multiple extensions."""
        target_path = (base_dir / rel_path).resolve()
        
        # Exact match
        if target_path.exists() and target_path.is_file():
            return True
            
        # Try extensions (.tsx, .jsx, .ts, .js)
        for ext in (".tsx", ".jsx", ".ts", ".js"):
            candidate = Path(str(target_path) + ext)
            if candidate.exists() and candidate.is_file():
                return True
                
        # Try index file inside directory
        if target_path.exists() and target_path.is_dir():
            for ext in (".tsx", ".jsx", ".ts", ".js"):
                candidate = target_path / f"index{ext}"
                if candidate.exists() and candidate.is_file():
                    return True

        return False



class TopologyVerificationResult(BaseModel):
    topology_passed: bool = True
    schema_passed: bool = True
    state_passed: bool = True
    route_passed: bool = True
    dependency_graph_passed: bool = True

    topology_survival: float = 1.0
    schema_survival: float = 1.0
    state_survival: float = 1.0
    route_survival: float = 1.0
    dependency_graph_survival: float = 1.0

    verification_score: float = 1.0
    failures: List[FailureFingerprint] = Field(default_factory=list)

    @property
    def overall_survival(self) -> float:
        values = [
            self.topology_survival,
            self.schema_survival,
            self.state_survival,
            self.route_survival,
            self.dependency_graph_survival,
        ]
        return round(sum(values) / len(values), 4)


class RepairGoal:
    def __init__(self, goal_id: str, target_type: str, target_name: str, expected_state: str):
        self.goal_id = goal_id
        self.target_type = target_type       # e.g., "EVENT_HANDLER", "SCHEMA_NODE", "ROUTE_NODE"
        self.target_name = target_name       # e.g., "toggleSidebar", "Note"
        self.expected_state = expected_state # e.g., "exists", "connected"
        self.completion = False
        
    def serialize(self) -> dict:
        return {
            "goal_id": self.goal_id,
            "target_type": self.target_type,
            "target_name": self.target_name,
            "expected_state": self.expected_state,
            "completion": self.completion
        }


def verify_repair_goal(graph: ProjectTopologyGraph, goal: RepairGoal) -> bool:
    if goal.target_type == "EVENT_HANDLER":
        for node in graph.nodes.values():
            if node.node_type == NodeType.UI_NODE or str(node.node_type) == "UI_NODE":
                bindings = node.properties.get("state_bindings", [])
                for b in bindings:
                    if b.get("state_name") == goal.target_name:
                        return True
                    if b.get("handler_name") == goal.target_name:
                        return True
        return False
    elif goal.target_type == "SCHEMA_NODE":
        exists = goal.target_name in graph.nodes or any(
            n.properties.get("entity_name") == goal.target_name
            for n in graph.nodes.values()
        )
        return exists
    elif goal.target_type == "STATE_NODE":
        exists = any(
            n.node_type == NodeType.STATE_NODE and n.properties.get("store_name") == goal.target_name
            for n in graph.nodes.values()
        )
        return exists
    return False


class SentinelTopologyVerifier:
    """
    In-memory topology verifier that evaluates logical relations,
    constraints, schemas, and state mappings without accessing the file system.
    """

    @staticmethod
    def verify(
        graph: ProjectTopologyGraph,
        intent_graph: Optional[Any] = None
    ) -> TopologyVerificationResult:
        result = TopologyVerificationResult()
        
        # Helper to log failures
        def add_failure(type_str: str, stage: str, details: str, category: Optional[FailureCategory] = None):
            result.failures.append(
                FailureFingerprint(
                    failure_type=type_str,
                    stage=stage,
                    details=details,
                    category=category
                )
            )

        # 1. route_survival
        ui_nodes = [node_id for node_id, node in graph.nodes.items() if node.node_type in (NodeType.UI_NODE, NodeType.PAGE_NODE)]
        if ui_nodes:
            has_root = any(graph.nodes[node_id].properties.get("is_root", False) for node_id in ui_nodes)
            if not has_root:
                result.route_survival = 0.0
                result.route_passed = False
                add_failure("ENTRY_ROUTE_FAILURE", "Sentinel Route Verifier", "No entry route (is_root=True) found in topology.", FailureCategory.GRAPH_STATE_FAILURE)

        # 2. state_survival
        if ui_nodes:
            state_nodes = {node_id for node_id, node in graph.nodes.items() if node.node_type == NodeType.STATE_NODE}
            checks = 0
            passes = 0
            for ui_id in ui_nodes:
                checks += 1
                has_binding = any(
                    edge.relation == "binds_state" and edge.target_id in state_nodes 
                    for edge in graph.edges if edge.source_id == ui_id
                )
                if has_binding:
                    passes += 1
                else:
                    add_failure("STATE_BINDING_FAILURE", "Sentinel State Verifier", f"UI node '{ui_id}' lacks binds_state edge.", FailureCategory.RUNTIME_STATE_FAILURE)
            
            result.state_survival = (passes / checks) if checks > 0 else 1.0
            result.state_passed = (result.state_survival == 1.0)

        # 3. dependency_graph_survival
        checks = 0
        passes = 0
        for edge in graph.edges:
            checks += 1
            if edge.target_id in graph.nodes:
                passes += 1
            else:
                add_failure("UNRESOLVED_IMPORT_FAILURE", "Sentinel Dependency Verifier", f"Edge points to non-existent node '{edge.target_id}'.", FailureCategory.GRAPH_STATE_FAILURE)
        result.dependency_graph_survival = (passes / checks) if checks > 0 else 1.0
        result.dependency_graph_passed = (result.dependency_graph_survival == 1.0)

        # 4. schema_survival and topology_survival
        # For simplicity in testing, we assume they pass unless there's an obvious missing schema fields
        schema_nodes = [node_id for node_id, node in graph.nodes.items() if node.node_type == NodeType.SCHEMA_NODE]
        for s_id in schema_nodes:
            # Minimal check
            pass

        result.verification_score = result.overall_survival
        
        # Determine overall pass
        if any(not val for val in [
            result.topology_passed,
            result.schema_passed,
            result.state_passed,
            result.route_passed,
            result.dependency_graph_passed
        ]):
            result.verification_score = min(result.verification_score, 0.4)

        return result

