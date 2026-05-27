# app/runtime/reconstruction.py
"""
V4 Forensic Reconstruction Engine — Stage 5: Runtime Synchronization

Performs cold disaster recovery and severe drift recovery.
Strictly non-cognitive: reconstructs the canonical topology ProjectTopologyGraph
exclusively through deterministic forensic parsing of disk manifest files,
pre-cycle snapshot JSON assets, and committed database transaction journals.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import json

from app.core.logging import log
from app.topology.project_graph import ProjectTopologyGraph
from app.topology.topology_version_manager import TopologyVersionManager
from app.models.runtime_models import RuntimeTransaction, TransactionStatus
from app.runtime.projection_snapshots import SNAPSHOT_DIR_NAME

class ReconstructionError(Exception):
    """Raised when forensic topology reconstruction fails due to lack of evidence."""


class ForensicReconstruction:
    """
    evidence-grounded non-cognitive reconstruction engine.
    """

    @classmethod
    async def reconstruct_topology(cls, project_id: str, project_path: Path) -> ProjectTopologyGraph:
        log("RECONSTRUCTION", f"🔍 Commencing forensic non-cognitive reconstruction of topology for {project_id}")

        # ── 1. Attempt manifest forensic recovery ──────────────
        manifest_path = project_path / ".genx_ast_manifest.json"
        if manifest_path.exists():
            log("RECONSTRUCTION", f"📄 Found grounding manifest at {manifest_path}. Forensic parsing initiated...")
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest_data = json.load(f)
                
                # Check for serialized topology graph inside manifest
                topology_data = manifest_data.get("topology")
                if topology_data:
                    graph = ProjectTopologyGraph.deserialize(topology_data)
                    log("RECONSTRUCTION", f"✅ Reconstructed topology from disk manifest (hash={graph.graph_hash[:12]}).")
                    await TopologyVersionManager.commit_topology(project_id, graph, author="reconstructor")
                    return graph
            except Exception as parse_err:
                log("RECONSTRUCTION", f"⚠️ Error parsing grounding manifest: {parse_err}. Continuing search...")

        # ── 2. Attempt snapshot forensic recovery ──────────────
        snapshot_root = project_path / SNAPSHOT_DIR_NAME
        if snapshot_root.exists():
            log("RECONSTRUCTION", f"📂 Found snapshots folder at {snapshot_root}. Scanning chronological traces...")
            try:
                # Find all subdirectories which are named after cycle IDs (UUIDs)
                # Sort by folder creation time to find the most recent
                snap_dirs = [d for d in snapshot_root.iterdir() if d.is_dir()]
                snap_dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)

                for cycle_dir in snap_dirs:
                    topo_file = cycle_dir / "topology.json"
                    if topo_file.exists():
                        log("RECONSTRUCTION", f"📂 Found baseline snapshot topology: {topo_file}")
                        with open(topo_file, "r", encoding="utf-8") as f:
                            topology_data = json.load(f)
                        
                        graph = ProjectTopologyGraph.deserialize(topology_data)
                        log("RECONSTRUCTION", f"✅ Reconstructed topology from snapshot directory {cycle_dir.name} (hash={graph.graph_hash[:12]}).")
                        await TopologyVersionManager.commit_topology(project_id, graph, author="reconstructor")
                        return graph
            except Exception as snap_err:
                log("RECONSTRUCTION", f"⚠️ Snapshot scanning failed: {snap_err}. Continuing recovery...")

        # ── 3. Attempt transaction journal recovery ───────────
        log("RECONSTRUCTION", "📜 Querying committed transaction logs inside database ledger...")
        try:
            latest_committed_tx = await RuntimeTransaction.find(
                {"project_id": project_id, "status": TransactionStatus.COMMITTED}
            ).sort(-RuntimeTransaction.committed_at).to_list(1)

            if latest_committed_tx:
                # Retrieve the transaction details and baseline topology snapshot mapping
                tx = latest_committed_tx[0]
                log("RECONSTRUCTION", f"📄 Found committed transaction journal: {tx.tx_id[:8]} (snapshot={tx.snapshot_id[:8]})")
                
                # Fetch baseline projection snapshot
                from app.models.runtime_models import ProjectionSnapshot
                snapshot = await ProjectionSnapshot.find_one({"snapshot_id": tx.snapshot_id})
                if snapshot and snapshot.topology_snapshot_path:
                    topo_path = Path(snapshot.topology_snapshot_path)
                    if topo_path.exists():
                        with open(topo_path, "r", encoding="utf-8") as f:
                            topology_data = json.load(f)
                        
                        graph = ProjectTopologyGraph.deserialize(topology_data)
                        log("RECONSTRUCTION", f"✅ Reconstructed topology from journal snapshot reference (hash={graph.graph_hash[:12]}).")
                        await TopologyVersionManager.commit_topology(project_id, graph, author="reconstructor")
                        return graph
        except Exception as tx_err:
            log("RECONSTRUCTION", f"⚠️ Transaction journal recovery failed: {tx_err}")

        # ── 4. Final Fallback: Reconstruct baseline from directory structure ──
        log("RECONSTRUCTION", "⚠️ Severe drift: No manifest, snapshots, or transaction evidence remains. Initializing empty baseline ProjectTopologyGraph.")
        fallback_graph = ProjectTopologyGraph(project_id=project_id)
        
        # Scan for physical file paths to repopulate nodes forensically
        from app.runtime.projection_snapshots import TRACKED_EXTENSIONS, EXCLUDED_DIRS
        from app.topology.node_types import NodeType
        
        for p in project_path.rglob("*"):
            if not p.is_file():
                continue
            if any(excl in p.parts for excl in EXCLUDED_DIRS):
                continue
            if p.suffix.lower() not in TRACKED_EXTENSIONS:
                continue

            rel_str = str(p.relative_to(project_path)).replace("\\", "/")
            
            # Form topological node types based on path namespaces
            if "models" in rel_str or "schemas" in rel_str:
                node_id = f"schema_{p.stem.lower()}"
                fallback_graph.add_node(node_id, NodeType.SCHEMA_NODE)
                log("RECONSTRUCTION", f"   🔧 Rebuilt schema node: {node_id} from {rel_str}")
            elif "api" in rel_str or "routers" in rel_str:
                node_id = f"api_{p.stem.lower()}"
                fallback_graph.add_node(node_id, NodeType.API_NODE)
                log("RECONSTRUCTION", f"   🔧 Rebuilt API node: {node_id} from {rel_str}")
            elif "Frontend" in rel_str:
                node_id = f"ui_{p.stem.lower()}"
                fallback_graph.add_node(node_id, NodeType.UI_NODE)
                log("RECONSTRUCTION", f"   🔧 Rebuilt UI node: {node_id} from {rel_str}")

        fallback_graph.update_graph_hash()
        await TopologyVersionManager.commit_topology(project_id, fallback_graph, author="reconstructor")
        log("RECONSTRUCTION", f"✅ Reconstructed topological framework from file directory structures (hash={fallback_graph.graph_hash[:12]})")
        return fallback_graph
