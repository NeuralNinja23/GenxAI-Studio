# app/cognition/sentinel_core.py
"""
V4 Bounded Cognition — Stage 6: Minimal Cognition
Implements SentinelCore, the cognitive navigation layer.
Coordinates branch tree search, constraint checks, repulsion vector evaluation, and attention routing.
"""

from typing import Dict, List, Tuple, Optional, Any
import traceback
import numpy as np
from app.sentinel.cognition.branch import BranchState, BranchTreeManager
from app.sentinel.cognition.patch_ir import PatchIR
from app.sentinel.cognition.constraint_engine import ConstraintEngine
from app.sentinel.cognition.convergence_engine import ConvergenceEngine
from app.sentinel.cognition.attention_router import AttentionRouter
from app.sentinel.topology.topology_compression import TopologyCompressor
from app.sentinel.topology.project_graph import ProjectTopologyGraph
from app.sentinel.topology.node_types import NodeType
from app.sentinel.directives import IntentField
from app.core.logging import log
from app.sentinel.failure_memory.failure_recorder import record_failure, FailureType, Severity

class SentinelCore:
    """
    Cognitive Navigation Layer.
    Orchestrates candidate graph traversal without direct write/reality authority.
    """

    def __init__(self, max_branches: int = 5):
        self.tree_manager = BranchTreeManager()
        self.attention_router = AttentionRouter(max_branches)

    def initialize_root(self, root_graph: ProjectTopologyGraph) -> BranchState:
        """Initialize the root branch of the search tree."""
        # Clean existing tree
        self.tree_manager = BranchTreeManager()
        root = BranchState(
            branch_id="root",
            topology_graph=root_graph
        )
        entropy = ConvergenceEngine.calculate_entropy(root_graph)
        root.entropy_history.append(entropy)
        self.tree_manager.active_branches[root.branch_id] = root
        return root

    def explore_possibilities(
        self,
        intent: IntentField,
        proposals: List[PatchIR],
        marcus_advisory_modifiers: Optional[Dict[str, float]] = None
    ) -> List[BranchState]:
        """
        Takes candidate topological mutation proposals (PatchIR) and explores them in parallel branch states.
        Applies constraint filters, computes failure repulsion vectors, updates entropy, and routes attention.
        """
        active_list = list(self.tree_manager.active_branches.values())
        if not active_list:
            raise ValueError("No active branches in the tree. Initialize the root first.")

        # Source parent branch is the currently highest ranked active branch
        # Sort current active list by weight
        self.attention_router.route_attention(active_list, marcus_advisory_modifiers)
        parent = active_list[0]

        new_children = []
        valid_patches = []

        # [INSTRUMENT-B] Count UI-type patches entering the exploration pipeline
        ui_type_proposals = [p for p in proposals if p.node_data and str(p.node_data.get("node_type", "")).upper() == "UI_NODE"]
        log("COGNITION", f"[SENTINEL-INSTRUMENT-B] total_proposals={len(proposals)} | ui_node_proposals={len(ui_type_proposals)}")

        for patch in proposals:
            # 1. Enforce laws of physics (ConstraintEngine)
            validation = ConstraintEngine.validate_mutation(patch, intent)
            if not validation.passed:
                # Discard proposed branch path
                continue
            valid_patches.append(patch)

            # 2. Spawn isolated candidate universe
            child = self.tree_manager.spawn_branch(parent, patch)

            # NOTE: Compression is intentionally NOT run per-branch here.
            # Individual patch branches are temporary candidates evaluated for entropy/cycle checks.
            # Compression runs once on the composite branch after all patches are merged.

            # 3. Calculate new topological entropy
            child_entropy = ConvergenceEngine.calculate_entropy(child.topology_graph)
            child.entropy_history.append(child_entropy)

            # 4. Encode state features to calculate failure memory repulsion vector
            node_count = len(child.topology_graph.nodes)
            edge_count = len(child.topology_graph.edges)

            # [VERIFY-2] Is the failure_memory DB actually receiving writes?
            # [VERIFY-3] Is RepulsionEngine ever queried on the read path?
            # Run these once per explore_possibilities call (not per-branch) using a sentinel.
            if not getattr(self, '_verify_ran_this_cycle', False):
                self._verify_ran_this_cycle = True
                try:
                    import sqlite3, os
                    _db_candidates = [
                        os.path.join(os.getcwd(), "data", "memory.sqlite"),
                        os.path.join(os.getcwd(), "app", "sentinel", "failure_memory", "sentinel_memory.db"),
                    ]
                    for _db_path in _db_candidates:
                        if os.path.exists(_db_path):
                            _conn = sqlite3.connect(_db_path)
                            _cur = _conn.cursor()
                            _cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
                            _tables = [r[0] for r in _cur.fetchall()]
                            for _t in _tables:
                                _cur.execute(f"SELECT COUNT(*) FROM {_t}")
                                _cnt = _cur.fetchone()[0]
                                log("COGNITION", f"[VERIFY-2] DB={_db_path} table={_t} rows={_cnt}")
                            _conn.close()
                        else:
                            log("COGNITION", f"[VERIFY-2] DB not found at {_db_path}")
                except Exception as _ve:
                    log("COGNITION", f"[VERIFY-2] DB audit error: {_ve}")

                # [VERIFY-3] Read path: is RepulsionEngine ever instantiated or queried?
                # Simulate what SHOULD happen — encode a dummy candidate and score it.
                try:
                    from app.sentinel.failure_memory.failure_geometry import FailureGeometry
                    from app.sentinel.failure_memory.repulsion_engine import RepulsionEngine
                    import numpy as np
                    _dummy_db = os.path.join(os.getcwd(), "data", "memory.sqlite")
                    _fg = FailureGeometry(_dummy_db)  # connects to existing DB
                    _re = RepulsionEngine(_fg)
                    _dummy_vec = FailureGeometry.encode_failure(
                        node_count=node_count, edge_count=edge_count,
                        is_cyclic=False, error_class=""
                    )
                    _score = _re.get_repulsion_score(_dummy_vec)
                    log("COGNITION", (
                        f"[VERIFY-3] RepulsionEngine read path WORKS. "
                        f"Queried DB with candidate vec. "
                        f"repulsion_score_from_db={_score:.4f} "
                        f"(0.0 = DB is empty / no prior failures recorded)"
                    ))
                except Exception as _re_err:
                    log("COGNITION", f"[VERIFY-3] RepulsionEngine read path ERROR: {_re_err}")


            has_cycles = False
            try:
                adj = child.topology_graph.get_dependencies_dag()
                visited = set()
                rec_stack = set()
                def is_cyclic(v):
                    visited.add(v)
                    rec_stack.add(v)
                    for neighbour in adj.get(v, []):
                        if neighbour not in visited:
                            if is_cyclic(neighbour):
                                return True
                        elif neighbour in rec_stack:
                            return True
                    rec_stack.remove(v)
                    return False
                for node in child.topology_graph.nodes:
                    if node not in visited:
                        if is_cyclic(node):
                            has_cycles = True
                            break
            except Exception as cycle_err:
                # Phase 9: Full traceback instead of silent swallow
                log(
                    "COGNITION",
                    f"⚠️ Cycle detection failed for branch '{child.branch_id}': "
                    f"{type(cycle_err).__name__}: {cycle_err}\n"
                    f"{traceback.format_exc()}"
                )
                has_cycles = True

            # Auto-classify and normalize STATE_NODEs to UI_STATE_NODE/DATA_STATE_NODE
            self._normalize_and_classify_state_nodes(child.topology_graph)
            from app.sentinel.topology.topology_compiler import TopologyCompiler
            TopologyCompiler._ensure_schema_grounding(child.topology_graph)
            TopologyCompiler._ensure_data_state_grounding(child.topology_graph)



            api_count = sum(1 for n in child.topology_graph.nodes.values() if n.node_type.value == "API_NODE")

            ui_count = sum(1 for n in child.topology_graph.nodes.values() if n.node_type.value == "UI_NODE")
            schema_count = sum(1 for n in child.topology_graph.nodes.values() if n.node_type.value == "SCHEMA_NODE")

            if has_cycles:
                # Phase 3: HARD Rules - Prune instantly
                self.tree_manager.prune_branch(child.branch_id, "Failure Topology Cycle.")
                # ── Phase 6A: Record cyclic branch prune ────────────────────────
                record_failure(
                    FailureType.BRANCH_PRUNED,
                    Severity.INFO,
                    f"Cyclic dependency detected in branch '{child.branch_id}'. Pruned.",
                    branch_id=child.branch_id,
                    component=patch.target_node_id,
                    node_type=str(patch.node_data.get("node_type", "UNKNOWN")) if patch.node_data else "UNKNOWN",
                    ui_nodes=ui_count,
                    api_nodes=api_count,
                    entropy=child.entropy_history[-1] if child.entropy_history else 0.0,
                )
                continue

            # Phase 3: SOFT Rules - Bypass pruning and route to Stabilization
            soft_violations = []
            if ui_count > 15:
                soft_violations.append("High UI Density (UI count > 15)")
            if node_count > 0 and edge_count > node_count * 3:
                soft_violations.append("High Edge Density (Fan-out > 3x)")

            if soft_violations:
                log("COGNITION", f"⚠️ Branch {child.branch_id} violated SOFT constraints: {soft_violations}. Routing to Stabilization.")
                child.needs_stabilization = True

            new_children.append(child)

        # 5. Spawn unified/composite candidate universe combining ALL valid proposals
        if len(valid_patches) > 1:
            from app.models.runtime_models import MutationTier
            composite_child = self.tree_manager.spawn_branch(parent, patch=None)
            
            for patch in valid_patches:
                action = patch.action.upper()
                target = patch.target_node_id
                cloned_graph = composite_child.topology_graph

                if action == "ADD_NODE":
                    node_type_str = str(patch.node_data.get("node_type", "AST_NODE")).strip().upper()
                    try:
                        node_type = NodeType(node_type_str)
                    except ValueError:
                        node_type = NodeType.AST_NODE
                    cloned_graph.add_node(
                        node_id=target,
                        node_type=node_type,
                        properties=patch.node_data.get("properties", {})
                    )

                elif action in ("REMOVE_NODE", "DELETE_NODE"):
                    cloned_graph.remove_node(target)

                elif action in ("UPDATE_NODE", "MODIFY_NODE"):
                    node = cloned_graph.get_node(target)
                    if node:
                        props = patch.node_data.get("properties", {})
                        node.properties.update(props)
                        node.update_integrity()
                        cloned_graph.update_graph_hash()

                elif action == "ADD_EDGE":
                    source = patch.edge_data.get("source")
                    target_edge = patch.edge_data.get("target")
                    relation = patch.edge_data.get("relation", "imports")
                    if source and target_edge:
                        cloned_graph.add_edge(
                            source_id=source,
                            target_id=target_edge,
                            relation=relation,
                            properties=patch.edge_data.get("properties", {})
                        )

                elif action in ("REMOVE_EDGE", "DELETE_EDGE"):
                    source = patch.edge_data.get("source")
                    target_edge = patch.edge_data.get("target")
                    relation = patch.edge_data.get("relation", "imports")
                    if source and target_edge:
                        cloned_graph.remove_edge(source, target_edge, relation)

            # Automatically ground renderable UI nodes to state nodes, schema nodes to service nodes, and data states to APIs
            from app.sentinel.topology.topology_compiler import TopologyCompiler

            # Phase 4: Meaning-Aware Topology Compression — runs ONCE on the composite
            # after all patches are merged, not per-branch on throwaway candidates.
            composite_child.topology_graph = TopologyCompressor.compress_topology(composite_child.topology_graph)

            # [INSTRUMENT-C-PRE] Count UI nodes in composite graph BEFORE grounding
            ui_pre = sum(1 for n in composite_child.topology_graph.nodes.values() if n.node_type.value == "UI_NODE")
            log("COGNITION", f"[SENTINEL-INSTRUMENT-C] ui_nodes_before_grounding={ui_pre} | total_nodes={len(composite_child.topology_graph.nodes)}")

            TopologyCompiler._ensure_renderable_grounding(composite_child.topology_graph)
            TopologyCompiler._ensure_schema_grounding(composite_child.topology_graph)
            TopologyCompiler._ensure_data_state_grounding(composite_child.topology_graph)

            # [INSTRUMENT-C-POST] Count UI nodes AFTER grounding to see if grounding destroys any
            ui_post = sum(1 for n in composite_child.topology_graph.nodes.values() if n.node_type.value == "UI_NODE")
            log("COGNITION", f"[SENTINEL-INSTRUMENT-C] ui_nodes_after_grounding={ui_post} | delta={ui_post - ui_pre}")



            # Update composite branch's hash and entropy
            composite_child.topology_graph.update_graph_hash()
            comp_entropy = ConvergenceEngine.calculate_entropy(composite_child.topology_graph)
            composite_child.entropy_history.append(comp_entropy)
            
            # Cycle check for composite
            has_cycles = False
            try:
                adj = composite_child.topology_graph.get_dependencies_dag()
                visited = set()
                rec_stack = set()
                def is_cyclic(v):
                    visited.add(v)
                    rec_stack.add(v)
                    for neighbour in adj.get(v, []):
                        if neighbour not in visited:
                            if is_cyclic(neighbour):
                                return True
                        elif neighbour in rec_stack:
                            return True
                    rec_stack.remove(v)
                    return False
                for node in composite_child.topology_graph.nodes:
                    if node not in visited:
                        if is_cyclic(node):
                            has_cycles = True
                            break
            except Exception as cycle_err:
                # Phase 9: Full traceback instead of silent swallow
                log(
                    "COGNITION",
                    f"⚠️ Cycle detection failed for composite branch: "
                    f"{type(cycle_err).__name__}: {cycle_err}\n"
                    f"{traceback.format_exc()}"
                )
                has_cycles = True

            # Auto-classify and normalize STATE_NODEs to UI_STATE_NODE/DATA_STATE_NODE
            self._normalize_and_classify_state_nodes(composite_child.topology_graph)

            api_count = sum(1 for n in composite_child.topology_graph.nodes.values() if n.node_type.value == "API_NODE")

            ui_count = sum(1 for n in composite_child.topology_graph.nodes.values() if n.node_type.value == "UI_NODE")
            schema_count = sum(1 for n in composite_child.topology_graph.nodes.values() if n.node_type.value == "SCHEMA_NODE")

            if not has_cycles:
                # Remove randomly generated ID from active branches and register with "composite" ID
                if composite_child.branch_id in self.tree_manager.active_branches:
                    del self.tree_manager.active_branches[composite_child.branch_id]
                composite_child.branch_id = "composite"
                self.tree_manager.active_branches[composite_child.branch_id] = composite_child
                new_children.append(composite_child)

        # 6. Route attention and prune excess branches based on budget
        all_active = list(self.tree_manager.active_branches.values())
        kept, pruned = self.attention_router.prune_to_budget(all_active, marcus_advisory_modifiers)

        for p in pruned:
            # Never prune the root baseline or the fully compiled composite child branch
            if p.branch_id in ["root", "composite"]:
                if p not in kept:
                    kept.append(p)
                continue
            self.tree_manager.prune_branch(p.branch_id, "Budget capacity limit exceeded.")

        # ── Phase 9: Emit branch-level metrics ────────────────
        try:
            from app.sentinel.topology.projection_metrics import ProjectionMetrics
            metrics = ProjectionMetrics.get_instance()
            metrics.set_branch_density(len(kept))
            for branch in kept:
                if branch.entropy_history:
                    metrics.record_branch_entropy(
                        branch.branch_id, branch.entropy_history[-1]
                    )
        except Exception:
            pass  # Metrics are best-effort; never block cognition

        return kept

    def _normalize_and_classify_state_nodes(self, graph: ProjectTopologyGraph):
        """
        Intelligently auto-classifies proposed generic STATE_NODEs into either
        UI_STATE_NODEs or DATA_STATE_NODEs based on semantic naming and routing.
        """
        for node_id, node in graph.nodes.items():
            if node.node_type == NodeType.STATE_NODE:
                name_lower = node_id.lower()
                is_local_ui = any(kw in name_lower for kw in ["ui", "modal", "editor", "sidebar", "header", "search", "button", "filter", "layout"])
                if is_local_ui:
                    node.node_type = NodeType.UI_STATE_NODE
                else:
                    outgoing_edges = graph.get_outgoing_edges(node_id)
                    has_api_call = any(
                        e.relation == "calls_api" and graph.nodes[e.target_id].node_type == NodeType.API_NODE
                        for e in outgoing_edges
                    )
                    if has_api_call:
                        node.node_type = NodeType.DATA_STATE_NODE
                    else:
                        node.node_type = NodeType.DATA_STATE_NODE


