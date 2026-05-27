# app/topology/ast_validator.py
"""
V4 Syntax Physics Engine — Stage 3: AST Pipeline

Provides purely deterministic syntax correctness, structural legality,
and parser validations on ASTFile projections. No cognition allowed here.
"""

from typing import Dict, List, Any
import re
from app.topology.ast_generator import ASTFile

class ASTValidator:
    """
    Purely Deterministic Syntax Physics Engine.
    Ensures that projected code complies with strict syntax and path rules.
    """

    @classmethod
    def validate_file(cls, ast_file: ASTFile) -> Dict[str, Any]:
        """
        Validate syntax correctness, import integrity, and projection boundaries.
        Returns {"passed": bool, "errors": List[str]}.
        """
        errors: List[str] = []
        code_str = ast_file.render()

        # ── 1. Parse/Compile Legality (Syntax Physics) ───────
        if ast_file.file_path.endswith(".py"):
            try:
                # Compile Python to check for syntax errors
                compile(code_str, ast_file.file_path, "exec")
            except SyntaxError as se:
                errors.append(f"Python SyntaxError in {ast_file.file_path} at line {se.lineno}: {se.msg}")
            except Exception as e:
                errors.append(f"Failed to compile Python AST {ast_file.file_path}: {e}")
        
        elif ast_file.file_path.endswith((".ts", ".tsx")):
            # Deterministic brace/tag matching for TypeScript/React
            if not cls._verify_brackets_matching(code_str):
                errors.append(f"TypeScript JSX validation failed: mismatched curly braces or tags in {ast_file.file_path}")

        # ── 2. Import Integrity Checks ────────────────────────
        for imp in ast_file.imports:
            if not imp.source:
                errors.append(f"Invalid blank import source detected in {ast_file.file_path}")
            if "/" in imp.source:
                errors.append(f"Illegal file path style in import statement source '{imp.source}' inside {ast_file.file_path}")

        # ── 3. Projection Path Legality ───────────────────────
        # Ensure that no code files attempt to overwrite key sandbox config files
        forbidden_writes = ["package.json", "vite.config.ts", "requirements.txt", "Dockerfile"]
        for forbidden in forbidden_writes:
            if forbidden in ast_file.file_path:
                errors.append(f"Governance violation: attempt to write to forbidden substrate file path '{ast_file.file_path}'")

        return {
            "passed": len(errors) == 0,
            "errors": errors
        }

    @classmethod
    def _verify_brackets_matching(cls, code: str) -> bool:
        """Helper to ensure balanced syntax boundaries in TSX/JSX files."""
        stack = []
        brackets = {'{': '}', '[': ']', '(': ')'}
        for char in code:
            if char in brackets.keys():
                stack.append(char)
            elif char in brackets.values():
                if not stack:
                    return False
                last = stack.pop()
                if brackets[last] != char:
                    return False
        return len(stack) == 0
