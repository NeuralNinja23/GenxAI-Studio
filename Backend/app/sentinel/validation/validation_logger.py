import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any
import datetime
from app.core.logging import log

# Define DB path in the root folder
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
DB_PATH = ROOT_DIR / "Sentinel_Validation" / "sentinel_validation V2.db"

class ValidationLogger:
    """
    Synchronous database logger for Sentinel Validation metrics.
    Writes telemetry to `sentinel_validation.db`.
    """

    @classmethod
    def _get_connection(cls) -> sqlite3.Connection:
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    @classmethod
    def initialize_db(cls):
        """Creates the necessary validation tables if they do not exist."""
        log("TELEMETRY", f"Initializing Validation DB at {DB_PATH}")
        with cls._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS projection_runs (
                run_id TEXT PRIMARY KEY,
                timestamp DATETIME,
                project_id TEXT,
                prompt TEXT,
                state_fingerprint TEXT,
                selected_branch TEXT,
                branch_count INTEGER,
                final_weight REAL,
                convergence REAL,
                complexity REAL,
                repulsion_score REAL,
                governance_score REAL,
                memory_hits INTEGER,
                dependency_score REAL,
                schema_score REAL,
                state_score REAL,
                build_score REAL,
                runtime_score REAL,
                visual_score REAL,
                topology_score REAL,
                final_result TEXT,
                failure_type TEXT,
                termination_reason TEXT,
                duration_ms INTEGER,
                primary_failure_category TEXT,
                active_failure_categories TEXT,
                routing_decision TEXT,
                routing_reason TEXT,
                search_outcome TEXT
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS branch_runs (
                branch_id TEXT PRIMARY KEY,
                run_id TEXT,
                parent_branch TEXT,
                state_fingerprint TEXT,
                mutation_type TEXT,
                weight REAL,
                convergence REAL,
                complexity REAL,
                repulsion_score REAL,
                advisory_mod REAL,
                governance_passed BOOLEAN,
                selected BOOLEAN,
                failure_type TEXT,
                FOREIGN KEY(run_id) REFERENCES projection_runs(run_id)
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS failure_events (
                event_id TEXT PRIMARY KEY,
                run_id TEXT,
                branch_id TEXT,
                failure_type TEXT,
                failure_fingerprint TEXT,
                cfm TEXT,
                principle_violated TEXT,
                root_cause TEXT,
                stage TEXT,
                severity TEXT,
                recovered BOOLEAN,
                escape_mutation_used BOOLEAN,
                FOREIGN KEY(run_id) REFERENCES projection_runs(run_id)
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_events (
                event_id TEXT PRIMARY KEY,
                run_id TEXT,
                branch_id TEXT,
                memory_hit TEXT,
                fingerprint_matched TEXT,
                repulsion_before REAL,
                repulsion_after REAL,
                branch_suppressed BOOLEAN,
                decision_changed BOOLEAN,
                FOREIGN KEY(run_id) REFERENCES projection_runs(run_id)
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS governance_events (
                event_id TEXT PRIMARY KEY,
                run_id TEXT,
                branch_id TEXT,
                governance_rule TEXT,
                score_before REAL,
                score_after REAL,
                action TEXT,
                reason TEXT,
                FOREIGN KEY(run_id) REFERENCES projection_runs(run_id)
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS skill_usage_events (
                event_id TEXT PRIMARY KEY,
                run_id TEXT,
                timestamp DATETIME,
                faculty TEXT,
                skill_id TEXT,
                intent TEXT,
                used BOOLEAN,
                FOREIGN KEY(run_id) REFERENCES projection_runs(run_id)
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_events (
                event_id TEXT PRIMARY KEY,
                run_id TEXT,
                timestamp DATETIME,
                event_type TEXT,
                severity TEXT,
                message TEXT,
                metadata_json TEXT,
                FOREIGN KEY(run_id) REFERENCES projection_runs(run_id)
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS failure_clusters (
                cluster_id TEXT PRIMARY KEY,
                run_id TEXT,
                root_failure TEXT,
                failure_manifold TEXT,
                fingerprint TEXT,
                event_count INTEGER,
                recovered BOOLEAN,
                FOREIGN KEY(run_id) REFERENCES projection_runs(run_id)
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS failure_cascades (
                cascade_id TEXT PRIMARY KEY,
                run_id TEXT,
                root_failure TEXT,
                root_confidence REAL,
                cascade_depth INTEGER,
                fingerprint TEXT,
                cfm TEXT,
                repair_strategy TEXT,
                recovered BOOLEAN,
                FOREIGN KEY(run_id) REFERENCES projection_runs(run_id)
            )
            """)
            
            # Idempotent schema migration for routing fields and renamed fields
            for col, col_type in [
                ("primary_failure_category", "TEXT"),
                ("active_failure_categories", "TEXT"),
                ("routing_decision", "TEXT"),
                ("routing_reason", "TEXT"),
                ("search_outcome", "TEXT"),
                ("governance_score", "REAL"),
            ]:
                try:
                    cursor.execute(f"ALTER TABLE projection_runs ADD COLUMN {col} {col_type};")
                except sqlite3.OperationalError:
                    pass

            for col, col_type in [
                ("advisory_mod", "REAL"),
            ]:
                try:
                    cursor.execute(f"ALTER TABLE branch_runs ADD COLUMN {col} {col_type};")
                except sqlite3.OperationalError:
                    pass

            conn.commit()

    @classmethod
    def flush_events(cls, run_id: str, events: List[Dict[str, Any]]):
        """
        Synchronously flushes all recorded events in a single SQLite transaction.
        """
        if not events:
            return

        with cls._get_connection() as conn:
            cursor = conn.cursor()
            
            for event in events:
                e_type = event.get("type")
                p = event.get("payload", {})

                if e_type == "projection_run":
                    cursor.execute("""
                    INSERT OR REPLACE INTO projection_runs (
                        run_id, timestamp, project_id, prompt, state_fingerprint, selected_branch, branch_count,
                        final_weight, convergence, complexity, repulsion_score, governance_score, memory_hits,
                        dependency_score, schema_score, state_score, build_score, runtime_score, visual_score,
                        topology_score, final_result, failure_type, termination_reason, duration_ms,
                        primary_failure_category, active_failure_categories, routing_decision, routing_reason, search_outcome
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        run_id,
                        datetime.datetime.utcnow().isoformat(),
                        p.get("project_id"),
                        p.get("prompt"),
                        p.get("state_fingerprint"),
                        p.get("selected_branch"),
                        p.get("branch_count"),
                        p.get("final_weight"),
                        p.get("convergence"),
                        p.get("complexity"),
                        p.get("repulsion_score"),
                        p.get("governance_score"),
                        p.get("memory_hits"),
                        p.get("dependency_score"),
                        p.get("schema_score"),
                        p.get("state_score"),
                        p.get("build_score"),
                        p.get("runtime_score"),
                        p.get("visual_score"),
                        p.get("topology_score"),
                        p.get("final_result"),
                        p.get("failure_type"),
                        p.get("termination_reason"),
                        p.get("duration_ms"),
                        p.get("primary_failure_category"),
                        json.dumps(p.get("active_failure_categories", [])) if isinstance(p.get("active_failure_categories"), list) else json.dumps([]),
                        p.get("routing_decision"),
                        p.get("routing_reason"),
                        p.get("search_outcome")
                    ))
                
                elif e_type == "branch_run":
                    cursor.execute("""
                    INSERT OR REPLACE INTO branch_runs (
                        branch_id, run_id, parent_branch, state_fingerprint, mutation_type, weight,
                        convergence, complexity, repulsion_score, advisory_mod, governance_passed, selected, failure_type
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        p.get("branch_id"),
                        run_id,
                        p.get("parent_branch"),
                        p.get("state_fingerprint"),
                        p.get("mutation_type"),
                        p.get("weight"),
                        p.get("convergence"),
                        p.get("complexity"),
                        p.get("repulsion_score"),
                        p.get("advisory_mod"),
                        p.get("governance_passed"),
                        p.get("selected"),
                        p.get("failure_type")
                    ))
                
                elif e_type == "failure_event":
                    cursor.execute("""
                    INSERT OR REPLACE INTO failure_events (
                        event_id, run_id, branch_id, failure_type, failure_fingerprint,
                        cfm, principle_violated, root_cause, stage, severity, recovered, escape_mutation_used
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        p.get("event_id"),
                        run_id,
                        p.get("branch_id"),
                        p.get("failure_type"),
                        p.get("failure_fingerprint"),
                        p.get("cfm"),
                        p.get("principle_violated"),
                        p.get("root_cause"),
                        p.get("stage"),
                        p.get("severity"),
                        p.get("recovered"),
                        p.get("escape_mutation_used")
                    ))

                elif e_type == "memory_event":
                    cursor.execute("""
                    INSERT OR REPLACE INTO memory_events (
                        event_id, run_id, branch_id, memory_hit, fingerprint_matched,
                        repulsion_before, repulsion_after, branch_suppressed, decision_changed
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        p.get("event_id"),
                        run_id,
                        p.get("branch_id"),
                        p.get("memory_hit"),
                        p.get("fingerprint_matched"),
                        p.get("repulsion_before"),
                        p.get("repulsion_after"),
                        p.get("branch_suppressed"),
                        p.get("decision_changed")
                    ))
                
                elif e_type == "governance_event":
                    cursor.execute("""
                    INSERT OR REPLACE INTO governance_events (
                        event_id, run_id, branch_id, governance_rule, score_before,
                        score_after, action, reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        p.get("event_id"),
                        run_id,
                        p.get("branch_id"),
                        p.get("governance_rule"),
                        p.get("score_before"),
                        p.get("score_after"),
                        p.get("action"),
                        p.get("reason")
                    ))
                
                elif e_type == "skill_usage_event":
                    cursor.execute("""
                    INSERT OR REPLACE INTO skill_usage_events (
                        event_id, run_id, timestamp, faculty, skill_id, intent, used
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        p.get("event_id"),
                        run_id,
                        datetime.datetime.utcnow().isoformat(),
                        p.get("faculty"),
                        p.get("skill_id"),
                        p.get("intent"),
                        p.get("used")
                    ))
                
                elif e_type == "system_event":
                    cursor.execute("""
                    INSERT OR REPLACE INTO system_events (
                        event_id, run_id, timestamp, event_type, severity, message, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        p.get("event_id"),
                        run_id,
                        datetime.datetime.utcnow().isoformat(),
                        p.get("event_type"),
                        p.get("severity"),
                        p.get("message"),
                        json.dumps(p.get("metadata_json", {}))
                    ))
                
                elif e_type == "failure_cluster":
                    cursor.execute("""
                    INSERT OR REPLACE INTO failure_clusters (
                        cluster_id, run_id, root_failure, failure_manifold, fingerprint,
                        event_count, recovered
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        p.get("cluster_id"),
                        run_id,
                        p.get("root_failure"),
                        p.get("failure_manifold"),
                        p.get("fingerprint"),
                        p.get("event_count"),
                        p.get("recovered")
                    ))
                
                elif e_type == "failure_cascade":
                    cursor.execute("""
                    INSERT OR REPLACE INTO failure_cascades (
                        cascade_id, run_id, root_failure, root_confidence, cascade_depth,
                        fingerprint, cfm, repair_strategy, recovered
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        p.get("cascade_id"),
                        run_id,
                        p.get("root_failure"),
                        p.get("root_confidence"),
                        p.get("cascade_depth"),
                        p.get("fingerprint"),
                        p.get("cfm"),
                        p.get("repair_strategy"),
                        p.get("recovered")
                    ))
            
            conn.commit()

# Ensure DB is initialized when this module is imported.
ValidationLogger.initialize_db()
