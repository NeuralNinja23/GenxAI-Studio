# app/sentinel/failure_memory/failure_geometry.py
import sqlite3
import json
import numpy as np

class FailureGeometry:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS failure_memory (
                    failure_id TEXT PRIMARY KEY,
                    vector TEXT NOT NULL,
                    error_class TEXT,
                    cycle_id TEXT,
                    details TEXT
                )
            """)
            conn.commit()

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
        if is_cyclic:
            structural_instability += 2.0
        if error_class == "topology":
            structural_instability += 0.5
        if mutation_tier >= 4:
            structural_instability += 0.3

        # visual_density (tuned parameter weight of 0.25)
        # Visual density raw: ui_node_count relative to total nodes, scaled by 0.25 weight
        total_nodes = max(1, node_count)
        visual_density_raw = ui_node_count / total_nodes
        visual_density = 0.25 * visual_density_raw

        # semantic_incoherence
        semantic_incoherence = (api_node_count + schema_node_count) / total_nodes
        if error_class in ("semantic", "conflict"):
            semantic_incoherence += 0.5

        # runtime_instability
        runtime_instability = mutation_tier / 5.0
        if error_class == "runtime":
            runtime_instability += 0.5

        # ux_entropy
        ux_entropy = min(1.0, error_len / 1000.0)

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
        details: str = ""
    ):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO failure_memory (failure_id, vector, error_class, cycle_id, details) VALUES (?, ?, ?, ?, ?)",
                (failure_id, json.dumps(vector.tolist()), error_class, cycle_id, details)
            )
            conn.commit()

    def get_all_failures(self) -> list:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT failure_id, vector, error_class, cycle_id, details FROM failure_memory")
            rows = cursor.fetchall()
            res = []
            for row in rows:
                f_id, vec_str, err_class, cyc_id, details = row
                vec = np.array(json.loads(vec_str), dtype=float)
                res.append((f_id, vec, err_class, cyc_id, details))
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

