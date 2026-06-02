# app/agents/sub_agents.py
"""
V4 Cognitive Faculty System — Stage 6: Bounded LLM-Driven Cognition

Defines the live wired cognitive faculties calling Gemini via the unified
LLM adapter and parsing outputs strictly through PatchIRNormalizer.
"""

from typing import Any, Dict, List, Optional
import json
import uuid

from app.sentinel.cognition.patch_ir import PatchIR
from app.sentinel.cognition.branch import BranchState
from app.models.runtime_models import MutationTier
from app.sentinel.topology.project_graph import ProjectTopologyGraph

# Prompt and LLM imports
from app.llm.prompts import VICTORIA_PROMPT, DEREK_PROMPT, LUNA_PROMPT, MARCUS_PROMPT
from app.llm.adapter import call_llm
from app.sentinel.cognition.patch_ir_normalizer import PatchIRNormalizer
from app.core.logging import log
from pathlib import Path
from app.sentinel.verification.verification_gate import SentinelVerificationGate


def serialize_graph_for_llm(graph: ProjectTopologyGraph) -> str:
    """Serializes ProjectTopologyGraph into human-readable logical components, stripping file paths/code."""
    lines = []
    lines.append("=== CURRENT ACTIVE TOPOLOGY ===")
    
    for node_id, node in graph.nodes.items():
        lines.append(f"- Node: {node_id} ({node.node_type.value})")
        props = node.properties
        if node.node_type.value == "SCHEMA_NODE":
            lines.append(f"  Entity Name: {props.get('entity_name')}")
            lines.append(f"  Description: {props.get('description')}")
            fields = props.get('fields', [])
            fields_str = ", ".join([f"{f['name']}: {f['type']}" for f in fields])
            lines.append(f"  Fields: [{fields_str}]")
        elif node.node_type.value == "API_NODE":
            lines.append(f"  Router Name: {props.get('router_name')}")
            endpoints = props.get('endpoints', [])
            eps_str = ", ".join([f"{e['method']} {e['path']}" for e in endpoints])
            lines.append(f"  Endpoints: [{eps_str}]")
        elif node.node_type.value == "UI_NODE":
            lines.append(f"  Component Name: {props.get('component_name')}")
            lines.append(f"  Layout Type: {props.get('layout_type')}")
            lines.append(f"  Role: {props.get('role')}")
            bindings = props.get('state_bindings', [])
            bindings_str = ", ".join([f"{b['state_name']} ({b['binding_type']})" for b in bindings])
            lines.append(f"  State Bindings: [{bindings_str}]")
            
    for edge in graph.edges:
        lines.append(f"- Relationship: {edge.source_id} ==[{edge.relation}]==> {edge.target_id}")
        
    return "\n".join(lines)


class VictoriaUIFaculty:
    """
    Victoria: UI Faculty
    Suggests component layouts, navigation routes, and state bindings.
    """

    @staticmethod
    async def propose_mutations(
        branch: BranchState,
        description: str,
        intent: Any = None,
    ) -> List[PatchIR]:
        log("COGNITION", "Victoria UI Faculty analyzing intentions...")
        graph = branch.topology_graph

        user_prompt = f"""
USER INTENT / REQUEST:
{description}

{serialize_graph_for_llm(graph)}
"""
        from app.sentinel.cognition.mutation_engine import MutationEngine
        patches = await MutationEngine.critique_and_stabilize(
            prompt=user_prompt,
            system_prompt=VICTORIA_PROMPT,
            branch=branch,
            intent=intent
        )
        # [INSTRUMENT-A] Measure Victoria's output immediately after stabilization
        ui_patches = [p for p in patches if p.node_data and p.node_data.get("node_type") == "UI_NODE"]
        log("COGNITION", f"[VICTORIA-INSTRUMENT] raw_patches={len(patches)} | ui_node_patches={len(ui_patches)} | patch_ids={[p.patch_id for p in patches[:5]]}")
        return patches


class DerekAPIFaculty:
    """
    Derek: API Faculty
    Suggests API route paths, REST methods, and service wiring layers.
    """

    @staticmethod
    async def propose_mutations(
        branch: BranchState,
        description: str,
        intent: Any = None,
    ) -> List[PatchIR]:
        log("COGNITION", "Derek API Faculty analyzing routing requirements...")
        graph = branch.topology_graph

        user_prompt = f"""
USER INTENT / REQUEST:
{description}

{serialize_graph_for_llm(graph)}
"""
        from app.sentinel.cognition.mutation_engine import MutationEngine
        return await MutationEngine.critique_and_stabilize(
            prompt=user_prompt,
            system_prompt=DEREK_PROMPT,
            branch=branch,
            intent=intent
        )


