# app/topology/ast_generator.py
"""
V4 AST Generator — Stage 3: AST Pipeline

Synthesizes high-level structured AST representations (ASTFile) from canonical
topology nodes, graph relationships, and projection configurations.
"""

from typing import Dict, List, Any, Optional, Set
import hashlib
import json
from pydantic import BaseModel, Field
from app.topology.node_types import NodeType
from app.topology.project_graph import ProjectTopologyGraph, TopologyNode

# ─────────────────────────────────────────────────────────────
# AST Node Structures
# ─────────────────────────────────────────────────────────────

class ASTImport(BaseModel):
    source: str
    symbols: List[str] = Field(default_factory=list)
    alias: Optional[str] = None

    def render(self, is_typescript: bool = False) -> str:
        if is_typescript:
            if not self.symbols:
                return f"import '{self.source}';"
            joined_symbols = ", ".join(self.symbols)
            return f"import {{ {joined_symbols} }} from '{self.source}';"
        else:
            if not self.symbols:
                return f"import {self.source}"
            joined_symbols = ", ".join(self.symbols)
            return f"from {self.source} import {joined_symbols}"


class ASTField(BaseModel):
    name: str
    type_str: str
    required: bool = True
    default: Optional[str] = None
    description: Optional[str] = None

    def render(self, is_typescript: bool = False) -> str:
        desc_comment = f"  # {self.description}\n" if self.description and not is_typescript else ""
        if is_typescript:
            opt = "" if self.required else "?"
            default_val = f" = {self.default}" if self.default else ""
            return f"  {self.name}{opt}: {self.type_str}{default_val};"
        else:
            default_factory = ""
            if self.default:
                default_factory = f" = Field(default={self.default})"
            elif not self.required:
                default_factory = " = None"
            elif self.description:
                default_factory = f" = Field(description='{self.description}')"
            return f"{desc_comment}    {self.name}: {self.type_str}{default_factory}"


class ASTMethod(BaseModel):
    name: str
    args: List[str] = Field(default_factory=list)
    body: List[str] = Field(default_factory=list)
    decorator: Optional[str] = None
    return_type: Optional[str] = None

    def render(self, is_typescript: bool = False) -> str:
        indent = "    "
        body_str = "\n".join([f"{indent}{line}" for line in self.body]) or f"{indent}pass"
        
        if is_typescript:
            args_str = ", ".join(self.args)
            ret = f": {self.return_type}" if self.return_type else ""
            body_ts = "\n".join([f"  {line}" for line in self.body]) or "  // noop"
            return f"  async {self.name}({args_str}){ret} {{\n{body_ts}\n  }}"
        else:
            dec = f"    @{self.decorator}\n" if self.decorator else ""
            args_str = ", ".join(["self"] + self.args)
            ret = f" -> {self.return_type}" if self.return_type else ""
            return f"{dec}    async def {self.name}({args_str}){ret}:\n{body_str}"


class ASTClass(BaseModel):
    name: str
    bases: List[str] = Field(default_factory=list)
    fields: List[ASTField] = Field(default_factory=list)
    methods: List[ASTMethod] = Field(default_factory=list)

    def render(self, is_typescript: bool = False) -> str:
        if is_typescript:
            base_str = f" extends {self.bases[0]}" if self.bases else ""
            fields_str = "\n".join([f.render(True) for f in self.fields])
            methods_str = "\n\n".join([m.render(True) for m in self.methods])
            body = "\n".join(filter(None, [fields_str, methods_str]))
            return f"export class {self.name}{base_str} {{\n{body}\n}}"
        else:
            base_str = f"({', '.join(self.bases)})" if self.bases else ""
            fields_str = "\n".join([f.render(False) for f in self.fields])
            methods_str = "\n\n".join([m.render(False) for m in self.methods])
            body = "\n".join(filter(None, [fields_str, methods_str])) or "    pass"
            return f"class {self.name}{base_str}:\n{body}"


