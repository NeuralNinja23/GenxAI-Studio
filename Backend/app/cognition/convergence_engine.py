# app/cognition/convergence_engine.py
"""
V4 Bounded Cognition — Stage 6: Minimal Cognition
Implements the ConvergenceEngine, measuring structural stabilization and topological entropy.
"""

import math
from collections import Counter
from typing import List
from app.topology.project_graph import ProjectTopologyGraph

class ConvergenceEngine:
    """
    Measures structural equilibrium and stability slopes in active branches.
    Enables stable freezing and pruning signals without semantic interpretation.
    """

    @staticmethod
    def calculate_entropy(graph: ProjectTopologyGraph) -> float:
        """
        Calculate structural entropy of the topology graph based on node type distributions.
        $$H(G) = -\\sum_{i} p_i \\log_2(p_i)$$
        """
        if not graph.nodes:
            return 0.0

        node_types = [node.node_type.value for node in graph.nodes.values()]
        counts = Counter(node_types)
        total = len(node_types)

        entropy = 0.0
        for count in counts.values():
            p = count / total
            entropy -= p * math.log2(p)

        # Include edge density contribution to distinguish graphs with identical node counts but different relations
        edge_total = len(graph.edges)
        if edge_total > 0:
            # Normalized edge ratio contribution
            edge_ratio = edge_total / (total * total)
            entropy += (edge_ratio * 0.1)

        return float(entropy)

    @staticmethod
    def calculate_slope(entropy_history: List[float]) -> float:
        """
        Calculate the delta change in structural entropy:
        $$\\Delta L = L_t - L_{t-1}$$
        """
        if len(entropy_history) < 2:
            return 0.0
        return float(entropy_history[-1] - entropy_history[-2])

    @staticmethod
    def is_stagnant(entropy_history: List[float], consecutive_threshold: int = 3, tolerance: float = 1e-4) -> bool:
        """
        Detects if mutation entropy changes have flatlined (stagnated).
        """
        if len(entropy_history) < consecutive_threshold:
            return False

        last_elements = entropy_history[-consecutive_threshold:]
        first = last_elements[0]
        return all(abs(x - first) <= tolerance for x in last_elements)

    @staticmethod
    def is_converged(entropy_history: List[float], tolerance: float = 1e-4) -> bool:
        """
        Check if the structural graph has reached stable convergence (zero change in last turn).
        """
        if len(entropy_history) < 2:
            return False
        return abs(entropy_history[-1] - entropy_history[-2]) <= tolerance
