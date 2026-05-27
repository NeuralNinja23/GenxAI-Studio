# app/topology/node_types.py
"""
V4 Topology Node Types & Ontology — Stage 2: Canonical Topology Engine

Defines the formal node types, capabilities, mutation legality, and
projection mappings that govern the ProjectTopologyGraph.
"""

from enum import Enum, auto
from typing import Dict, List, Set, Any
from pydantic import BaseModel, Field
from app.models.runtime_models import MutationTier

class NodeType(str, Enum):
    API_NODE = "API_NODE"
    SCHEMA_NODE = "SCHEMA_NODE"
    UI_NODE = "UI_NODE"
    SERVICE_NODE = "SERVICE_NODE"
    STATE_NODE = "STATE_NODE"
    ROUTE_NODE = "ROUTE_NODE"
    WORKFLOW_NODE = "WORKFLOW_NODE"
    ORACLE_NODE = "ORACLE_NODE"
    RUNTIME_NODE = "RUNTIME_NODE"
    DEPLOYMENT_NODE = "DEPLOYMENT_NODE"
    CONTRACT_NODE = "CONTRACT_NODE"
    AST_NODE = "AST_NODE"


class CapabilityBoundary(BaseModel):
    """Defines which faculties can interact with or mutate a node type."""
    allowed_proposers: Set[str] = Field(description="Cognitive faculties allowed to propose mutations")
    allowed_validators: Set[str] = Field(description="Oracles or faculties allowed to validate")
    execution_governed: bool = Field(default=True, description="If True, only deterministic kernel can execute")


class ProjectionLegality(BaseModel):
    """Defines how a topology node translates into physical files/directories."""
    allowed_file_patterns: List[str] = Field(description="Glob patterns of files this node can project to")
    forbidden_file_patterns: List[str] = Field(default_factory=list, description="Forbidden file destinations")
    target_format: str = Field(description="e.g. 'python', 'typescript', 'json', 'yaml'")


