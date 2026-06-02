# app/sentinel/telemetry/validation_recorder.py
from typing import Optional, Dict, Any
from app.sentinel.validation.validation_bus import ValidationBus
import uuid

class ValidationRecorder:
    """
    Facade for Sentinel subsystems to record validation events.
    Isolates the rest of the application from the inner workings of the ValidationBus.
    """

    @staticmethod
    def record_projection_run(payload: Dict[str, Any]):
        ValidationBus().emit("projection_run", payload)

    @staticmethod
    def record_branch_run(payload: Dict[str, Any]):
        ValidationBus().emit("branch_run", payload)

    @staticmethod
    def record_failure(payload: Dict[str, Any]):
        if "event_id" not in payload:
            payload["event_id"] = f"fail_{uuid.uuid4().hex[:8]}"
        ValidationBus().emit("failure_event", payload)

    @staticmethod
    def record_cluster(payload: Dict[str, Any]):
        if "cluster_id" not in payload:
            payload["cluster_id"] = f"clus_{uuid.uuid4().hex[:8]}"
        ValidationBus().emit("failure_cluster", payload)

    @staticmethod
    def record_cascade(payload: Dict[str, Any]):
        if "cascade_id" not in payload:
            payload["cascade_id"] = f"casc_{uuid.uuid4().hex[:8]}"
        ValidationBus().emit("failure_cascade", payload)

    @staticmethod
    def record_memory_event(payload: Dict[str, Any]):
        if "event_id" not in payload:
            payload["event_id"] = f"mem_{uuid.uuid4().hex[:8]}"
        ValidationBus().emit("memory_event", payload)

    @staticmethod
    def record_governance_event(payload: Dict[str, Any]):
        if "event_id" not in payload:
            payload["event_id"] = f"gov_{uuid.uuid4().hex[:8]}"
        ValidationBus().emit("governance_event", payload)

    @staticmethod
    def record_system_event(
        event_type: str,
        severity: str,
        message: str,
        metadata_json: Optional[Dict[str, Any]] = None
    ):
        payload = {
            "event_id": f"sys_{uuid.uuid4().hex[:8]}",
            "event_type": event_type,
            "severity": severity,
            "message": message,
            "metadata_json": metadata_json or {}
        }
        ValidationBus().emit("system_event", payload)
