# app/topology/ast_merger.py
"""
V4 AST Merger — Stage 3: AST Pipeline

Deterministic structural reconciliation of ASTFiles at the syntax tree node
level rather than file text or git diff level.
"""

from typing import List
from app.core.logging import log
from app.topology.ast_generator import ASTFile, ASTImport, ASTClass, ASTRoute, ASTReactComponent
from app.topology.ast_mutator import ASTMutator

class ASTMerger:
    """
    Deterministic Structural Reconciliation Engine.
    Merges branch mutations safely while preserving existing AST structural context.
    """

    @staticmethod
    def merge(base: ASTFile, target: ASTFile) -> ASTFile:
        """
        Merge target ASTFile nodes into the base ASTFile.
        Deduplicates imports, updates class elements, routes, and JSX components.
        """
        if base.file_path != target.file_path:
            raise ValueError(
                f"Cannot merge mismatched file paths: '{base.file_path}' vs '{target.file_path}'"
            )

        # ── 1. Reconcile Imports ──────────────────────────────
        for imp in target.imports:
            base = ASTMutator.add_import(base, source=imp.source, symbols=imp.symbols)

        # ── 2. Reconcile Classes ──────────────────────────────
        for t_class in target.classes:
            # Find if class already exists in base
            b_class = None
            for cl in base.classes:
                if cl.name == t_class.name:
                    b_class = cl
                    break

            if not b_class:
                # Class does not exist, safe to append
                base.classes.append(t_class)
            else:
                # Class exists, reconcile fields
                for f in t_class.fields:
                    base = ASTMutator.add_class_field(
                        base,
                        class_name=b_class.name,
                        field_name=f.name,
                        field_type=f.type_str,
                        required=f.required,
                        default=f.default,
                        description=f.description
                    )
                # Reconcile methods
                for m in t_class.methods:
                    base = ASTMutator.add_class_method(base, class_name=b_class.name, method=m)

        # ── 3. Reconcile FastAPI Routes ───────────────────────
        for t_route in target.routes:
            base = ASTMutator.add_api_route(base, t_route)

        # ── 4. Reconcile React Components ─────────────────────
        for t_comp in target.components:
            b_comp = None
            for comp in base.components:
                if comp.name == t_comp.name:
                    b_comp = comp
                    break

            if not b_comp:
                base.components.append(t_comp)
            else:
                # Merge state items
                b_comp.state = sorted(list(set(b_comp.state + t_comp.state)))
                # Merge hooks
                b_comp.hooks = sorted(list(set(b_comp.hooks + t_comp.hooks)))
                # Overwrite/update JSX structure
                b_comp.jsx = t_comp.jsx

        # ── 5. Reconcile Raw Blocks ───────────────────────────
        for rb in target.raw_blocks:
            if rb not in base.raw_blocks:
                base.raw_blocks.append(rb)

        base.update_integrity()
        return base