class NodeOntology:
    """
    Ontological dictionary for topology nodes.
    Enforces strict capability and projection constraints per node type.
    """

    ONTOLOGY: Dict[NodeType, Dict[str, Any]] = {
        NodeType.API_NODE: {
            "max_mutation_tier": MutationTier.TOPOLOGY,
            "boundary": CapabilityBoundary(
                allowed_proposers={"Victoria", "Derek"},
                allowed_validators={"Luna", "topology_oracle", "behavioral_oracle"}
            ),
            "projection": ProjectionLegality(
                allowed_file_patterns=["Backend/app/api/**/*.py", "Backend/app/routers/**/*.py"],
                forbidden_file_patterns=["Backend/app/runtime/**/*.py"],
                target_format="python"
            )
        },
        NodeType.SCHEMA_NODE: {
            "max_mutation_tier": MutationTier.TOPOLOGY,
            "boundary": CapabilityBoundary(
                allowed_proposers={"Victoria", "Derek"},
                allowed_validators={"Luna", "topology_oracle", "syntax_oracle"}
            ),
            "projection": ProjectionLegality(
                allowed_file_patterns=["Backend/app/models/**/*.py"],
                forbidden_file_patterns=["Backend/app/runtime/**/*.py"],
                target_format="python"
            )
        },
        NodeType.UI_NODE: {
            "max_mutation_tier": MutationTier.STRUCTURAL_UI,
            "boundary": CapabilityBoundary(
                allowed_proposers={"Victoria", "Derek"},
                allowed_validators={"Luna", "visual_oracle"}
            ),
            "projection": ProjectionLegality(
                allowed_file_patterns=["Frontend/src/components/**/*.tsx", "Frontend/src/views/**/*.tsx"],
                forbidden_file_patterns=["Frontend/vite.config.ts"],
                target_format="typescript"
            )
        },
        NodeType.SERVICE_NODE: {
            "max_mutation_tier": MutationTier.BEHAVIORAL,
            "boundary": CapabilityBoundary(
                allowed_proposers={"Derek"},
                allowed_validators={"Luna", "runtime_oracle", "syntax_oracle"}
            ),
            "projection": ProjectionLegality(
                allowed_file_patterns=["Backend/app/services/**/*.py", "Backend/app/utils/**/*.py"],
                forbidden_file_patterns=["Backend/app/runtime/**/*.py"],
                target_format="python"
            )
        },
        NodeType.STATE_NODE: {
            "max_mutation_tier": MutationTier.BEHAVIORAL,
            "boundary": CapabilityBoundary(
                allowed_proposers={"Derek"},
                allowed_validators={"Luna", "visual_oracle", "syntax_oracle"}
            ),
            "projection": ProjectionLegality(
                allowed_file_patterns=["Frontend/src/store/**/*.ts", "Frontend/src/context/**/*.tsx"],
                forbidden_file_patterns=[],
                target_format="typescript"
            )
        },
        NodeType.ROUTE_NODE: {
            "max_mutation_tier": MutationTier.TOPOLOGY,
            "boundary": CapabilityBoundary(
                allowed_proposers={"Victoria", "Derek"},
                allowed_validators={"Luna", "topology_oracle", "behavioral_oracle"}
            ),
            "projection": ProjectionLegality(
                allowed_file_patterns=["Backend/app/api/**/*.py", "Frontend/src/router/**/*.ts"],
                forbidden_file_patterns=[],
                target_format="python_typescript"
            )
        },
        NodeType.WORKFLOW_NODE: {
            "max_mutation_tier": MutationTier.TOPOLOGY,
            "boundary": CapabilityBoundary(
                allowed_proposers={"Victoria", "Derek"},
                allowed_validators={"Luna", "behavioral_oracle"}
            ),
            "projection": ProjectionLegality(
                allowed_file_patterns=["Backend/app/workflow/**/*.py"],
                forbidden_file_patterns=["Backend/app/workflow/engine.py"],
                target_format="python"
            )
        },
        NodeType.ORACLE_NODE: {
            "max_mutation_tier": MutationTier.FORBIDDEN,  # Immutable governance
            "boundary": CapabilityBoundary(
                allowed_proposers=set(),
                allowed_validators=set(),
                execution_governed=True
            ),
            "projection": ProjectionLegality(
                allowed_file_patterns=["Backend/app/oracles/**/*.py"],
                forbidden_file_patterns=["*"],
                target_format="python"
            )
        },
        NodeType.RUNTIME_NODE: {
            "max_mutation_tier": MutationTier.FORBIDDEN,  # Immutable OS Core
            "boundary": CapabilityBoundary(
                allowed_proposers=set(),
                allowed_validators=set(),
                execution_governed=True
            ),
            "projection": ProjectionLegality(
                allowed_file_patterns=["Backend/app/runtime/**/*.py"],
                forbidden_file_patterns=["*"],
                target_format="python"
            )
        },
        NodeType.DEPLOYMENT_NODE: {
            "max_mutation_tier": MutationTier.FORBIDDEN,  # Framework boundary
            "boundary": CapabilityBoundary(
                allowed_proposers={"Reggie"},
                allowed_validators={"Luna", "deployment_oracle"}
            ),
            "projection": ProjectionLegality(
                allowed_file_patterns=["docker-compose.yml", "Dockerfile", "nginx.conf"],
                forbidden_file_patterns=["*"],
                target_format="yaml_dockerfile"
            )
        },
        NodeType.CONTRACT_NODE: {
            "max_mutation_tier": MutationTier.FORBIDDEN,  # Immutable directive constraints
            "boundary": CapabilityBoundary(
                allowed_proposers=set(),
                allowed_validators=set()
            ),
            "projection": ProjectionLegality(
                allowed_file_patterns=["Backend/app/models/directive.py"],
                forbidden_file_patterns=["*"],
                target_format="python"
            )
        },
        NodeType.AST_NODE: {
            "max_mutation_tier": MutationTier.TOPOLOGY,
            "boundary": CapabilityBoundary(
                allowed_proposers={"Derek"},
                allowed_validators={"Luna", "syntax_oracle"}
            ),
            "projection": ProjectionLegality(
                allowed_file_patterns=["**/*.py", "**/*.ts", "**/*.tsx"],
                forbidden_file_patterns=[],
                target_format="source_code"
            )
        }
    }

    @classmethod
    def get_max_mutation_tier(cls, node_type: NodeType) -> MutationTier:
        return cls.ONTOLOGY[node_type]["max_mutation_tier"]

    @classmethod
    def get_boundary(cls, node_type: NodeType) -> CapabilityBoundary:
        return cls.ONTOLOGY[node_type]["boundary"]

    @classmethod
    def get_projection(cls, node_type: NodeType) -> ProjectionLegality:
        return cls.ONTOLOGY[node_type]["projection"]
