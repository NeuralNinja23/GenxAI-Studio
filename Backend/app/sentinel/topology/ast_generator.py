# app/sentinel/topology/ast_generator.py
"""
V4 AST Generator — Stage 3: AST Pipeline
=========================================

Synthesizes high-level structured AST representations (ASTFile) from canonical
topology nodes, graph relationships, and projection configurations.

COMPILATION POLICY (NON-NEGOTIABLE):
- LLVM, not Copilot.
- AST mappings remain 100% deterministic.
- Specific topology edges and properties map strictly to predefined, stable compiler patterns.
"""

from typing import Dict, List, Any, Optional, Set
import hashlib
import json
from pydantic import BaseModel, Field
from app.sentinel.topology.node_types import NodeType
from app.sentinel.topology.project_graph import ProjectTopologyGraph, TopologyNode


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
        
        # Render internal structures.
        # FIX #1: raw_blocks (e.g. `router = APIRouter()`) MUST come before routes
        # so that route decorators (@router.get/post/...) never reference an undefined name.
        rendered_elements = []
        for cl in self.classes:
            rendered_elements.append(cl.render(is_ts))
        for rb in self.raw_blocks:          # ← moved above routes
            rendered_elements.append(rb)
        for rt in self.routes:
            rendered_elements.append(rt.render())
        for comp in self.components:
            rendered_elements.append(comp.render())

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

        # First pass: identify active entity names for routing resolutions
        entity_lookup = {}
        for node_id, node in graph.nodes.items():
            if node.node_type == NodeType.SCHEMA_NODE:
                entity_lookup[node_id] = node.properties.get("entity_name", "Model")

        for node_id, node in graph.nodes.items():
            if node.node_type == NodeType.SCHEMA_NODE:
                path = "Backend/app/models/runtime_models.py"
                if path not in ast_files:
                    ast_files[path] = ASTFile(file_path=path)
                cls_def = ASTGenerator._generate_schema_class(node)
                ast_files[path].classes.append(cls_def)
                
                # Ensure essential Beanie imports
                ast_files[path].imports.append(ASTImport(source="beanie", symbols=["Document", "Indexed"]))
                ast_files[path].imports.append(ASTImport(source="pydantic", symbols=["Field"]))
                ast_files[path].imports.append(ASTImport(source="typing", symbols=["Optional", "List", "Dict"]))
                # FIX #2: datetime is always needed for created_at/updated_at fields generated
                # by the schema compiler. Without this, any timestamp field causes a NameError.
                ast_files[path].imports.append(ASTImport(source="datetime", symbols=["datetime"]))

            elif node.node_type == NodeType.API_NODE:
                router_name = node.properties.get("router_name", "default")
                path = f"Backend/app/api/{router_name}.py"
                if path not in ast_files:
                    ast_files[path] = ASTFile(file_path=path)
                
                # FastAPI imports
                ast_files[path].imports.append(ASTImport(source="fastapi", symbols=["APIRouter", "HTTPException"]))
                ast_files[path].imports.append(ASTImport(source="typing", symbols=["List", "Dict", "Optional"]))
                ast_files[path].raw_blocks.append("router = APIRouter()\n")

                # Resolve bound entity (if schema node has a binds edge to API or router)
                target_entity = "Model"
                for edge in graph.edges:
                    if edge.relation == "binds_schema" and (edge.source_id == node_id or edge.target_id == node_id):
                        schema_node_id = edge.target_id if edge.source_id == node_id else edge.source_id
                        if schema_node_id in entity_lookup:
                            target_entity = entity_lookup[schema_node_id]
                            # Import the bound entity from model space
                            ast_files[path].imports.append(
                                ASTImport(source="app.models.runtime_models", symbols=[target_entity])
                            )

                endpoints = node.properties.get("endpoints", [])
                for ep in endpoints:
                    route = ASTGenerator._generate_api_route(ep, target_entity)
                    ast_files[path].routes.append(route)

            elif node.node_type == NodeType.UI_NODE:
                comp_name = node.properties.get("component_name", "Component")
                path = f"Frontend/src/components/{comp_name}.tsx"
                if path not in ast_files:
                    ast_files[path] = ASTFile(file_path=path)
                
                # Trace active bound routes to inject deterministic async fetch hook hooks
                bound_endpoints = []
                for edge in graph.edges:
                    if edge.relation == "binds_route" and (edge.source_id == node_id or edge.target_id == node_id):
                        route_node_id = edge.target_id if edge.source_id == node_id else edge.source_id
                        route_node = graph.nodes.get(route_node_id)
                        if route_node:
                            bound_endpoints.append(route_node.properties.get("path", "/api/data"))

                fetch_hooks = []
                for be in bound_endpoints:
                    fetch_hooks.append(
                        f"useEffect(() => {{\n"
                        f"    const loadData = async () => {{\n"
                        f"      setLoading(true);\n"
                        f"      try {{\n"
                        f"        const res = await fetch('{be}');\n"
                        f"        const json = await res.json();\n"
                        f"        setData(json);\n"
                        f"      }} catch (err) {{\n"
                        f"        console.error(err);\n"
                        f"      }}\n"
                        f"      setLoading(false);\n"
                        f"    }};\n"
                        f"    loadData();\n"
                        f"  }}, []);"
                    )

                features = node.properties.get("features", [])
                
                # Check for other UI components to build a beautiful directory index in RootView
                if comp_name == "RootView":
                    other_ui_components = []
                    for other_id, other_node in graph.nodes.items():
                        if other_node.node_type == NodeType.UI_NODE:
                            other_cname = other_node.properties.get("component_name")
                            if other_cname and other_cname != "RootView":
                                other_ui_components.append(other_cname)
                    
                    if other_ui_components:
                        links_html = []
                        for other_c in other_ui_components:
                            links_html.append(
                                f"      <a href='/{other_c.lower()}' className='flex items-center justify-between p-4 bg-slate-800/40 border border-slate-700/50 rounded-xl hover:bg-slate-800 hover:border-cyan-500/50 transition-all group'>\n"
                                f"        <div>\n"
                                f"          <div className='font-bold text-slate-200 group-hover:text-cyan-400 transition-colors'>{other_c}</div>\n"
                                f"          <div className='text-xs text-slate-400 mt-1'>Click to open the {other_c} module</div>\n"
                                f"        </div>\n"
                                f"        <span className='text-slate-500 group-hover:text-cyan-400 transition-all transform group-hover:translate-x-1'>→</span>\n"
                                f"      </a>"
                            )
                        links_jsx = "\n".join(links_html)
                        
                        jsx_payload = (
                            f"<div className='min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center p-8'>\n"
                            f"  <div className='max-w-4xl w-full bg-slate-900/50 border border-slate-800 rounded-2xl p-8 backdrop-blur-md shadow-2xl'>\n"
                            f"    <h1 className='text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-indigo-500 mb-2'>\n"
                            f"      {graph.project_id.replace('-', ' ').title()}\n"
                            f"    </h1>\n"
                            f"    <p className='text-slate-400 mb-8'>GenxAI V4 Cognitively Synthesized Application Portal</p>\n"
                            f"    \n"
                            f"    <h2 className='text-lg font-semibold text-slate-300 mb-4 flex items-center gap-2'>\n"
                            f"      <span>🧭</span> Synthesized App Screens\n"
                            f"    </h2>\n"
                            f"    \n"
                            f"    <div className='grid grid-cols-1 md:grid-cols-2 gap-4 mb-8'>\n"
                            f"{links_jsx}\n"
                            f"    </div>\n"
                            f"    \n"
                            f"    <div className='border-t border-slate-800/80 pt-6 text-xs text-slate-500 flex justify-between items-center'>\n"
                            f"      <span>Status: Active & Hydrated</span>\n"
                            f"      <span>V4 Cognitive Engine</span>\n"
                            f"    </div>\n"
                            f"  </div>\n"
                            f"</div>"
                        )
                    else:
                        jsx_payload = (
                            f"<div className='p-6 bg-slate-900 text-white rounded-lg shadow-xl'>\n"
                            f"  <h1 className='text-2xl font-bold mb-4'>{comp_name} View</h1>\n"
                            f"  <div className='text-sm text-slate-400'>Features: {', '.join(features)}</div>\n"
                            f"  {{loading && <p className='text-cyan-400 mt-2'>Loading active stream...</p>}}\n"
                            f"</div>"
                        )
                else:
                    jsx_payload = (
                        f"<div className='p-6 bg-slate-900 text-white rounded-lg shadow-xl'>\n"
                        f"  <h1 className='text-2xl font-bold mb-4'>{comp_name} View</h1>\n"
                        f"  <div className='text-sm text-slate-400'>Features: {', '.join(features)}</div>\n"
                        f"  {{loading && <p className='text-cyan-400 mt-2'>Loading active stream...</p>}}\n"
                        f"</div>"
                    )

                react_comp = ASTReactComponent(
                    name=comp_name,
                    state=["data", "loading"],
                    hooks=fetch_hooks if fetch_hooks else ["// No active route bindings"],
                    jsx=jsx_payload
                )
                ast_files[path].components.append(react_comp)
                ast_files[path].imports.append(ASTImport(source="react", symbols=["useState", "useEffect"]))


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

        for af in ast_files.values():
            af.update_integrity()

        return ast_files

    @staticmethod
    def _generate_schema_class(node: TopologyNode) -> ASTClass:
        fields = []
        for f in node.properties.get("fields", []):
            req = f.get("required", True)
            t_str = f.get("type", "str")
            if not req and not t_str.startswith("Optional"):
                t_str = f"Optional[{t_str}]"
            
            fields.append(
                ASTField(
                    name=f["name"],
                    type_str=t_str,
                    required=req,
                    default=None if req else "None",
                    description=f.get("description")
                )
            )
        
        return ASTClass(
            name=node.properties.get("entity_name", "Model"),
            bases=["Document"],
            fields=fields
        )

    @staticmethod
    def _generate_api_route(endpoint: Dict[str, Any], entity_name: str) -> ASTRoute:
        path = endpoint["path"]
        method = endpoint["method"].upper()
        handler_name = f"{method.lower()}_{path.replace('/', '_').replace('{', '').replace('}', '').strip('_')}"
        
        args = []
        body = []
        response_model = None
        
        # Enforce highly strict LLVM-style deterministic CRUD templates
        is_item_path = "{id}" in path or "{key}" in path or "{uid}" in path
        param_name = "id"
        if "{key}" in path:
            param_name = "key"
        elif "{uid}" in path:
            param_name = "uid"

        if not entity_name or entity_name == "Model":
            body = [
                f"# Realized API Handler for {method} {path}",
                "return {'status': 'success', 'data': []}"
            ]
        else:
            if method == "POST":
                if is_item_path:
                    args = [f"{param_name}: str", f"payload: {entity_name}"]
                    body = [
                        f"item = await {entity_name}.get({param_name})",
                        "if not item:",
                        "    raise HTTPException(status_code=404, detail='Not found')",
                        "return {'status': 'success'}"
                    ]
                else:
                    args = [f"payload: {entity_name}"]
                    body = [
                        "await payload.insert()",
                        "return payload"
                    ]
                    response_model = entity_name
            elif method == "GET":
                if is_item_path:
                    args = [f"{param_name}: str"]
                    body = [
                        f"item = await {entity_name}.get({param_name})",
                        "if not item:",
                        "    raise HTTPException(status_code=404, detail='Resource not found')",
                        "return item"
                    ]
                    response_model = entity_name
                else:
                    args = []
                    body = [
                        f"return await {entity_name}.find_all().to_list()"
                    ]
                    response_model = f"List[{entity_name}]"
            elif method in ("PUT", "PATCH"):
                args = [f"{param_name}: str", f"payload: {entity_name}"]
                body = [
                    f"item = await {entity_name}.get({param_name})",
                    "if not item:",
                    "    raise HTTPException(status_code=404, detail='Resource not found')",
                    "await item.update({\"$set\": payload.model_dump(exclude_unset=True)})",
                    "return item"
                ]
                response_model = entity_name
            elif method == "DELETE":
                args = [f"{param_name}: str"]
                body = [
                    f"item = await {entity_name}.get({param_name})",
                    "if not item:",
                    "    raise HTTPException(status_code=404, detail='Resource not found')",
                    "await item.delete()",
                    "return {'status': 'success'}"
                ]

        return ASTRoute(
            path=path,
            method=method,
            handler_name=handler_name,
            args=args,
            body=body,
            response_model=response_model
        )
