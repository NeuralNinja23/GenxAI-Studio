# app/topology/ast_mutator.py
"""
V4 AST Mutator — Stage 3: AST Pipeline

Provides scope-aware, surgical syntax mutations on ASTFile structures.
Direct text replacement and regex modification are strictly prohibited.
"""

from typing import List, Optional
from app.core.logging import log
from app.topology.ast_generator import ASTFile, ASTImport, ASTField, ASTMethod, ASTClass, ASTRoute, ASTReactComponent

class ASTMutator:
    """
    Surgical Code Mutator.
    Executes controlled syntax tree deformations governed by topology bounds.
    """

    @staticmethod
    def add_import(ast_file: ASTFile, source: str, symbols: List[str]) -> ASTFile:
        """Surgically inject an import without causing duplicate declarations."""
        # Check if import source already exists
        found = False
        for imp in ast_file.imports:
            if imp.source == source:
                # Merge imported symbols
                new_symbols = sorted(list(set(imp.symbols + symbols)))
                imp.symbols = new_symbols
                found = True
                break

        if not found:
            ast_file.imports.append(ASTImport(source=source, symbols=symbols))

        ast_file.update_integrity()
        return ast_file

    @staticmethod
    def add_class_field(
        ast_file: ASTFile,
        class_name: str,
        field_name: str,
        field_type: str,
        required: bool = True,
        default: Optional[str] = None,
        description: Optional[str] = None
    ) -> ASTFile:
        """Insert a field into a target class definition in the ASTFile."""
        target_class = None
        for cl in ast_file.classes:
            if cl.name == class_name:
                target_class = cl
                break

        if not target_class:
            raise ValueError(f"Class '{class_name}' does not exist in ASTFile '{ast_file.file_path}'")

        # Check if field already exists, overwrite if found, otherwise append
        field_found = False
        for f in target_class.fields:
            if f.name == field_name:
                f.type_str = field_type
                f.required = required
                f.default = default
                f.description = description
                field_found = True
                break

        if not field_found:
            target_class.fields.append(
                ASTField(
                    name=field_name,
                    type_str=field_type,
                    required=required,
                    default=default,
                    description=description
                )
            )

        ast_file.update_integrity()
        return ast_file

    @staticmethod
    def add_class_method(ast_file: ASTFile, class_name: str, method: ASTMethod) -> ASTFile:
        """Surgically append a class method definition."""
        target_class = None
        for cl in ast_file.classes:
            if cl.name == class_name:
                target_class = cl
                break

        if not target_class:
            raise ValueError(f"Class '{class_name}' does not exist in ASTFile '{ast_file.file_path}'")

        # Replace existing or append
        target_class.methods = [m for m in target_class.methods if m.name != method.name]
        target_class.methods.append(method)

        ast_file.update_integrity()
        return ast_file

    @staticmethod
    def add_api_route(ast_file: ASTFile, route: ASTRoute) -> ASTFile:
        """Insert a new FastAPI route endpoint into the ASTFile."""
        # Replace existing route matching path and method
        ast_file.routes = [
            r for r in ast_file.routes
            if not (r.path == route.path and r.method.upper() == route.method.upper())
        ]
        ast_file.routes.append(route)
        ast_file.update_integrity()
        return ast_file

    @staticmethod
    def mutate_component_jsx(ast_file: ASTFile, component_name: str, new_jsx: str) -> ASTFile:
        """Surgically modify the JSX element composition of a React component."""
        target_comp = None
        for comp in ast_file.components:
            if comp.name == component_name:
                target_comp = comp
                break

        if not target_comp:
            raise ValueError(f"React component '{component_name}' does not exist in ASTFile '{ast_file.file_path}'")

        target_comp.jsx = new_jsx
        ast_file.update_integrity()
        return ast_file
