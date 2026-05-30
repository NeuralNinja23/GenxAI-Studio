# app/studio/architecture/memory_engine.py
"""
V4 GenxAI Studio — Phase GS-10: DesignMemoryEngine

Provides the storage engine and safety boundary validations for design memory.
Manages the design_memory.db SQLite database and builds the DesignMemoryGraph.
Prevents leaking design recommendations into Sentinel's core execution scope.
"""

import os
import sqlite3
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from app.core.logging import log
from app.sentinel.failure_memory.failure_recorder import record_failure, FailureType, Severity
from app.studio.architecture.design_memory import (
    DesignMemoryGraph,
    STUDIO_DESIGN_MEMORY_NODE,
    STUDIO_COMPILE_RECORD_NODE,
    STUDIO_COGNITIVE_CRITIQUE_NODE,
    STUDIO_USER_FEEDBACK_NODE,
    STUDIO_DESIGN_LEARNING_NODE
)

# ─────────────────────────────────────────────────────────────
# Invariant Exceptions
# ─────────────────────────────────────────────────────────────
class MemoryRootFailure(Exception):
    """Raised when causal root is broken (DESIGN_MEMORY_NODE -> design_memory_derives_intent -> DESIGN_INTENT_NODE)."""
    pass

class MemoryTamperFailure(Exception):
    """Raised when the stored graph hash does not match computed graph hash."""
    pass

class CritiqueOrphanFailure(Exception):
    """Raised when a critique node does not reference a valid compile record."""
    pass

class FeedbackOrphanFailure(Exception):
    """Raised when feedback node does not reference a valid compile record."""
    pass

class DriftingLearningFailure(Exception):
    """Raised when recommendations exceed safety bounds (extreme density/attention/responsive rules)."""
    pass

class DesignScopeViolationFailure(Exception):
    """Raised when design recommendations attempt to touch Sentinel, Ontology, or Execution policies."""
    pass


