# app/topology/__init__.py
"""
V4 Topology Package — Stage 2: Canonical Topology Engine

Defines the project node ontology, canonical ProjectTopologyGraph model,
compiler, builder, validator, difference analyzer, and version manager.
"""

from .node_types import NodeType, CapabilityBoundary, ProjectionLegality, NodeOntology
from .project_graph import TopologyNode, TopologyEdge, ProjectTopologyGraph
from .topology_compiler import TopologyCompiler
from .topology_builder import TopologyBuilder
from .topology_validator import TopologyValidator, TopologyValidationResult, ValidationViolation
from .structural_diff import StructuralDiff, TopologyDiffReport, NodeDiff, EdgeDiff
from .topology_version_manager import TopologyVersionRecord, TopologyVersionManager
from .ast_generator import ASTFile, ASTImport, ASTField, ASTMethod, ASTClass, ASTRoute, ASTReactComponent, ASTGenerator
from .ast_mutator import ASTMutator
from .ast_merger import ASTMerger
from .ast_projector import ASTProjector
from .ast_validator import ASTValidator

__all__ = [
    "NodeType",
    "CapabilityBoundary",
    "ProjectionLegality",
    "NodeOntology",
    "TopologyNode",
    "TopologyEdge",
    "ProjectTopologyGraph",
    "TopologyCompiler",
    "TopologyBuilder",
    "TopologyValidator",
    "TopologyValidationResult",
    "ValidationViolation",
    "StructuralDiff",
    "TopologyDiffReport",
    "NodeDiff",
    "EdgeDiff",
    "TopologyVersionRecord",
    "TopologyVersionManager",
    "ASTFile",
    "ASTImport",
    "ASTField",
    "ASTMethod",
    "ASTClass",
    "ASTRoute",
    "ASTReactComponent",
    "ASTGenerator",
    "ASTMutator",
    "ASTMerger",
    "ASTProjector",
    "ASTValidator",
]
