# app/topology/node_types.py
"""
V4 Topology Node Types & Ontology — Stage 2: Canonical Topology Engine

Defines the formal node types, capabilities, mutation legality, and
projection mappings that govern the ProjectTopologyGraph.

Phase 1 Upgrade: Partitioned UI Domains & Domain-Specific Physics
    Each NodeType is now bound to a TopologyDomain (UI, DATA, SECURITY,
    RUNTIME, INFRASTRUCTURE) with its own DomainPhysics envelope.
    This separates visual density from structural instability so that
    rich UIs are guided into coherence — never pruned for complexity.
"""

from enum import Enum, auto
from typing import Dict, List, Set, Any
from pydantic import BaseModel, Field
from app.models.runtime_models import MutationTier


# ─────────────────────────────────────────────────────────────
# Topology Domains
# ─────────────────────────────────────────────────────────────

class TopologyDomain(str, Enum):
    """
    Logical partitions of the topology graph.

    Each domain owns a distinct physics envelope so that the cognition
    engine can apply domain-aware repulsion thresholds, density tolerances,
    and stabilization strategies instead of a single global threshold.

    UI_DOMAIN       — Visual components, layouts, views, state stores.
                      High density tolerance; complexity is *expected*.
    DATA_DOMAIN     — Schemas, services, workflows.  Moderate density.
    SECURITY_DOMAIN — Routes, contracts, oracles.  Low density; high
                      structural integrity requirements.
    RUNTIME_DOMAIN  — Runtime nodes, deployment.  Near-zero mutation
                      tolerance; immutable execution substrate.
    """
    UI_DOMAIN       = "UI_DOMAIN"
    DATA_DOMAIN     = "DATA_DOMAIN"
    SECURITY_DOMAIN = "SECURITY_DOMAIN"
    RUNTIME_DOMAIN  = "RUNTIME_DOMAIN"
    EXPERIENCE_DOMAIN = "EXPERIENCE_DOMAIN"
    ONTOLOGY_DOMAIN = "ONTOLOGY_DOMAIN"


class DomainPhysics(BaseModel):
    """
    Per-domain physics parameters that govern the bounded cognition
    engine's repulsion, density evaluation, and stabilization behaviour.

    These replace the former single global repulsion threshold (0.85)
    with domain-sensitive envelopes.
    """
    repulsion_threshold: float = Field(
        description="Cosine similarity threshold above which a candidate "
                    "branch is flagged for stabilization (NOT pruning) "
                    "within this domain.  Lower = more conservative."
    )
    density_tolerance: float = Field(
        description="Maximum normalised visual/structural density (0-1) "
                    "before triggering compression passes.  UI domains "
                    "have a high tolerance; infrastructure has near-zero."
    )
    max_nodes_soft_cap: int = Field(
        description="Soft cap on the number of nodes in this domain "
                    "before the stabiliser suggests clustering or "
                    "hierarchy folding.  NOT a hard block."
    )
    compression_eligible: bool = Field(
        description="Whether nodes in this domain are candidates for "
                    "meaning-aware topology compression.  Immutable "
                    "domains must never be compressed."
    )
    stabilization_priority: int = Field(
        description="1 (highest) to 5 (lowest).  Determines the order "
                    "in which the reflection loop addresses domains "
                    "when multiple domains need stabilisation."
    )