class LunaSchemaFaculty:
    """
    Luna: Database Schema Faculty
    Suggests entity structures, indexes, and standard data definitions.
    """

    @staticmethod
    async def propose_mutations(
        branch: BranchState,
        description: str,
        intent: Any = None,
    ) -> List[PatchIR]:
        log("COGNITION", "Luna Database Schema Faculty designing entity bounds...")
        graph = branch.topology_graph

        user_prompt = f"""
USER INTENT / REQUEST:
{description}

{serialize_graph_for_llm(graph)}
"""
        from app.sentinel.cognition.mutation_engine import MutationEngine
        return await MutationEngine.critique_and_stabilize(
            prompt=user_prompt,
            system_prompt=LUNA_PROMPT,
            branch=branch,
            intent=intent
        )


class ReggieWorkflowFaculty:
    """
    Reggie: Workflow Faculty (Adaptive Fallback)
    Suggests transitions and logical state workflow diagrams.
    """

    @staticmethod
    async def propose_mutations(
        branch: BranchState,
        description: str,
        intent: Any = None,
    ) -> List[PatchIR]:
        # Fallback to simple topology additions for stages
        workflow_id = f"workflow_{uuid.uuid4().hex[:6]}"
        return [
            PatchIR(
                patch_id=f"reggie-wf-{uuid.uuid4().hex[:6]}",
                target_node_id=workflow_id,
                mutation_tier=MutationTier.TOPOLOGY,
                action="ADD_NODE",
                node_data={
                    "node_type": "WORKFLOW_NODE",
                    "properties": {
                        "workflow_name": "EmergencyFallbackWorkflow",
                        "states": ["IDLE", "RUNNING", "COMPLETED"],
                        "description": description,
                    }
                },
            )
        ]


