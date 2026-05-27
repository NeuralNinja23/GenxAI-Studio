# app/oracles/__init__.py
"""
V4 Oracles Package — Stage 4: Oracle Layer

Defines the modular Oracle interface structures, syntax checks, graph legality,
and workflow assertions.
"""

from .base import BaseOracle, OracleResult
from .syntax_oracle import SyntaxOracle
from .topology_oracle import TopologyOracle
from .behavioral_oracle import BehavioralOracle
from .runtime_oracle import RuntimeOracle
from .visual_oracle import VisualOracle
from .semantic_oracle import SemanticOracle
from .convergence_oracle import ConvergenceOracle
from .pipeline import OraclePipeline

__all__ = [
    "BaseOracle",
    "OracleResult",
    "SyntaxOracle",
    "TopologyOracle",
    "BehavioralOracle",
    "RuntimeOracle",
    "VisualOracle",
    "SemanticOracle",
    "ConvergenceOracle",
    "OraclePipeline",
]
