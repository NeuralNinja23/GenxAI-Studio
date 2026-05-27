# app/topology/topology_builder.py
"""
V4 Topology Reconstruction System — Stage 2: Canonical Topology Engine

Rebuilds ProjectTopologyGraph using an AST-first, topology-first paradigm,
relying on physical filesystem scanning only as a secondary fallback.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Any, Optional

from app.core.logging import log
from app.topology.node_types import NodeType
from app.topology.project_graph import ProjectTopologyGraph

class TopologyBuilder:
    """
    AST-First & Topology-First Reconstruction Engine.
    Corrects V3's filesystem-first assumptions by asserting:
    1. Active AST projection manifest is the preferred source of truth.
    2. Filesystem scanning is used only as a last-resort fallback reconciliation.
    """

    @classmethod
    async def reconstruct(cls, project_id: str, project_path: Path) -> ProjectTopologyGraph:
        """
        Reconstruct the ProjectTopologyGraph.
        Loads from AST manifest first, with filesystem fallback.
        """
        ast_manifest_path = project_path / ".genx_ast_manifest.json"

        # ── 1. AST-First: Check for AST Projection Manifest ──
        if ast_manifest_path.exists():
            try:
                log("TOPOLOGY", f"📖 Loading topology from AST Manifest: {ast_manifest_path}")
                with open(ast_manifest_path, "r", encoding="utf-8") as f:
                    serialized_data = json.load(f)
                
                # Reconstruct graph from serialized projection
                graph = ProjectTopologyGraph.deserialize(serialized_data.get("topology", {}))
                log("TOPOLOGY", f"✅ AST-First topology restoration success: {graph.graph_hash[:8]}...")
                return graph
            except Exception as e:
                log("TOPOLOGY", f"⚠️ Failed to parse AST manifest: {e}. Falling back to filesystem scanner.")

        # ── 2. Filesystem-Last Fallback Reconciliation ────────
        log("TOPOLOGY", f"🔍 Filesystem-Last Fallback Reconstruction active for path: {project_path}")
        graph = ProjectTopologyGraph(project_id=project_id, version=1)

        # Scan Backend
        backend_dir = project_path / "Backend" / "app"
        if backend_dir.exists():
            cls._scan_backend(graph, backend_dir)

        # Scan Frontend
        frontend_dir = project_path / "Frontend" / "src"
        if frontend_dir.exists():
            cls._scan_frontend(graph, frontend_dir)

        # Establish dependency/import edges by scanning import statements
        cls._resolve_import_edges(graph, project_path)

        graph.update_graph_hash()
        
        # Write back a clean AST manifest to stabilize the system
        try:
            manifest_payload = {
                "project_id": project_id,
                "reconstructed_at": os.environ.get("CURRENT_TIME", ""),
                "topology": graph.serialize()
            }
            with open(ast_manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest_payload, f, indent=2)
            log("TOPOLOGY", f"📝 Re-established AST manifest boundary at: {ast_manifest_path}")
        except Exception as write_err:
            log("TOPOLOGY", f"⚠️ Could not write stabilized AST manifest: {write_err}")

        return graph

    @classmethod
    def _scan_backend(cls, graph: ProjectTopologyGraph, backend_dir: Path) -> None:
        """Scan Python modules for schemas, APIs, and services."""
        models_dir = backend_dir / "models"
        if models_dir.exists():
            for p in models_dir.glob("**/*.py"):
                if p.name == "__init__.py":
                    continue
                node_id = f"schema_{p.stem.lower()}"
                graph.add_node(
                    node_id=node_id,
                    node_type=NodeType.SCHEMA_NODE,
                    properties={"file_path": str(p.relative_to(backend_dir.parent.parent)), "entity_name": p.stem}
                )

        api_dir = backend_dir / "api"
        if api_dir.exists():
            for p in api_dir.glob("**/*.py"):
                if p.name == "__init__.py":
                    continue
                node_id = f"api_{p.stem.lower()}"
                graph.add_node(
                    node_id=node_id,
                    node_type=NodeType.API_NODE,
                    properties={"file_path": str(p.relative_to(backend_dir.parent.parent))}
                )
                
                # Invert route nodes from API router naming conventions
                route_id = f"route_{p.stem.lower()}"
                graph.add_node(
                    node_id=route_id,
                    node_type=NodeType.ROUTE_NODE,
                    properties={"base_path": f"/api/v1/{p.stem.lower()}"}
                )
                graph.add_edge(source_id=route_id, target_id=node_id, relation="routes_to")

        services_dir = backend_dir / "services"
        if services_dir.exists():
            for p in services_dir.glob("**/*.py"):
                if p.name == "__init__.py":
                    continue
                node_id = f"service_{p.stem.lower()}"
                graph.add_node(
                    node_id=node_id,
                    node_type=NodeType.SERVICE_NODE,
                    properties={"file_path": str(p.relative_to(backend_dir.parent.parent))}
                )

    @classmethod
    def _scan_frontend(cls, graph: ProjectTopologyGraph, frontend_dir: Path) -> None:
        """Scan UI layouts, components, and state modules."""
        components_dir = frontend_dir / "components"
        if components_dir.exists():
            for p in components_dir.glob("**/*.tsx"):
                node_id = f"ui_component_{p.stem.lower()}"
                graph.add_node(
                    node_id=node_id,
                    node_type=NodeType.UI_NODE,
                    properties={"file_path": str(p.relative_to(frontend_dir.parent.parent))}
                )

        store_dir = frontend_dir / "store"
        if store_dir.exists():
            for p in store_dir.glob("**/*.ts"):
                node_id = f"state_{p.stem.lower()}"
                graph.add_node(
                    node_id=node_id,
                    node_type=NodeType.STATE_NODE,
                    properties={"file_path": str(p.relative_to(frontend_dir.parent.parent))}
                )

    @classmethod
    def _resolve_import_edges(cls, graph: ProjectTopologyGraph, project_path: Path) -> None:
        """Parse source code import structures to construct logical dependency edges."""
        # Walk and extract import relationships to build DAG edges
        for node_id, node in list(graph.nodes.items()):
            rel_path = node.properties.get("file_path")
            if not rel_path:
                continue

            full_path = project_path / rel_path
            if not full_path.exists():
                continue

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Simple regex import parsing
                imports = re.findall(r"(?:import|from)\s+([a-zA-Z0-9_\.]+)", content)
                for imp in imports:
                    imp_lower = imp.split(".")[-1].lower()
                    
                    # Match against other nodes in the graph
                    for other_id, other_node in graph.nodes.items():
                        if other_id == node_id:
                            continue
                        if imp_lower in other_id:
                            # Reconstructed dependency relationship
                            graph.add_edge(source_id=node_id, target_id=other_id, relation="imports")
            except Exception as read_err:
                log("TOPOLOGY", f"⚠️ Failed to parse imports from {rel_path}: {read_err}")
