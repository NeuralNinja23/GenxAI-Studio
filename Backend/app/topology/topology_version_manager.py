# app/topology/topology_version_manager.py
"""
V4 Topological Lineage Tracking — Stage 2: Canonical Topology Engine

Manages versioned graph snapshots, branch tracking, ancestry trees,
and rollback genealogy to establish persistent cognitive continuity.
"""

from datetime import datetime
from typing import Dict, List, Optional
from beanie import Document, Indexed
from pydantic import Field
import uuid

from app.core.time import utc_now

from app.topology.project_graph import ProjectTopologyGraph

# ─────────────────────────────────────────────────────────────
# 1. Beanie Persistence Model for Version Lineage
# ─────────────────────────────────────────────────────────────

class TopologyVersionRecord(Document):
    """
    Persistent topological branch and ancestry record.
    Tracks cognitive genealogy and structural ancestry.
    """
    version_id: Indexed(str, unique=True)
    project_id: Indexed(str)
    branch_name: Indexed(str)
    parent_ids: List[str] = Field(default_factory=list)
    graph_hash: str
    serialized_graph: Dict = Field(default_factory=dict)
    
    author: str = "kernel"  # "Derek", "Victoria", "kernel"
    created_at: datetime = Field(default_factory=utc_now)
    metadata: Dict = Field(default_factory=dict)

    class Settings:
        name = "topology_versions"


# ─────────────────────────────────────────────────────────────
# 2. Version Manager Engine
# ─────────────────────────────────────────────────────────────

class TopologyVersionManager:
    """
    Lineage tracking engine for topological universes.
    Supports branching, committing new topologies, and rollback.
    """

    @staticmethod
    async def commit_topology(
        project_id: str,
        graph: ProjectTopologyGraph,
        branch_name: str = "main",
        author: str = "kernel",
        metadata: Optional[Dict] = None
    ) -> TopologyVersionRecord:
        """
        Record a new structural graph state into the topological lineage registry.
        Automatically infers the parent version from the current branch head.
        """
        graph.update_graph_hash()
        
        # Find current branch head to set as parent
        parent_version = await TopologyVersionRecord.find_one({
            "project_id": project_id,
            "branch_name": branch_name
        }, sort=[("-created_at", 1)])
        
        parent_ids = [parent_version.version_id] if parent_version else []
        version_id = str(uuid.uuid4())

        record = TopologyVersionRecord(
            version_id=version_id,
            project_id=project_id,
            branch_name=branch_name,
            parent_ids=parent_ids,
            graph_hash=graph.graph_hash,
            serialized_graph=graph.serialize(),
            author=author,
            metadata=metadata or {}
        )
        await record.insert()
        return record

    @staticmethod
    async def get_active_topology(project_id: str, branch_name: str = "main") -> Optional[ProjectTopologyGraph]:
        """Fetch the latest topology graph of the given branch."""
        record = await TopologyVersionRecord.find_one({
            "project_id": project_id,
            "branch_name": branch_name
        }, sort=[("-created_at", 1)])
        if not record:
            return None
        return ProjectTopologyGraph.deserialize(record.serialized_graph)

    @staticmethod
    async def get_version_by_id(version_id: str) -> Optional[ProjectTopologyGraph]:
        """Fetch a specific historical topology by version UUID."""
        record = await TopologyVersionRecord.find_one({
            "version_id": version_id
        })
        if not record:
            return None
        return ProjectTopologyGraph.deserialize(record.serialized_graph)

    @staticmethod
    async def get_ancestry_tree(project_id: str) -> List[Dict]:
        """Return a chronological tree representation of structural mutations."""
        records = await TopologyVersionRecord.find(
            {"project_id": project_id},
            sort=[("created_at", 1)]
        ).to_list()
        
        tree = []
        for r in records:
            tree.append({
                "version_id": r.version_id,
                "branch": r.branch_name,
                "parents": r.parent_ids,
                "hash": r.graph_hash,
                "author": r.author,
                "timestamp": r.created_at.isoformat()
            })
        return tree

    @staticmethod
    async def rollback_to_version(project_id: str, target_version_id: str, branch_name: str = "main") -> ProjectTopologyGraph:
        """
        Roll back branch head to a historical version.
        Appends a rollback record to preserve genealogical continuity.
        """
        historical_graph = await TopologyVersionManager.get_version_by_id(target_version_id)
        if not historical_graph:
            raise ValueError(f"Historical topology version '{target_version_id}' not found.")

        # Create rollback commit
        await TopologyVersionManager.commit_topology(
            project_id=project_id,
            graph=historical_graph,
            branch_name=branch_name,
            author="kernel",
            metadata={"rollback_target": target_version_id, "rollback_reason": "Manual rollback request"}
        )
        return historical_graph
