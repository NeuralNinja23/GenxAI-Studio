# app/sentinel/failure_memory/__init__.py
"""
Failure Memory module for the GenCode Studio V4.
"""
from .failure_geometry import FailureGeometry, TopologyHeatMap
from .repulsion_engine import RepulsionEngine
from .failure_recorder import FailureRecorder, FailureType, Severity, record_failure

__all__ = [
    "FailureGeometry", "RepulsionEngine", "TopologyHeatMap",
    "FailureRecorder", "FailureType", "Severity", "record_failure",
]