class ASTRoute(BaseModel):
    path: str
    method: str
    handler_name: str
    args: List[str] = Field(default_factory=list)
    body: List[str] = Field(default_factory=list)
    response_model: Optional[str] = None

    def render(self) -> str:
        # FastAPI route projection
        args_str = ", ".join(self.args)
        resp = f", response_model={self.response_model}" if self.response_model else ""
        decorator = f"@router.{self.method.lower()}('{self.path}'{resp})"
        indent = "    "
        body_str = "\n".join([f"{indent}{line}" for line in self.body]) or f"{indent}pass"
        return f"{decorator}\nasync def {self.handler_name}({args_str}):\n{body_str}"


class ASTReactComponent(BaseModel):
    name: str
    state: List[str] = Field(default_factory=list)
    hooks: List[str] = Field(default_factory=list)
    jsx: str = ""

    def render(self) -> str:
        # React Functional TSX projection
        state_renders = "\n  ".join([f"const [{s}, set{s[0].upper()}{s[1:]}] = useState(null);" for s in self.state])
        hooks_renders = "\n  ".join(self.hooks)
        body = "\n  ".join(filter(None, [state_renders, hooks_renders]))
        jsx_indented = "\n".join([f"    {line}" for line in self.jsx.split("\n")])
        return (
            f"export default function {self.name}() {{\n"
            f"  {body}\n\n"
            f"  return (\n"
            f"{jsx_indented}\n"
            f"  );\n"
            f"}}"
        )


class ASTFile(BaseModel):
    file_path: str
    imports: List[ASTImport] = Field(default_factory=list)
    classes: List[ASTClass] = Field(default_factory=list)
    routes: List[ASTRoute] = Field(default_factory=list)
    components: List[ASTReactComponent] = Field(default_factory=list)
    raw_blocks: List[str] = Field(default_factory=list)
    integrity_hash: str = ""

    def render(self) -> str:
        """Render the complete structured code to a source string."""
        is_ts = self.file_path.endswith((".ts", ".tsx"))
        
        # Determine import lines
        import_lines = [imp.render(is_ts) for imp in self.imports]
        # Remove duplicate imports deterministically
        import_lines = sorted(list(set(import_lines)))
        
        # Render internal structures
        rendered_elements = []
        for cl in self.classes:
            rendered_elements.append(cl.render(is_ts))
        for rt in self.routes:
            rendered_elements.append(rt.render())
        for comp in self.components:
            rendered_elements.append(comp.render())
        for rb in self.raw_blocks:
            rendered_elements.append(rb)

        content = "\n\n".join(filter(None, ["\n".join(import_lines)] + rendered_elements)) + "\n"
        return content

    def calculate_hash(self) -> str:
        """Compute the syntactic projection hash of this file."""
        return hashlib.sha256(self.render().encode("utf-8")).hexdigest()

    def update_integrity(self) -> None:
        self.integrity_hash = self.calculate_hash()


# ─────────────────────────────────────────────────────────────
# AST Generator
# ─────────────────────────────────────────────────────────────

