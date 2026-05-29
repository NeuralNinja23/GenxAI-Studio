# app/sentinel/directive.py
"""
V4 IntentField System
=====================

IntentField is the bounded semantic substrate governing
topology evolution, runtime embodiment, compiler legality,
workflow coherence, and systemic software physics.

It DOES NOT define:
- raw source code,
- framework syntax,
- deterministic file blueprints,
- UI templates,
- application hardcoding.

It defines:
- behavioral topology constraints,
- runtime interaction physics,
- semantic pressure fields,
- workflow legality,
- ontology contracts,
- compiler invariants.

LLMs operate ONLY inside bounded topology cognition space.
Runtime remains the sole execution authority.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from pydantic import BaseModel, Field
from beanie import Document


# =========================================================
# Utilities
# =========================================================

def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# =========================================================
# Semantic Pressure Fields
# =========================================================

class SemanticPressureField(BaseModel):
    """
    Defines areas of semantic pressure that drive emerging topology mutations.
    E.g. Performance focus, visual hierarchy focus, or security focus.
    """
    focus_area: str
    gradient_vector: str
    strength: float = 1.0



# =========================================================
# Domain Schema Models
# =========================================================

class DomainField(BaseModel):
    name: str
    type: str
    required: bool = True
    indexed: bool = False
    unique: bool = False
    default: Optional[Any] = None


class DomainRelationship(BaseModel):
    relation_type: str
    target_entity: str
    required: bool = False


class DomainEntity(BaseModel):
    name: str
    description: Optional[str] = None
    fields: List[DomainField] = Field(default_factory=list)
    relationships: List[DomainRelationship] = Field(default_factory=list)


# =========================================================
# Workflow Legality
# =========================================================

class WorkflowLegalityRule(BaseModel):
    workflow_id: str

    allowed_transitions: Dict[str, List[str]] = Field(
        default_factory=dict
    )

    forbidden_states: List[str] = Field(
        default_factory=list
    )

    required_states: List[str] = Field(
        default_factory=list
    )


# =========================================================
# Runtime Constraints
# =========================================================

class RuntimeConstraints(BaseModel):
    supports_realtime: bool = False
    supports_websockets: bool = False
    supports_async_processing: bool = True
    supports_background_jobs: bool = False
    supports_transactions: bool = True
    supports_state_rehydration: bool = True
    supports_distributed_state: bool = False
    supports_streaming: bool = False
    supports_file_uploads: bool = False
    supports_notifications: bool = True
    supports_audit_trails: bool = True
    supports_search_indexing: bool = True
    supports_multi_tenant: bool = False
    supports_soft_delete: bool = True
    supports_rollback_recovery: bool = True


# =========================================================
# UX Constraints
# =========================================================

class UXConstraints(BaseModel):
    responsive: bool = True
    mobile_friendly: bool = True
    supports_dark_mode: bool = True
    supports_keyboard_navigation: bool = True
    supports_multi_panel_layouts: bool = True
    supports_drag_and_drop: bool = False
    supports_loading_states: bool = True
    supports_error_boundaries: bool = True
    supports_empty_states: bool = True
    supports_interactive_state: bool = True
    supports_modal_workflows: bool = True
    supports_navigation_shells: bool = True
    supports_filtering: bool = True
    supports_search: bool = True
    supports_sorting: bool = True
    supports_dashboard_views: bool = True
    supports_detail_views: bool = True


# =========================================================
# Data Constraints
# =========================================================

class DataConstraints(BaseModel):
    supports_crud: bool = True
    supports_relationships: bool = True
    supports_versioning: bool = False
    supports_aggregation: bool = False
    supports_caching: bool = True
    supports_query_invalidation: bool = True
    supports_optimistic_updates: bool = False
    supports_pagination: bool = True
    supports_full_text_search: bool = False
    supports_activity_tracking: bool = False
    supports_permissions: bool = True
    supports_role_based_access: bool = True


# =========================================================
# Compiler Constraints
# =========================================================

class CompilerConstraints(BaseModel):
    deterministic_compilation: bool = True
    strict_ast_only_projection: bool = True
    enforce_projection_hashes: bool = True
    prohibit_direct_llm_file_writes: bool = True
    require_renderable_views: bool = True
    require_state_bindings: bool = True
    require_route_connectivity: bool = True
    require_runtime_validation: bool = True
    require_oracle_validation: bool = True


# =========================================================
# Behavioral Archetypes
# =========================================================

class BehavioralArchetypes(BaseModel):
    crud_system: bool = True
    workflow_system: bool = False
    analytics_system: bool = False
    collaboration_system: bool = False
    realtime_system: bool = False
    content_management_system: bool = False
    notification_system: bool = True
    reporting_system: bool = False
    approval_system: bool = False
    audit_system: bool = True


# =========================================================
# Semantic Topology Contracts
# =========================================================

class TopologyContracts(BaseModel):
    """
    Compiler-aware semantic topology ontology.
    """

    semantic_nodes: List[str] = Field(default_factory=lambda: [
        "APPLICATION_SHELL",
        "NAVIGATION_RAIL",
        "HEADER_BAR",
        "CONTENT_VIEWPORT",
        "DATA_GRID",
        "FORM_LAYOUT",
        "DETAIL_VIEW",
        "LIST_VIEW",
        "FILTER_BAR",
        "SEARCH_CONTEXT",
        "STATE_COLLECTION",
        "QUERY_SOURCE",
        "ENTITY_SCHEMA",
        "API_RESOURCE",
        "WORKFLOW_CHAIN",
        "MODAL_CONTAINER",
        "NOTIFICATION_CENTER",
        "ACTIVITY_STREAM",
        "AUDIT_LOG",
        "LOADING_BOUNDARY",
        "ERROR_BOUNDARY",
        "REPORT_VIEW",
        "ANALYTICS_PANEL",
        "APPROVAL_FLOW",
        "ROLE_MATRIX",
        "PERMISSION_SCOPE",
        "TASK_CARD",
        "PIPELINE_STAGE",
        "KANBAN_COLUMN",
        "TIMELINE_VIEW",
        "CHAT_CONTEXT",
        "FILE_ATTACHMENT_CONTEXT"
    ])

    semantic_edges: List[str] = Field(default_factory=lambda: [
        "renders",
        "binds_state",
        "binds_route",
        "depends_on",
        "calls_api",
        "hydrates",
        "coordinates",
        "governs",
        "queries",
        "mutates",
        "streams_to",
        "subscribes_to",
        "authorizes",
        "transitions_to",
        "contains",
        "references",
        "aggregates",
        "notifies"
    ])


# =========================================================
# IntentField Root Object
# =========================================================

class IntentField(Document):
    """
    IntentField defines bounded systemic software physics.

    It stabilizes:
    - topology emergence,
    - semantic gravity,
    - workflow legality,
    - runtime coherence,
    - deterministic compilation contracts.

    It NEVER acts as:
    - application template system,
    - static UI generator,
    - filesystem authority.
    """

    # =====================================================
    # Identity
    # =====================================================

    project_id: str

    ux_intent: Dict[str, Any] = Field(
        default_factory=dict,
        description="Defines the overarching UX archetype and aesthetic boundaries"
    )


    # =====================================================
    # Human Semantic Intent
    # =====================================================

    original_request: Optional[str] = None

    semantic_summary: Optional[str] = None

    inferred_domains: List[str] = Field(default_factory=list)

    inferred_workflows: List[str] = Field(default_factory=list)

    inferred_interactions: List[str] = Field(default_factory=list)

    # =====================================================
    # Semantic Pressure Physics
    # =====================================================

    semantic_pressure_fields: List[SemanticPressureField] = Field(
        default_factory=list
    )


    # =====================================================
    # Runtime Constraints
    # =====================================================

    runtime_constraints: RuntimeConstraints = Field(
        default_factory=RuntimeConstraints
    )

    # =====================================================
    # UX Constraints
    # =====================================================

    ux_constraints: UXConstraints = Field(
        default_factory=UXConstraints
    )

    # =====================================================
    # Data Constraints
    # =====================================================

    data_constraints: DataConstraints = Field(
        default_factory=DataConstraints
    )

    # =====================================================
    # Compiler Constraints
    # =====================================================

    compiler_constraints: CompilerConstraints = Field(
        default_factory=CompilerConstraints
    )

    # =====================================================
    # Behavioral Archetypes
    # =====================================================

    behavioral_archetypes: BehavioralArchetypes = Field(
        default_factory=BehavioralArchetypes
    )

    # =====================================================
    # Topology Contracts
    # =====================================================

    topology_contracts: TopologyContracts = Field(
        default_factory=TopologyContracts
    )

    # =====================================================
    # Domain Entities
    # =====================================================

    domain_entities: List[DomainEntity] = Field(
        default_factory=list
    )

    # =====================================================
    # Workflow Legality
    # =====================================================

    workflow_legality: List[WorkflowLegalityRule] = Field(
        default_factory=list
    )

    # =====================================================
    # Global Invariants
    # =====================================================

    invariants: List[str] = Field(default_factory=lambda: [
        "No orphaned topology nodes may exist.",
        "All state collections must bind to valid runtime interactions.",
        "All API resources must remain reachable.",
        "All rendered views must remain structurally renderable.",
        "No circular topology dependencies are permitted.",
        "All runtime mutations must remain deterministic.",
        "AST projection is the sole filesystem authority.",
        "All topology mutations require oracle validation.",
        "Projection integrity hashes must remain stable across cycles.",
        "LLMs possess zero direct filesystem authority.",
        "Runtime remains the sole embodiment authority."
    ])

    # =====================================================
    # Expected Runtime Contracts
    # =====================================================

    expected_contracts: List[str] = Field(default_factory=lambda: [
        "CRUD_OPERATIONS",
        "STATE_HYDRATION",
        "ASYNC_FETCHING",
        "ERROR_HANDLING",
        "LOADING_BOUNDARIES",
        "ROUTE_CONNECTIVITY",
        "QUERY_INVALIDATION",
        "RUNTIME_VALIDATION"
    ])

    # =====================================================
    # Metadata
    # =====================================================

    governance_version: str = "v4"

    semantic_version: str = "4.0"

    created_at: datetime = Field(default_factory=utc_now)

    updated_at: datetime = Field(default_factory=utc_now)

    # =====================================================
    # MongoDB Settings
    # =====================================================

    class Settings:
        name = "intent_fields"