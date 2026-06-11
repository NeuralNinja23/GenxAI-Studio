# app/sentinel/failure_memory/failure_analyzer.py
import uuid
import json
from typing import List, Dict, Any
from app.sentinel.validation.validation_recorder import ValidationRecorder

class FailureAnalyzer:
    """
    Translates raw VerificationGate failures into Sentinel Memory objects.
    Implements the 'Earliest Causal Failure Wins' algorithm to determine root causes.
    """
    
    STAGE_ORDER = {
        "Layer A": 10,
        "Layer B": 20,
        "Layer C": 30,
        "Layer D": 40,
        "Layer E": 50,
        "Layer F": 60
    }

    @classmethod
    def _get_stage_priority(cls, stage_str: str) -> int:
        for key, prio in cls.STAGE_ORDER.items():
            if key in stage_str:
                return prio
        return 999  # Unknown stage gets lowest priority

    @classmethod
    def analyze_and_record(cls, failures: List[Any]):
        import os
        logs_dir = os.path.join(os.path.dirname(__file__), "../../../../Logs")
        os.makedirs(logs_dir, exist_ok=True)
        debug_path = os.path.join(logs_dir, "analyzer_debug.txt")
        with open(debug_path, "a") as f:
            f.write(f"Analyze called with {len(failures)} failures: {failures}\n")
            
        if not failures:
            return

        # 1. Build Clusters
        # Group by (failure_type, stage)
        clusters_map = {}
        for f in failures:
            key = (f.failure_type, f.stage)
            if key not in clusters_map:
                clusters_map[key] = {
                    "cluster_id": f"clus_{uuid.uuid4().hex[:8]}",
                    "root_failure": f.failure_type,
                    "stage": f.stage,
                    "failure_manifold": [],
                    "fingerprint": f"{f.failure_type}:{f.stage}",
                    "event_count": 0,
                    "recovered": False
                }
            
            c = clusters_map[key]
            c["event_count"] += 1
            if len(c["failure_manifold"]) < 5:  # limit details to prevent huge DB bloat
                c["failure_manifold"].append({
                    "file": f.file,
                    "details": f.details
                })

        clusters = list(clusters_map.values())

        for c in clusters:
            ValidationRecorder.record_cluster({
                "cluster_id": c["cluster_id"],
                "root_failure": c["root_failure"],
                "failure_manifold": json.dumps(c["failure_manifold"]),
                "fingerprint": c["fingerprint"],
                "event_count": c["event_count"],
                "recovered": c["recovered"]
            })

        # 2. Build Cascade
        if not clusters:
            return

        # Earliest Causal Failure Wins
        clusters.sort(key=lambda c: cls._get_stage_priority(c["stage"]))
        root_cluster = clusters[0]
        
        # Calculate root_confidence
        earliest_prio = cls._get_stage_priority(root_cluster["stage"])
        ties = sum(1 for c in clusters if cls._get_stage_priority(c["stage"]) == earliest_prio)
        
        root_confidence = 1.0
        if ties > 1:
            root_confidence = 0.85
        if earliest_prio == 999:
            root_confidence = 0.50

        # Build the chain string for CFM
        chain_list = [c["root_failure"] for c in clusters]

        ValidationRecorder.record_cascade({
            "cascade_id": f"casc_{uuid.uuid4().hex[:8]}",
            "root_failure": root_cluster["root_failure"],
            "root_confidence": root_confidence,
            "cascade_depth": len(clusters),
            "fingerprint": root_cluster["fingerprint"],
            "cfm": json.dumps(chain_list),
            "repair_strategy": "N/A",
            "recovered": False
        })