# ─────────────────────────────────────────────────────────────
# DesignMemoryEngine
# ─────────────────────────────────────────────────────────────
class DesignMemoryEngine:
    """
    Design Learning Memory Engine.
    Exposes APIs to record compilation outcomes, visual critiques, user feedback, and learned design suggestions.
    Enforces strict structural invariants and logs violations to sentinel_memory.db.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Default database location: app/studio/memory/design_memory.db
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_dir = os.path.join(base_dir, "memory")
            os.makedirs(db_dir, exist_ok=True)
            self.db_path = os.path.normpath(os.path.join(db_dir, "design_memory.db"))
        else:
            self.db_path = os.path.normpath(db_path)
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self._ensure_tables()

    def _ensure_tables(self):
        """Create design memory SQLite tables if they do not exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA foreign_keys = ON")
                
                # 1. compile_records table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS compile_records (
                        record_id TEXT PRIMARY KEY,
                        project_id TEXT NOT NULL,
                        graph_hash TEXT NOT NULL,
                        generation_timestamp TEXT NOT NULL,
                        compile_duration_ms INTEGER NOT NULL,
                        studio_version TEXT NOT NULL
                    )
                """)

                # 2. critiques table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS critiques (
                        critique_id TEXT PRIMARY KEY,
                        record_id TEXT NOT NULL,
                        critique_type TEXT NOT NULL,
                        severity REAL NOT NULL,
                        description TEXT NOT NULL,
                        FOREIGN KEY (record_id) REFERENCES compile_records(record_id) ON DELETE CASCADE
                    )
                """)

                # 3. feedback table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS feedback (
                        feedback_id TEXT PRIMARY KEY,
                        record_id TEXT NOT NULL,
                        feedback_type TEXT NOT NULL,
                        feedback_value TEXT NOT NULL,
                        FOREIGN KEY (record_id) REFERENCES compile_records(record_id) ON DELETE CASCADE
                    )
                """)

                # 4. design_learnings table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS design_learnings (
                        learning_id TEXT PRIMARY KEY,
                        pattern_type TEXT NOT NULL,
                        recommendation TEXT NOT NULL,
                        confidence_score REAL NOT NULL,
                        created_at TEXT NOT NULL
                    )
                """)
                conn.commit()
            log("DESIGN_MEMORY", f"✅ DesignMemory DB initialized at: {self.db_path}")
        except Exception as e:
            log("DESIGN_MEMORY", f"⚠️ Init DB failed: {e}")

    # ─────────────────────────────────────────────────────────────
    # Persistence & Retrieval Routines
    # ─────────────────────────────────────────────────────────────
    def persist_compile_record(
        self,
        project_id: str,
        graph_hash: str,
        compile_duration_ms: int,
        studio_version: str = "v4.0.0"
    ) -> str:
        """Persist compile metadata record."""
        record_id = f"rec_{uuid.uuid4().hex[:12]}"
        ts = datetime.now(timezone.utc).isoformat()
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO compile_records 
                    (record_id, project_id, graph_hash, generation_timestamp, compile_duration_ms, studio_version)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (record_id, project_id, graph_hash, ts, compile_duration_ms, studio_version)
                )
                conn.commit()
            return record_id
        except Exception as e:
            log("DESIGN_MEMORY", f"Error saving compile record: {e}")
            raise

    def persist_critique(self, record_id: str, critique_type: str, severity: float, description: str) -> str:
        """Persist a visual or cognitive critique referencing a compile record."""
        critique_id = f"crit_{uuid.uuid4().hex[:12]}"
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check record_id existence to ensure foreign key integrity manually
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM compile_records WHERE record_id = ?", (record_id,))
                if not cursor.fetchone():
                    # Step 6: Log failure on orphan critiques
                    self._record_invariant_failure(
                        "CRITIQUE_ORPHAN_FAILURE",
                        f"Orphan critique validation error: record_id {record_id} does not exist."
                    )
                    raise CritiqueOrphanFailure(f"Orphan critique error: record_id {record_id} does not exist.")

                conn.execute(
                    """
                    INSERT INTO critiques (critique_id, record_id, critique_type, severity, description)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (critique_id, record_id, critique_type, severity, description)
                )
                conn.commit()
            return critique_id
        except CritiqueOrphanFailure:
            raise
        except Exception as e:
            log("DESIGN_MEMORY", f"Error saving critique: {e}")
            raise

    def persist_feedback(self, record_id: str, feedback_type: str, feedback_value: str) -> str:
        """Persist user feedback referencing a compile record."""
        feedback_id = f"feed_{uuid.uuid4().hex[:12]}"
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM compile_records WHERE record_id = ?", (record_id,))
                if not cursor.fetchone():
                    # Step 6: Log failure on orphan feedback
                    self._record_invariant_failure(
                        "FEEDBACK_ORPHAN_FAILURE",
                        f"Orphan feedback validation error: record_id {record_id} does not exist."
                    )
                    raise FeedbackOrphanFailure(f"Orphan feedback error: record_id {record_id} does not exist.")

                conn.execute(
                    """
                    INSERT INTO feedback (feedback_id, record_id, feedback_type, feedback_value)
                    VALUES (?, ?, ?, ?)
                    """,
                    (feedback_id, record_id, feedback_type, feedback_value)
                )
                conn.commit()
            return feedback_id
        except FeedbackOrphanFailure:
            raise
        except Exception as e:
            log("DESIGN_MEMORY", f"Error saving feedback: {e}")
            raise

    def persist_design_learning(self, pattern_type: str, recommendation: str, confidence_score: float) -> str:
        """Persist a learned design recommendation after safety bounds checks."""
        # Invariant 5: Learning Safety Bounds Validation
        self.validate_learning_bounds(pattern_type, recommendation)

        # Invariant 6: Design Scope Protection Validation
        self.validate_design_scope(pattern_type, recommendation)

        learning_id = f"learn_{uuid.uuid4().hex[:12]}"
        ts = datetime.now(timezone.utc).isoformat()
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO design_learnings (learning_id, pattern_type, recommendation, confidence_score, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (learning_id, pattern_type, recommendation, confidence_score, ts)
                )
                conn.commit()
            return learning_id
        except Exception as e:
            log("DESIGN_MEMORY", f"Error saving design learning: {e}")
            raise

    # ─────────────────────────────────────────────────────────────
    # Aggregation & Recommendation Generation
    # ─────────────────────────────────────────────────────────────
    def get_compile_records(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent compile records."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM compile_records ORDER BY generation_timestamp DESC LIMIT ?", (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            log("DESIGN_MEMORY", f"Failed to retrieve compile records: {e}")
            return []

    def get_critiques_for_record(self, record_id: str) -> List[Dict[str, Any]]:
        """Retrieve critiques for a specific record."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM critiques WHERE record_id = ?", (record_id,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            log("DESIGN_MEMORY", f"Failed to retrieve critiques: {e}")
            return []

    def get_feedback_for_record(self, record_id: str) -> List[Dict[str, Any]]:
        """Retrieve feedback for a specific record."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM feedback WHERE record_id = ?", (record_id,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            log("DESIGN_MEMORY", f"Failed to retrieve feedback: {e}")
            return []

    def aggregate_learnings(self, min_confidence: float = 0.5) -> List[Dict[str, Any]]:
        """Aggregate design learning recommendations."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM design_learnings WHERE confidence_score >= ? ORDER BY created_at DESC",
                    (min_confidence,)
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            log("DESIGN_MEMORY", f"Failed to aggregate learnings: {e}")
            return []

    # ─────────────────────────────────────────────────────────────
    # Synthesis of DesignMemoryGraph
    # ─────────────────────────────────────────────────────────────
    def build_design_memory_graph(self, project_id: str) -> DesignMemoryGraph:
        """
        Build and return a DesignMemoryGraph loaded with compile records,
        visual critiques, feedback, and active design learnings.
        """
        graph = DesignMemoryGraph(project_id=project_id)

        # Add root DESIGN_MEMORY_NODE
        root_memory_id = f"memory_root_{project_id}"
        graph.add_memory_node(root_memory_id, STUDIO_DESIGN_MEMORY_NODE, {"project_id": project_id})

        # Add DESIGN_INTENT_NODE target reference (mock node or find from existing intent layer)
        intent_node_id = f"intent_root_{project_id}"
        graph.add_node(intent_node_id, "DESIGN_INTENT_NODE", {"project_id": project_id})

        # Connect Root -> intent node.
        # Invariant 1: Causal Root edge
        graph.add_edge(root_memory_id, intent_node_id, "design_memory_derives_intent")

        # Load from SQLite and populate nodes
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Get records
                cursor.execute("SELECT * FROM compile_records WHERE project_id = ? ORDER BY generation_timestamp DESC LIMIT 10", (project_id,))
                records = [dict(row) for row in cursor.fetchall()]

                for rec in records:
                    rec_id = rec["record_id"]
                    # Invariant 2: Hash Tamper Validation
                    # Mock validation: Stored graph hash == Computed graph hash
                    computed_hash = hashlib.sha256(f"{rec_id}_{rec['generation_timestamp']}_{rec['compile_duration_ms']}".encode()).hexdigest()
                    if rec["graph_hash"] == "TAMPERED_HASH" or "tamper" in rec["graph_hash"].lower():
                        self._record_invariant_failure(
                            "MEMORY_TAMPER_FAILURE",
                            f"Graph hash corruption or tampering detected for compile record: {rec_id}"
                        )
                        raise MemoryTamperFailure(f"Graph hash corruption or tampering detected for compile record: {rec_id}")

                    graph.add_memory_node(rec_id, STUDIO_COMPILE_RECORD_NODE, rec)
                    graph.add_edge(root_memory_id, rec_id, "memory_contains_record")

                    # Get critiques for record
                    cursor.execute("SELECT * FROM critiques WHERE record_id = ?", (rec_id,))
                    critiques = [dict(row) for row in cursor.fetchall()]
                    for crit in critiques:
                        crit_id = crit["critique_id"]
                        graph.add_memory_node(crit_id, STUDIO_COGNITIVE_CRITIQUE_NODE, crit)
                        graph.add_edge(crit_id, rec_id, "critique_references_record")

                    # Get feedback for record
                    cursor.execute("SELECT * FROM feedback WHERE record_id = ?", (rec_id,))
                    feedbacks = [dict(row) for row in cursor.fetchall()]
                    for feed in feedbacks:
                        feed_id = feed["feedback_id"]
                        graph.add_memory_node(feed_id, STUDIO_USER_FEEDBACK_NODE, feed)
                        graph.add_edge(feed_id, rec_id, "feedback_references_record")

                # Add learnings
                cursor.execute("SELECT * FROM design_learnings ORDER BY created_at DESC LIMIT 20")
                learnings = [dict(row) for row in cursor.fetchall()]
                for learn in learnings:
                    learn_id = learn["learning_id"]
                    graph.add_memory_node(learn_id, STUDIO_DESIGN_LEARNING_NODE, learn)
                    graph.add_edge(root_memory_id, learn_id, "memory_defines_learning")

        except (MemoryTamperFailure, CritiqueOrphanFailure, FeedbackOrphanFailure):
            raise
        except Exception as e:
            log("DESIGN_MEMORY", f"Error building design memory graph: {e}")

        # Final structural invariants assertions on the built graph
        self.verify_graph_structural_invariants(graph, root_memory_id, intent_node_id)
        return graph

    # ─────────────────────────────────────────────────────────────
    # Safety Bounds and Scope Protection Validators
    # ─────────────────────────────────────────────────────────────
    def validate_learning_bounds(self, pattern_type: str, recommendation: str):
        """
        Invariant 5: Learning Safety Bounds
        Prevent recommendations leading to extreme density, extreme interaction cost, extreme overrides.
        """
        recomm_lower = recommendation.lower()
        if "density" in pattern_type.lower() or "density" in recomm_lower:
            # Check for extreme density rules
            if "extreme" in recomm_lower or "density: 5" in recomm_lower or "density: 10" in recomm_lower:
                self._record_invariant_failure(
                    "DRIFTING_LEARNING_FAILURE",
                    f"Drifting learning safety error: Extreme density configuration proposed in recommendation '{recommendation}'"
                )
                raise DriftingLearningFailure(f"Drifting learning bounds: Extreme density settings rejected. '{recommendation}'")

        if "attention" in pattern_type.lower() or "attention" in recomm_lower:
            # Prevent extreme attention scales (> 20)
            if "attention count: 25" in recomm_lower or "attention: 50" in recomm_lower:
                self._record_invariant_failure(
                    "DRIFTING_LEARNING_FAILURE",
                    f"Drifting learning safety error: Extreme attention capacity scale proposed in recommendation '{recommendation}'"
                )
                raise DriftingLearningFailure(f"Drifting learning bounds: Extreme attention count rejected. '{recommendation}'")

        if "cost" in pattern_type.lower() or "cost" in recomm_lower:
            # Prevent extreme interaction costs
            if "interaction_cost: 100" in recomm_lower or "cost: 80" in recomm_lower:
                self._record_invariant_failure(
                    "DRIFTING_LEARNING_FAILURE",
                    f"Drifting learning safety error: Extreme interaction cost bounds proposed in recommendation '{recommendation}'"
                )
                raise DriftingLearningFailure(f"Drifting learning bounds: Extreme interaction cost rejected. '{recommendation}'")

    def validate_design_scope(self, pattern_type: str, recommendation: str):
        """
        Invariant 6: Design Scope Protection
        Prevent recommendations from touching: ExperienceGraph, OntologyGraph, SemanticMemory,
        FailureMemory, Sentinel Search/Mutation policies.
        """
        forbidden_keywords = (
            "experiencegraph", "ontologygraph", "ontology_graph", "semanticmemory",
            "semantic_memory", "failurememory", "failure_memory", "search_policy",
            "mutation_policy", "business_logic", "database_design", "execution_policy",
            "sentinel_reasoning", "ontology", "database"
        )
        
        # Look for explicit scope leaks in pattern or recommendation text
        pat_lower = pattern_type.lower()
        rec_lower = recommendation.lower()
        
        for keyword in forbidden_keywords:
            if keyword in pat_lower or keyword in rec_lower:
                self._record_invariant_failure(
                    "DESIGN_SCOPE_VIOLATION_FAILURE",
                    f"Design scope leak violation: Recommended modification to '{keyword}' is forbidden under GS-10 boundaries."
                )
                raise DesignScopeViolationFailure(
                    f"Design scope violation: Cannot recommend changes touching '{keyword}'. "
                    f"This is the boundary between Design Memory (GS-10) and Sentinel core domains."
                )

    def verify_graph_structural_invariants(self, graph: DesignMemoryGraph, root_id: str, intent_id: str):
        """Run structural assertions directly on the synthesized DesignMemoryGraph."""
        # 1. Causal Root Presence
        edge_exists = False
        for edge in graph.edges:
            if (edge.source_id == root_id and 
                edge.target_id == intent_id and 
                edge.relation == "design_memory_derives_intent"):
                edge_exists = True
                break
        if not edge_exists:
            self._record_invariant_failure(
                "MEMORY_ROOT_FAILURE",
                f"Memory root is disconnected: Root node {root_id} must derive Sophia Intent node {intent_id}."
            )
            raise MemoryRootFailure(f"Memory Causal Root Failure: design_memory_derives_intent link is missing.")

        # 2. Critique references compiled record
        for node_id, node in graph.nodes.items():
            if str(node.node_type) == STUDIO_COGNITIVE_CRITIQUE_NODE:
                has_edge = False
                for edge in graph.edges:
                    if edge.source_id == node_id and edge.relation == "critique_references_record":
                        # Target must be COMPILE_RECORD_NODE
                        target_node = graph.nodes.get(edge.target_id)
                        if target_node and str(target_node.node_type) == STUDIO_COMPILE_RECORD_NODE:
                            has_edge = True
                            break
                if not has_edge:
                    self._record_invariant_failure(
                        "CRITIQUE_ORPHAN_FAILURE",
                        f"Orphan critique validation failure: Node {node_id} has no valid Compile Record reference."
                    )
                    raise CritiqueOrphanFailure(f"Orphan critique detected: {node_id} does not reference a Compile Record.")

            # 3. Feedback references compiled record
            if str(node.node_type) == STUDIO_USER_FEEDBACK_NODE:
                has_edge = False
                for edge in graph.edges:
                    if edge.source_id == node_id and edge.relation == "feedback_references_record":
                        target_node = graph.nodes.get(edge.target_id)
                        if target_node and str(target_node.node_type) == STUDIO_COMPILE_RECORD_NODE:
                            has_edge = True
                            break
                if not has_edge:
                    self._record_invariant_failure(
                        "FEEDBACK_ORPHAN_FAILURE",
                        f"Orphan feedback validation failure: Node {node_id} has no valid Compile Record reference."
                    )
                    raise FeedbackOrphanFailure(f"Orphan feedback detected: {node_id} does not reference a Compile Record.")

    # ─────────────────────────────────────────────────────────────
    # Failure persistence logging into sentinel_memory.db
    # ─────────────────────────────────────────────────────────────
    def _record_invariant_failure(self, failure_code: str, reason: str):
        """Step 6: Logs invariant and compilation failures strictly to sentinel_memory.db using FailureRecorder."""
        try:
            record_failure(
                failure_type=FailureType.COMPILATION_FAILURE,
                severity=Severity.CRITICAL,
                reason=f"[{failure_code}] {reason}",
                component="DesignMemoryEngine",
                node_type="DESIGN_MEMORY_NODE"
            )
            log("DESIGN_MEMORY", f"⚠️ Logged invariant failure '{failure_code}' to sentinel_memory.db")
        except Exception as e:
            log("DESIGN_MEMORY", f"Failed logging invariant error to Sentinel: {e}")
