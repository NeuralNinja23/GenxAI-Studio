# app/cognition/patch_ir.py
"""
V4 Bounded Cognition — Stage 6: Minimal Cognition
Defines the PatchIR (Intermediate Representation) payload wrapper for guided topological changes.
"""

import uuid
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from app.models.runtime_models import MutationTier

class PatchIR(BaseModel):
    """
    Intermediate Representation (IR) of a proposed topological change.
    Cognition emits this payload, completely decoupling logical suggestions
    from raw filesystem writes.
    """
    patch_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    target_node_id: str
    mutation_tier: MutationTier
    action: str  # "ADD_NODE", "REMOVE_NODE", "UPDATE_NODE", "ADD_EDGE", "REMOVE_EDGE"
    node_data: Optional[Dict[str, Any]] = Field(default_factory=dict)
    edge_data: Optional[Dict[str, Any]] = Field(default_factory=dict)
