# app/sentinel/failure_memory/failure_geometry.py
"""
FailureGeometry (S-0.8)
Hardened S-0 failure coordinate encoding engine integrated with MemoryAccessLayer.
"""

import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from pathlib import Path

from app.sentinel.failure_memory.memory_access_layer import MemoryAccessLayer


class FailureGeometry:
    """
    Decoupled vector encoding and failure geometry coordinator.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.mal = MemoryAccessLayer(db_path)

    @property
    def db_path(self) -> Path:
        return self.mal.db_path

    @classmethod
    def encode_failure(
        cls,
        node_count: int = 0,
        edge_count: int = 0,
        is_cyclic: bool = False,
        error_class: str = "",
        mutation_tier: int = 1,
        error_len: int = 0,
        api_node_count: int = 0,
        ui_node_count: int = 0,
        schema_node_count: int = 0
    ) -> np.ndarray:
        # structural_instability
        structural_instability = 0.0
        if is_cyclic or error_class == "TOPOLOGY_INTEGRITY_FAILURE":
            structural_instability += 2.0
        if error_class in ("topology", "TOPOLOGY_INTEGRITY_FAILURE", "WIRING_FAILURE"):
            structural_instability += 0.5
        if mutation_tier >= 4:
            structural_instability += 0.3

        # visual_density
        total_nodes = max(1, node_count)
        visual_density_raw = ui_node_count / total_nodes
        visual_density = 0.25 * visual_density_raw
        if error_class == "VISUAL_RENDER_FAILURE":
            visual_density += 0.5

        # semantic_incoherence
        semantic_incoherence = (api_node_count + schema_node_count) / total_nodes
        if error_class in ("semantic", "conflict", "SCHEMA_CONTRACT_FAILURE", "UNRESOLVED_IMPORT_FAILURE"):
            semantic_incoherence += 0.5

        # runtime_instability
        runtime_instability = mutation_tier / 5.0
        if error_class in ("runtime", "FRONTEND_BUILD_FAILURE", "BACKEND_BUILD_FAILURE", "RUNTIME_BOOT_FAILURE", "HEALTH_CHECK_FAILURE"):
            runtime_instability += 0.5

        # ux_entropy
        ux_entropy = min(1.0, error_len / 1000.0)
        if error_class == "STATE_BINDING_FAILURE":
            ux_entropy += 0.4

        vec = np.array([
            structural_instability,
            visual_density,
            semantic_incoherence,
            runtime_instability,
            ux_entropy
        ], dtype=float)

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    @staticmethod
    def decompose_vector(vector: np.ndarray) -> dict:
        return {
            "structural_instability": float(vector[0]),
            "visual_density": float(vector[1]),
            "semantic_incoherence": float(vector[2]),
            "runtime_instability": float(vector[3]),
            "ux_entropy": float(vector[4])
        }

    def insert_failure(
        self,
        failure_id: str,
        vector: np.ndarray,
        error_class: str = "",
        cycle_id: str = "",
        details: str = "",
        verification_stage: Optional[str] = None,
        error_field: Optional[str] = None,
        error_file: Optional[str] = None,
        error_component: Optional[str] = None
    ):
        """Atomically forwards S-0 error detail profiles to MemoryAccessLayer."""
        self.mal.insert_failure_record(
            failure_id=failure_id,
            vector=vector,
            error_class=error_class,
            cycle_id=cycle_id,
            details=details,
            verification_stage=verification_stage,
            error_field=error_field,
            error_file=error_file,
            error_component=error_component
        )

    def get_all_failures(self) -> list:
        records = self.mal.load_all_records()
        res = []
        for r in records:
            # Reconstruct legacy FailureGeometry output tuple (f_id, vec, err_class, cyc_id, details)
            res.append((r[0], r[1], r[2], r[3], r[4]))
        return res


class TopologyHeatMap:
    def __init__(self, failure_geometry: FailureGeometry):
        self.failure_geometry = failure_geometry
        self.mutation_history = {}  # node_id -> {"mutations": int, "failures": int}

    def track_mutation(self, node_id: str, node_type: str, is_failure: bool = False):
        if node_id not in self.mutation_history:
            self.mutation_history[node_id] = {"mutations": 0, "failures": 0}
        self.mutation_history[node_id]["mutations"] += 1
        if is_failure:
            self.mutation_history[node_id]["failures"] += 1

    def get_heat_score(self, node_id: str) -> float:
        """Returns a normalized fragility/heat score between 0.0 and 1.0."""
        history = self.mutation_history.get(node_id)
        if not history:
            return 0.0
        failures = history["failures"]
        mutations = history["mutations"]
        if mutations == 0:
            return 0.0
        return float(failures / mutations)

    def identify_high_value_ux_zones(self, topology_graph) -> list:
        """Identifies critical UI/UX nodes that represent high-value zones."""
        high_value_nodes = []
        for node_id, node in topology_graph.nodes.items():
            is_ui = node.node_type.value == "UI_NODE"
            properties = node.properties or {}
            is_root = properties.get("is_root", False)
            comp_name = str(properties.get("component_name", "")).lower()
            
            if is_ui and (is_root or any(kw in comp_name for kw in ["dashboard", "navbar", "auth", "settings", "main"])):
                high_value_nodes.append(node_id)
        return high_value_nodes

    def get_localized_physics(self, node_type, node_id: str, base_physics) -> dict:
        """
        Dynamically adjusts DomainPhysics based on heat scores and high-value zones.
        Ensures fragile or critical UX nodes are handled with specialized tolerances.
        """
        adjusted = {
            "repulsion_threshold": base_physics.repulsion_threshold,
            "density_tolerance": base_physics.density_tolerance,
            "max_nodes_soft_cap": base_physics.max_nodes_soft_cap,
            "compression_eligible": base_physics.compression_eligible,
            "stabilization_priority": base_physics.stabilization_priority
        }

        heat = self.get_heat_score(node_id)
        
        if heat > 0.5:
            adjusted["repulsion_threshold"] = max(0.4, base_physics.repulsion_threshold - 0.15)
            adjusted["density_tolerance"] = min(0.95, base_physics.density_tolerance + 0.1)
            adjusted["stabilization_priority"] = max(1, base_physics.stabilization_priority - 1)

        return adjusted