class ASTGenerator:
    """
    AST Generation Engine.
    Maps canonical graph topology nodes and relationship edges directly
    into concrete syntactic ASTFile blueprints. No text patches.
    """

    @staticmethod
    def generate(graph: ProjectTopologyGraph) -> Dict[str, ASTFile]:
        """
        Synthesize ASTFiles from the canonical ProjectTopologyGraph state.
        Returns a dictionary mapping filesystem destination paths to ASTFiles.
        """
        ast_files: Dict[str, ASTFile] = {}

        for node_id, node in graph.nodes.items():
            if node.node_type == NodeType.SCHEMA_NODE:
                path = "Backend/app/models/runtime_models.py"  # Scoped projection target
                if path not in ast_files:
                    ast_files[path] = ASTFile(file_path=path)
                cls_def = ASTGenerator._generate_schema_class(node)
                ast_files[path].classes.append(cls_def)
                
                # Ensure essential imports
                ast_files[path].imports.append(ASTImport(source="beanie", symbols=["Document", "Indexed"]))
                ast_files[path].imports.append(ASTImport(source="pydantic", symbols=["Field"]))
                ast_files[path].imports.append(ASTImport(source="typing", symbols=["Optional", "List", "Dict"]))

            elif node.node_type == NodeType.API_NODE:
                path = f"Backend/app/api/{node.properties.get('router_name', 'default')}.py"
                if path not in ast_files:
                    ast_files[path] = ASTFile(file_path=path)
                
                # Standard fastapi boilerplate setup
                ast_files[path].imports.append(ASTImport(source="fastapi", symbols=["APIRouter", "HTTPException"]))
                ast_files[path].raw_blocks.append("router = APIRouter()\n")
                
                endpoints = node.properties.get("endpoints", [])
                for ep in endpoints:
                    route = ASTGenerator._generate_api_route(ep)
                    ast_files[path].routes.append(route)

            elif node.node_type == NodeType.UI_NODE:
                comp_name = node.properties.get("component_name", "Component")
                path = f"Frontend/src/components/{comp_name}.tsx"
                if path not in ast_files:
                    ast_files[path] = ASTFile(file_path=path)
                
                # Create React Component AST
                features = node.properties.get("features", [])
                react_comp = ASTReactComponent(
                    name=comp_name,
                    state=["data", "loading"],
                    hooks=["const state = useLocation();"],
                    jsx=(
                        f"<div className='p-6 bg-slate-900 text-white rounded-lg shadow-xl'>\n"
                        f"  <h1 className='text-2xl font-bold mb-4'>{comp_name} View</h1>\n"
                        f"  <div className='text-sm text-slate-400'>Features: {', '.join(features)}</div>\n"
                        f"</div>"
                    )
                )
                ast_files[path].components.append(react_comp)
                ast_files[path].imports.append(ASTImport(source="react", symbols=["useState", "useEffect"]))
                ast_files[path].imports.append(ASTImport(source="react-router-dom", symbols=["useLocation"]))

        # Establish import mappings derived from topology edges
        for edge in graph.edges:
            if edge.relation == "imports":
                src_node = graph.nodes[edge.source_id]
                tgt_node = graph.nodes[edge.target_id]
                
                src_path = src_node.properties.get("file_path")
                tgt_name = tgt_node.properties.get("entity_name") or tgt_node.properties.get("component_name")
                tgt_module = tgt_node.properties.get("file_path", "").replace(".py", "").replace("/", ".").replace("Backend.", "")
                
                if src_path and tgt_name and tgt_module and src_path in ast_files:
                    ast_files[src_path].imports.append(ASTImport(source=tgt_module, symbols=[tgt_name]))

        # Update integrity hashes across all generated syntax trees
        for af in ast_files.values():
            af.update_integrity()

        return ast_files

    @staticmethod
    def _generate_schema_class(node: TopologyNode) -> ASTClass:
        fields = []
        for f in node.properties.get("fields", []):
            fields.append(
                ASTField(
                    name=f["name"],
                    type_str=f["type"],
                    required=f.get("required", True)
                )
            )
        
        return ASTClass(
            name=node.properties.get("entity_name", "Model"),
            bases=["Document"],
            fields=fields
        )

    @staticmethod
    def _generate_api_route(endpoint: Dict[str, Any]) -> ASTRoute:
        path = endpoint["path"]
        method = endpoint["method"]
        handler_name = f"{method.lower()}_{path.replace('/', '_').replace('{', '').replace('}', '')}"
        
        return ASTRoute(
            path=path,
            method=method,
            handler_name=handler_name,
            args=[],
            body=[
                f"# Realized API Handler for {method} {path}",
                "return {'status': 'success', 'data': []}"
            ]
        )