class MarcusGovernanceAnalyst:
    """
    Marcus: Governance Conscience
    Reviews proposed transformations, returning soft warnings and AttentionRouter advice.
    """

    @staticmethod
    async def analyze_governance(
        branch: BranchState,
        drift_severity: str = "CLEAN",
    ) -> Dict[str, Any]:
        log("COGNITION", "Marcus Governance Conscience conducting structural checks...")
        
        # S-0.6C decoupled in-memory verifier avoiding empty staging workspace file checks
        from app.sentinel.verification.verification_gate import MarcusTopologyVerifier
        verification = MarcusTopologyVerifier.verify(branch.topology_graph)
        
        # Prepare evaluation profile based strictly on technical verification metrics
        raw_prompt = f"""
Evaluate branch '{branch.branch_id}' converging with drift '{drift_severity}'.
Repulsion Metric: {branch.repulsion_score}
Entropy History: {branch.entropy_history}

TECHNICAL VERIFICATION METRICS:
- Topology Cohesion: {verification.topology_survival * 100}%
- Schema Integrity: {verification.schema_survival * 100}%
- State Binding: {verification.state_survival * 100}%
- Route Validity: {verification.route_survival * 100}%
- Graph Dependency: {verification.dependency_graph_survival * 100}%

Integrated Verification Score: {verification.verification_score}
Gate Recommendation: {"PASS" if verification.verification_score >= 0.70 else "REJECT"}
"""
        # Default fallback
        governance_result = {
            "branch_id": branch.branch_id,
            "marcus_advisory_modifier": 1.0,
            "warnings": [],
            "is_stable": True
        }

        try:
            raw_response = await call_llm(
                prompt=raw_prompt,
                system_prompt=MARCUS_PROMPT,
                temperature=0.1
            )
            
            # Clean markdown if returned
            cleaned = raw_response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            parsed = json.loads(cleaned)
            
            decision = parsed.get("governance_decision", "ALLOW")
            
            metrics = parsed.get("metrics") or {}
            branch_entropy_val = metrics.get("branch_entropy")
            if branch_entropy_val is None:
                branch_entropy_val = 0.1
            modifier = float(branch_entropy_val)
            
            warnings = [issue.get("description") for issue in parsed.get("issues", [])]
            
            governance_result["marcus_advisory_modifier"] = 0.2 if decision == "REJECT" else 0.6 if decision == "ADVISE_CAUTION" else 1.0
            governance_result["warnings"] = warnings
            governance_result["is_stable"] = decision != "REJECT"

            # Parse Phase 10 Holistic Review Scores
            default_holistic = {
                "code_review": {"score": 1.0, "comment": "Baseline clean code review."},
                "ux_review": {"score": 1.0, "comment": "Baseline clean UX flow structure."},
                "navigation_review": {"score": 1.0, "comment": "Baseline coherent route paths."},
                "design_review": {"score": 1.0, "comment": "Baseline clean layout alignment."},
                "accessibility_review": {"score": 1.0, "comment": "Baseline accessible component boundaries."}
            }
            
            holistic = parsed.get("holistic_reviews") or {}
            for key in default_holistic.keys():
                if key not in holistic or not isinstance(holistic[key], dict):
                    holistic[key] = default_holistic[key]
                else:
                    if "score" not in holistic[key]:
                        holistic[key]["score"] = default_holistic[key]["score"]
                    else:
                        try:
                            holistic[key]["score"] = float(holistic[key]["score"])
                        except Exception:
                            holistic[key]["score"] = default_holistic[key]["score"]
                    if "comment" not in holistic[key]:
                        holistic[key]["comment"] = default_holistic[key]["comment"]
            
            governance_result["holistic_reviews"] = holistic

        except Exception as e:
            log("COGNITION", f"⚠️ Marcus analysis failure: {e}. Falling back to baseline calculations.")
            
            # Deterministic backup formulas
            modifier = 1.0
            warnings = []
            is_stable = True

            if branch.repulsion_score > 0.6:
                modifier *= 0.5
                warnings.append("Severe repulsion index failure.")
                is_stable = False

            if len(branch.entropy_history) >= 3:
                h = branch.entropy_history
                if h[-1] > h[-2] and h[-2] < h[-3]:
                    modifier *= 0.7
                    warnings.append("Entropy oscillation detected.")
                    is_stable = False

            governance_result["marcus_advisory_modifier"] = modifier
            governance_result["warnings"] = warnings
            governance_result["is_stable"] = is_stable
            
            # Phase 10 Deterministic Fallback Holistic Review Scores
            governance_result["holistic_reviews"] = {
                "code_review": {"score": modifier, "comment": "Deterministic backup code review."},
                "ux_review": {"score": modifier, "comment": "Deterministic backup UX flow review."},
                "navigation_review": {"score": modifier, "comment": "Deterministic backup navigation review."},
                "design_review": {"score": modifier, "comment": "Deterministic backup design review."},
                "accessibility_review": {"score": modifier, "comment": "Deterministic backup accessibility review."}
            }

        return governance_result

    @staticmethod
    async def evaluate_failures(failures: List[Any], drift_severity: str = "CLEAN") -> Dict[str, Any]:
        """
        Evaluates projection failures directly to determine if they are recoverable.
        Returns:
            {
                "decision": "REPAIR" | "REJECT",
                "repair_strategy": str
            }
        """
        log("COGNITION", f"Marcus Governance analyzing {len(failures)} failures for repair strategy...")
        if not failures:
            return {"decision": "REPAIR", "repair_strategy": "No failures detected."}
        
        # Build evaluation context
        context_lines = []
        for i, f in enumerate(failures):
            context_lines.append(f"Failure {i+1}:")
            context_lines.append(f"  Type: {getattr(f, 'failure_type', 'UNKNOWN')}")
            context_lines.append(f"  Stage: {getattr(f, 'stage', 'UNKNOWN')}")
            context_lines.append(f"  Details: {getattr(f, 'details', 'None')}")
            context_lines.append("")
            
        failure_context = "\n".join(context_lines)
        
        raw_prompt = f"""
We have encountered the following projection failures:

{failure_context}

Based on Sentinel architectural principles:
1. If the failures indicate a fundamentally flawed or unsalvageable architecture (e.g. infinite loops, unrecoverable constraints), return REJECT.
2. If the failures are repairable through topology mutation or component rewriting (e.g. missing bindings, syntax errors, missing handlers), return REPAIR.

Respond in JSON format:
{{
    "decision": "REPAIR" or "REJECT",
    "repair_strategy": "A brief explanation of how the cognitive faculties should address this failure (e.g. 'Add a state node and bind to UI component')."
}}
"""
        
        try:
            raw_response = await call_llm(
                prompt=raw_prompt,
                system_prompt=MARCUS_PROMPT,
                temperature=0.1
            )
            
            cleaned = raw_response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            parsed = json.loads(cleaned)
            
            decision = parsed.get("decision", "REPAIR")
            if decision not in ["REPAIR", "REJECT"]:
                decision = "REPAIR"
                
            return {
                "decision": decision,
                "repair_strategy": parsed.get("repair_strategy", "Proceed with standard mutation fallbacks.")
            }
            
        except Exception as e:
            log("COGNITION", f"⚠️ Marcus failure analysis exception: {e}. Defaulting to REPAIR.")
            return {
                "decision": "REPAIR",
                "repair_strategy": "Default deterministic fallback: trigger standard mutation."
            }