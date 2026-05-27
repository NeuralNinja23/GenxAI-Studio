# app/models/directive.py
"""
V4 Directive / Intent Field System — Stage 2: Canonical Topology Engine

Defines the boundary-based IntentField model. This is NOT a rigid blueprint,
but a semantic boundary field that defines invariants, constraints, UX intent,
workflow legality, semantic pressure fields, and topology boundaries.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from beanie import Document, Indexed
from pydantic import BaseModel, Field
import uuid

from app.core.time import utc_now

class DomainEntityField(BaseModel):
    name: str
    type: str
    required: bool = True
    description: Optional[str] = None


class DomainEntity(BaseModel):
    name: str
    description: str
    fields: List[DomainEntityField] = Field(default_factory=list)


class SemanticConstraint(BaseModel):
    rule_id: str
    description: str
    severity: str = "HARD"  # HARD or SOFT
    validation_target: str  # e.g. "API", "UI", "DB"


class WorkflowLegalityRule(BaseModel):
    """Defines valid workflow paths and forbidden edge states."""
    workflow_id: str
    allowed_transitions: List[str] = Field(default_factory=list)
    forbidden_states: List[str] = Field(default_factory=list)


class SemanticPressureField(BaseModel):
    """
    Defines areas of semantic pressure that drive emerging topology mutations.
    E.g. Performance focus, visual hierarchy focus, or security focus.
    """
    focus_area: str  # e.g. "security", "responsiveness", "performance"
    gradient_vector: str  # direction of desired evolutionary mutation
    strength: float = 1.0  # magnitude of constraint pressure


class IntentField(Document):
    """
    The Semantic Boundary Field for Computational Emergence.

    Instead of defining a deterministic blueprint of files, this field defines
    the legal boundaries, semantic invariants, and attraction fields that
    guide the self-directed convergence of the ProjectTopologyGraph.
    """
    intent_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: Indexed(str, unique=True)
    version: int = 1

    # UX Intent
    ux_intent: Dict[str, Any] = Field(
        default_factory=dict,
        description="Defines the overarching UX archetype (e.g. SaaS dashboard) and aesthetic boundaries"
    )

    # Invariants (What MUST hold true under all topologies)
    invariants: List[str] = Field(
        default_factory=list,
        description="Immutable invariants that no mutation may ever violate"
    )

    # Hard & Soft Constraints
    constraints: List[SemanticConstraint] = Field(
        default_factory=list,
        description="Structural rules and semantic boundaries governing the system"
    )

    # Workflow Legality Boundaries
    workflow_legality: List[WorkflowLegalityRule] = Field(
        default_factory=list,
        description="State machine and legal transition constraints for workflows"
    )

    # Semantic Pressure Fields
    semantic_pressure_fields: List[SemanticPressureField] = Field(
        default_factory=list,
        description="Pressure gradients that deform topology search space to favor certain patterns"
    )

    # Abstract Domain boundaries
    domain_entities: List[DomainEntity] = Field(default_factory=list)
    expected_contracts: List[str] = Field(default_factory=list)
    deployment_target: str = "docker_local"

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "intent_fields"

    def verify_invariant(self, rule_check_fn) -> bool:
        """Evaluate if the current state satisfies all semantic invariants."""
        # Pure abstract boundary verification helper
        return all(rule_check_fn(inv) for inv in self.invariants)
