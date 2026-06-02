# app/sentinel/verification/marcus_governance_analyst.py
"""
Marcus V2: Grounded Governance Analyst
Translates deterministic outputs from the Sentinel Execution Oracle 
(VerificationResult) into structured, actionable mutation directives for LLM actuators.
"""

from typing import Dict, Any, List
from app.sentinel.verification.verification_gate import VerificationResult, FailureFingerprint

class MarcusGovernanceAnalyst:
    """
    Analyzes the deterministic survival metrics and failure geometries 
    produced by the Sentinel Verification Gate. 
    """

    @staticmethod
    def analyze(verification_result: VerificationResult) -> Dict[str, Any]:
        print("[MARCUS_V2] 🧠 Analyzing Execution Oracle Result...")

        if verification_result.recommendation == "PASS" and verification_result.verification_score == 1.0:
            print("[MARCUS_V2] ✅ Total System Convergence achieved. Approving transaction.")
            try:
                from app.sentinel.validation.validation_recorder import ValidationRecorder
                ValidationRecorder.record_governance_event({
                    "branch_id": None,
                    "governance_rule": "S-0 Full Integrity",
                    "score_before": verification_result.verification_score,
                    "score_after": verification_result.verification_score,
                    "action": "APPROVED",
                    "reason": "Total System Convergence achieved"
                })
            except Exception:
                pass
            return {
                "status": "APPROVED",
                "confidence": verification_result.verification_score,
                "directive": "PROCEED_TO_COMMIT",
                "mutation_plan": None
            }

        # 2. Failure Geometry Extraction
        print(f"[MARCUS_V2] ❌ Oracle rejected state. Survival: {verification_result.overall_survival:.2f}. Class: {verification_result.failure_classification}")
        
        primary_fault = verification_result.failure_classification or "UNKNOWN_FAULT"
        critical_failures = verification_result.failures

        # 3. Formulate Mutation Directive based on deterministic truth
        mutation_plan = MarcusGovernanceAnalyst._formulate_mutation(primary_fault, critical_failures)

        try:
            from app.sentinel.validation.validation_recorder import ValidationRecorder
            ValidationRecorder.record_governance_event({
                "branch_id": None,
                "governance_rule": primary_fault,
                "score_before": verification_result.verification_score,
                "score_after": verification_result.verification_score,
                "action": "MUTATION_DIRECTIVE_ISSUED",
                "reason": f"Survival: {verification_result.overall_survival:.2f}"
            })
        except Exception:
            pass

        return {
            "status": "REJECTED",
            "confidence": verification_result.verification_score,
            "primary_fault": primary_fault,
            "directive": "EXECUTE_MUTATION",
            "mutation_plan": mutation_plan,
            "telemetry": {
                "overall_survival": verification_result.overall_survival,
                "governance_score": verification_result.governance_score,
                "failed_layers": MarcusGovernanceAnalyst._extract_failed_layers(verification_result)
            }
        }

    @staticmethod
    def _extract_failed_layers(result: VerificationResult) -> List[str]:
        """Identifies exactly which S-0 layers failed for telemetry."""
        failed = []
        if not result.dependency_passed: failed.append("Layer A: Dependency")
        if not result.schema_passed: failed.append("Layer B: Schema")
        if not result.state_binding_passed: failed.append("Layer C: State Binding")
        if not result.build_passed: failed.append("Layer D: Build Integrity")
        if not result.runtime_passed or not result.visual_passed: failed.append("Layer E: Runtime/Visual")
        if not result.topology_passed: failed.append("Layer F: Topology")
        return failed

    @staticmethod
    def _formulate_mutation(primary_fault: str, failures: List[FailureFingerprint]) -> str:
        """
        Translates specific FailureFingerprints into explicit prompt directives
        to force the LLM into a corrective path without letting it hallucinate the problem.
        """
        if not failures:
            return "System validation failed. Review global constraints and regenerate."

        # Grab the most critical failure to drive the primary mutation
        primary = failures[0]
        component_ctx = f" in component '{primary.component}'" if primary.component else ""
        file_ctx = f" (File: {primary.file})" if primary.file else ""

        # Construct specific repulsion prompts based on our S-0 taxonomy
        if primary_fault == "UNRESOLVED_IMPORT_FAILURE":
            return f"CRITICAL: Failed to resolve import '{primary.details}'{component_ctx}. You must ensure all imports point to existing files in the frontend/src space. Do not hallucinate paths."
            
        elif primary_fault == "SCHEMA_CONTRACT_FAILURE":
            return f"CRITICAL: Schema violation{component_ctx}. {primary.details}. You must restrict your data access and prop drilling strictly to the attributes defined in the target schema contract."
            
        elif primary_fault == "UNRESOLVED_EVENT_HANDLER":
            return f"CRITICAL: Interactive trigger mismatch{component_ctx}. {primary.details}. You defined an event (like onClick) but the handler is missing from the scope. You must implement the handler."
            
        elif primary_fault == "STATE_MUTATION_MISSING":
            return f"CRITICAL: Ghost action detected{component_ctx}. {primary.details}. The handler executes but does not mutate state or trigger an API. You must connect this handler to a real state dispatcher or API call."
            
        elif primary_fault == "INVALID_STATE_TARGET":
            return f"CRITICAL: Domain cross-contamination{component_ctx}. {primary.details}. You are mutating state that belongs to a different schema domain. Isolate state mutations to their respective boundaries."
            
        elif primary_fault == "ORPHANED_STATE_MUTATION":
            return f"CRITICAL: Unconsumed state{component_ctx}. {primary.details}. You are mutating a state variable that is never mapped to the UI. If a state is mutated, it MUST be projected into the render tree."
            
        elif primary_fault == "FRONTEND_BUILD_FAILURE":
            return f"CRITICAL: Structural React/TSX syntax error{file_ctx}. {primary.details}. Ensure all curly braces, parentheses, JSX tags, and brackets are perfectly balanced. Do not use 'undefined' as a literal."
            
        elif primary_fault == "BACKEND_BUILD_FAILURE":
            return f"CRITICAL: Python syntax failure{file_ctx}. {primary.details}. Ensure valid Python 3 syntax."
            
        elif primary_fault == "RUNTIME_BOOT_FAILURE":
            return f"CRITICAL: Sandbox render crash. {primary.details}. Ensure App.tsx exists, has a valid default export, and returns a valid JSX element."
            
        elif primary_fault == "VISUAL_RENDER_FAILURE":
            return f"CRITICAL: Visual abstraction failure. {primary.details}. The UI is rendering blank or hidden. Ensure components are actively returned and not styled with display: none."
            
        elif primary_fault == "TOPOLOGY_INTEGRITY_FAILURE":
            return f"CRITICAL: Architectural drift. {primary.details}. The generated graph does not match the intent topology. Ensure all modules are connected and accessible from the root layout."

        elif primary_fault == "VERIFICATION_TIMEOUT_FAILURE":
            return "CRITICAL: Execution oracle timed out. The generated code likely contains an infinite loop, excessive dependencies, or computationally intractable patterns. Simplify the logic."

        # Fallback
        return f"CRITICAL: Validation failed during {primary.stage}. Details: {primary.details}. Re-align with strict execution constraints."