class NodeType(str, Enum):
    API_NODE = "API_NODE"
    SCHEMA_NODE = "SCHEMA_NODE"
    UI_NODE = "UI_NODE"
    SERVICE_NODE = "SERVICE_NODE"
    STATE_NODE = "STATE_NODE"
    UI_STATE_NODE = "UI_STATE_NODE"
    DATA_STATE_NODE = "DATA_STATE_NODE"
    ROUTE_NODE = "ROUTE_NODE"

    WORKFLOW_NODE = "WORKFLOW_NODE"
    ORACLE_NODE = "ORACLE_NODE"
    RUNTIME_NODE = "RUNTIME_NODE"
    DEPLOYMENT_NODE = "DEPLOYMENT_NODE"
    CONTRACT_NODE = "CONTRACT_NODE"
    AST_NODE = "AST_NODE"

    EXPERIENCE_NODE = "EXPERIENCE_NODE"
    GOAL_NODE = "GOAL_NODE"
    JOURNEY_NODE = "JOURNEY_NODE"
    FLOW_NODE = "FLOW_NODE"
    SCREEN_NODE = "SCREEN_NODE"
    ACTION_NODE = "ACTION_NODE"

    ENTITY_NODE = "ENTITY_NODE"
    ROLE_NODE = "ROLE_NODE"
    RELATIONSHIP_NODE = "RELATIONSHIP_NODE"
    CAPABILITY_NODE = "CAPABILITY_NODE"
    ONTOLOGY_WORKFLOW_NODE = "ONTOLOGY_WORKFLOW_NODE"

    WORKSPACE_NODE = "WORKSPACE_NODE"
    PAGE_NODE = "PAGE_NODE"
    FEATURE_NODE = "FEATURE_NODE"
    NAV_LAYOUT_NODE = "NAV_LAYOUT_NODE"


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

    # ── Domain-level physics presets ────────────────────────────
    #    Referenced by each ONTOLOGY entry via the 'physics' key.
    #    Downstream consumers (sentinel_core, repulsion_engine, mutation_engine)
    #    should use `get_physics(node_type)` instead of hard-coding thresholds.

    _DOMAIN_PHYSICS: Dict[TopologyDomain, DomainPhysics] = {
        TopologyDomain.UI_DOMAIN: DomainPhysics(
            repulsion_threshold=0.55,     # Very permissive — UI density is expected
            density_tolerance=0.85,       # Allow rich, dense frontends
            max_nodes_soft_cap=40,        # Soft cap; triggers clustering, not pruning
            compression_eligible=True,    # Can fold/cluster when it helps UX
            stabilization_priority=2      # Important but after security
        ),
        TopologyDomain.DATA_DOMAIN: DomainPhysics(
            repulsion_threshold=0.70,     # Moderate — schemas can grow
            density_tolerance=0.60,
            max_nodes_soft_cap=25,
            compression_eligible=True,
            stabilization_priority=3
        ),
        TopologyDomain.SECURITY_DOMAIN: DomainPhysics(
            repulsion_threshold=0.80,     # Strict — route/contract integrity matters
            density_tolerance=0.40,
            max_nodes_soft_cap=15,
            compression_eligible=False,   # Never compress security/governance nodes
            stabilization_priority=1      # Highest — fix security first
        ),
        TopologyDomain.RUNTIME_DOMAIN: DomainPhysics(
            repulsion_threshold=0.90,     # Near-immutable; only catastrophic issues
            density_tolerance=0.15,
            max_nodes_soft_cap=8,
            compression_eligible=False,
            stabilization_priority=1
        ),
        TopologyDomain.EXPERIENCE_DOMAIN: DomainPhysics(
            repulsion_threshold=0.70,     # Conservative baseline for Phase 7
            density_tolerance=0.60,       # Similar to DATA_DOMAIN initially
            max_nodes_soft_cap=25,
            compression_eligible=True,
            stabilization_priority=4      # Important but not security-critical
        ),
        TopologyDomain.ONTOLOGY_DOMAIN: DomainPhysics(
            repulsion_threshold=0.70,     # Conservative baseline
            density_tolerance=0.60,
            max_nodes_soft_cap=25,
            compression_eligible=True,
            stabilization_priority=4
        ),
    }

    ONTOLOGY: Dict[NodeType, Dict[str, Any]] = {
        NodeType.EXPERIENCE_NODE: {
            "domain": TopologyDomain.EXPERIENCE_DOMAIN,
            "max_mutation_tier": MutationTier.TOPOLOGY,
            "boundary": CapabilityBoundary(
                allowed_proposers={"Sentinel"},
                allowed_validators={"topology_oracle"}
            ),
            "projection": ProjectionLegality(
                allowed_file_patterns=[],
                forbidden_file_patterns=["*"],  # In Memory Only
                target_format="json"
            )
        },
        NodeType.ENTITY_NODE: {
            "domain": TopologyDomain.ONTOLOGY_DOMAIN,
            "max_mutation_tier": MutationTier.TOPOLOGY,
            "boundary": CapabilityBoundary(
                allowed_proposers={"Sentinel"},
                allowed_validators={"topology_oracle"}
            ),
            "projection": ProjectionLegality(
                allowed_file_patterns=[],
                forbidden_file_patterns=["*"],  # In Memory Only
                target_format="json"
            )
        },
        NodeType.ROLE_NODE: {
            "domain": TopologyDomain.ONTOLOGY_DOMAIN,
            "max_mutation_tier": MutationTier.TOPOLOGY,
            "boundary": CapabilityBoundary(
                allowed_proposers={"Sentinel"},
                allowed_validators={"topology_oracle"}
            ),
            "projection": ProjectionLegality(
                allowed_file_patterns=[],
                forbidden_file_patterns=["*"],  # In Memory Only
                target_format="json"
            )
        },
        NodeType.RELATIONSHIP_NODE: {
            "domain": TopologyDomain.ONTOLOGY_DOMAIN,
            "max_mutation_tier": MutationTier.TOPOLOGY,
            "boundary": CapabilityBoundary(
                allowed_proposers={"Sentinel"},
                allowed_validators={"topology_oracle"}
            ),
            "projection": ProjectionLegality(
                allowed_file_patterns=[],
                forbidden_file_patterns=["*"],  # In Memory Only
                target_format="json"
            )
        },
        NodeType.CAPABILITY_NODE: {
            "domain": TopologyDomain.ONTOLOGY_DOMAIN,
            "max_mutation_tier": MutationTier.TOPOLOGY,
            "boundary": CapabilityBoundary(
                allowed_proposers={"Sentinel"},
                allowed_validators={"topology_oracle"}
            ),
            "projection": ProjectionLegality(
                allowed_file_patterns=[],
                forbidden_file_patterns=["*"],  # In Memory Only
                target_format="json"
            )
        },
        NodeType.ONTOLOGY_WORKFLOW_NODE: {
            "domain": TopologyDomain.ONTOLOGY_DOMAIN,
            "max_mutation_tier": MutationTier.TOPOLOGY,
            "boundary": CapabilityBoundary(
                allowed_proposers={"Sentinel"},
                allowed_validators={"topology_oracle"}
            ),
            "projection": ProjectionLegality(
                allowed_file_patterns=[],
                forbidden_file_patterns=["*"],  # In Memory Only
                target_format="json"
            )
        },
        NodeType.GOAL_NODE: {
            "domain": TopologyDomain.EXPERIENCE_DOMAIN,
            "max_mutation_tier": MutationTier.TOPOLOGY,
            "boundary": CapabilityBoundary(
                allowed_proposers={"Sentinel"},
                allowed_validators={"topology_oracle"}
            ),
            "projection": ProjectionLegality(
                allowed_file_patterns=[],
                forbidden_file_patterns=["*"],
                target_format="json"
            )
        },
        NodeType.JOURNEY_NODE: {
            "domain": TopologyDomain.EXPERIENCE_DOMAIN,
            "max_mutation_tier": MutationTier.TOPOLOGY,
            "boundary": CapabilityBoundary(
                allowed_proposers={"Sentinel"},
                allowed_validators={"topology_oracle"}
            ),
            "projection": ProjectionLegality(
                allowed_file_patterns=[],
                forbidden_file_patterns=["*"],
                target_format="json"
            )
        },
        NodeType.FLOW_NODE: {
            "domain": TopologyDomain.EXPERIENCE_DOMAIN,
            "max_mutation_tier": MutationTier.TOPOLOGY,
            "boundary": CapabilityBoundary(
                allowed_proposers={"Sentinel"},
                allowed_validators={"topology_oracle"}
            ),
            "projection": ProjectionLegality(
                allowed_file_patterns=[],
                forbidden_file_patterns=["*"],
                target_format="json"
            )
        },
        NodeType.SCREEN_NODE: {
            "domain": TopologyDomain.EXPERIENCE_DOMAIN,
            "max_mutation_tier": MutationTier.TOPOLOGY,
            "boundary": CapabilityBoundary(
                allowed_proposers={"Sentinel"},
                allowed_validators={"topology_oracle"}
            ),
            "projection": ProjectionLegality(
                allowed_file_patterns=[],
                forbidden_file_patterns=["*"],
                target_format="json"
            )
        },
        NodeType.ACTION_NODE: {
            "domain": TopologyDomain.EXPERIENCE_DOMAIN,
            "max_mutation_tier": MutationTier.TOPOLOGY,
            "boundary": CapabilityBoundary(
                allowed_proposers={"Sentinel"},
                allowed_validators={"topology_oracle"}
            ),
            "projection": ProjectionLegality(
                allowed_file_patterns=[],
                forbidden_file_patterns=["*"],
                target_format="json"
            )
        },
        NodeType.API_NODE: {
            "domain": TopologyDomain.DATA_DOMAIN,
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
            "domain": TopologyDomain.DATA_DOMAIN,
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
        NodeType.WORKSPACE_NODE: {
            "domain": TopologyDomain.UI_DOMAIN,
            "max_mutation_tier": MutationTier.TOPOLOGY,
            "boundary": CapabilityBoundary(
                allowed_proposers={"Sentinel"},
                allowed_validators={"topology_oracle"}
            ),
            "projection": ProjectionLegality(
                allowed_file_patterns=[],
                forbidden_file_patterns=["*"],  # In Memory Only
                target_format="json"
            )
        },
        NodeType.PAGE_NODE: {
            "domain": TopologyDomain.UI_DOMAIN,
            "max_mutation_tier": MutationTier.TOPOLOGY,
            "boundary": CapabilityBoundary(
                allowed_proposers={"Sentinel"},
                allowed_validators={"topology_oracle"}
            ),
            "projection": ProjectionLegality(
                allowed_file_patterns=[],
                forbidden_file_patterns=["*"],  # In Memory Only
                target_format="json"
            )
        },
        NodeType.FEATURE_NODE: {
            "domain": TopologyDomain.UI_DOMAIN,
            "max_mutation_tier": MutationTier.TOPOLOGY,
            "boundary": CapabilityBoundary(
                allowed_proposers={"Sentinel"},
                allowed_validators={"topology_oracle"}
            ),
            "projection": ProjectionLegality(
                allowed_file_patterns=[],
                forbidden_file_patterns=["*"],  # In Memory Only
                target_format="json"
            )
        },
        NodeType.NAV_LAYOUT_NODE: {
            "domain": TopologyDomain.UI_DOMAIN,
            "max_mutation_tier": MutationTier.TOPOLOGY,
            "boundary": CapabilityBoundary(
                allowed_proposers={"Sentinel"},
                allowed_validators={"topology_oracle"}
            ),
            "projection": ProjectionLegality(
                allowed_file_patterns=[],
                forbidden_file_patterns=["*"],  # In Memory Only
                target_format="json"
            )
        },
        NodeType.UI_NODE: {
            "domain": TopologyDomain.UI_DOMAIN,
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
            "domain": TopologyDomain.DATA_DOMAIN,
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
            "domain": TopologyDomain.UI_DOMAIN,
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
        NodeType.UI_STATE_NODE: {
            "domain": TopologyDomain.UI_DOMAIN,
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
        NodeType.DATA_STATE_NODE: {
            "domain": TopologyDomain.UI_DOMAIN,
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
            "domain": TopologyDomain.SECURITY_DOMAIN,
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
            "domain": TopologyDomain.DATA_DOMAIN,
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
            "domain": TopologyDomain.SECURITY_DOMAIN,
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
            "domain": TopologyDomain.RUNTIME_DOMAIN,
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
            "domain": TopologyDomain.RUNTIME_DOMAIN,
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
            "domain": TopologyDomain.SECURITY_DOMAIN,
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
            "domain": TopologyDomain.DATA_DOMAIN,
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

    # ── Accessors ─────────────────────────────────────────────

    @classmethod
    def get_max_mutation_tier(cls, node_type: NodeType) -> MutationTier:
        return cls.ONTOLOGY[node_type]["max_mutation_tier"]

    @classmethod
    def get_boundary(cls, node_type: NodeType) -> CapabilityBoundary:
        return cls.ONTOLOGY[node_type]["boundary"]

    @classmethod
    def get_projection(cls, node_type: NodeType) -> ProjectionLegality:
        return cls.ONTOLOGY[node_type]["projection"]

    # ── Phase 1 Domain Accessors ──────────────────────────────

    @classmethod
    def get_domain(cls, node_type: NodeType) -> TopologyDomain:
        """Return the TopologyDomain for a given NodeType."""
        return cls.ONTOLOGY[node_type]["domain"]

    @classmethod
    def get_physics(cls, node_type: NodeType) -> DomainPhysics:
        """Return the DomainPhysics envelope for a given NodeType's domain."""
        domain = cls.get_domain(node_type)
        return cls._DOMAIN_PHYSICS[domain]

    @classmethod
    def get_domain_physics(cls, domain: TopologyDomain) -> DomainPhysics:
        """Return the DomainPhysics envelope for a domain directly."""
        return cls._DOMAIN_PHYSICS[domain]

    @classmethod
    def get_nodes_for_domain(cls, domain: TopologyDomain) -> List[NodeType]:
        """Return all NodeTypes that belong to the given TopologyDomain."""
        return [
            nt for nt, entry in cls.ONTOLOGY.items()
            if entry["domain"] == domain
        ]
