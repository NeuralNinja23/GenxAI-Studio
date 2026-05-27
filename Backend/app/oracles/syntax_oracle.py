# app/oracles/syntax_oracle.py
"""
V4 Syntax Oracle — Stage 4: Oracle Layer

HARD Oracle enforcing compile-level syntax physics across all projected files.
"""

from pathlib import Path
from typing import Any
import uuid

from app.core.logging import log
from app.oracles.base import BaseOracle, OracleResult
from app.topology.ast_generator import ASTGenerator
from app.topology.ast_validator import ASTValidator
from app.topology.topology_version_manager import TopologyVersionManager

class SyntaxOracle(BaseOracle):
    """
    Syntax Physics Oracle (HARD).
    Validates physical AST legality, compile checks, and TSX/JSX parsing correctness.
    No semantic reasoning or intent evaluation is allowed.
    """

    def __init__(self):
        super().__init__(name="syntax_oracle", is_hard=True)

    async def validate(self, project_id: str, project_path: Path, cycle_ctx: Any) -> OracleResult:
        log("ORACLE", f"🔍 Running Syntax Oracle physics checks on {project_id}")

        # Retrieve projected files listed in the context
        files_written = getattr(cycle_ctx, "files_written", [])
        if not files_written:
            # Fallback: scan generated files from the latest active topology graph
            graph = await TopologyVersionManager.get_active_topology(project_id)
            if graph:
                ast_files = ASTGenerator.generate(graph)
                files_written = list(ast_files.keys())
            else:
                return OracleResult(
                    passed=True,
                    reason="No files generated and no active topology found to compile.",
                    evidence_key=f"syntax-pass-empty-{uuid.uuid4()}"
                )

        errors = []
        for rel_path in files_written:
            full_path = project_path / rel_path
            if not full_path.exists():
                errors.append(f"File {rel_path} does not exist on disk but was registered in projection cycle.")
                continue

            try:
                # Read content from filesystem
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Mock an ASTFile representation to validate with ASTValidator
                from app.topology.ast_generator import ASTFile
                mock_ast = ASTFile(file_path=rel_path, raw_blocks=[content])
                val_res = ASTValidator.validate_file(mock_ast)
                
                if not val_res.get("passed"):
                    errors.extend(val_res.get("errors", []))
            except Exception as read_err:
                errors.append(f"Could not read projected file '{rel_path}' for compilation checks: {read_err}")

        passed = len(errors) == 0
        reason = "All projected files successfully compiled without syntax errors." if passed else f"Syntax compilation failures: {errors}"
        
        evidence_key = f"ev-syntax-pass-{str(uuid.uuid4())[:8]}" if passed else f"ev-syntax-fail-{str(uuid.uuid4())[:8]}"

        return OracleResult(
            passed=passed,
            reason=reason,
            metrics={"files_checked": len(files_written), "syntax_errors": len(errors)},
            evidence_key=evidence_key
        )
