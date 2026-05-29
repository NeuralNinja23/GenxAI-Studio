# app/sentinel/cognition/intent_parser.py
"""
V4 Bounded Cognition — Phase 5: User Intent Salience Mapping & Anchoring

Implements a semantic parsing pass to extract core intent vectors (nouns/verbs)
from user requests and injects semantic pressure anchoring into the IntentField.
"""

from typing import List, Dict, Any
import json
from pydantic import BaseModel
from app.sentinel.directives import IntentField, SemanticPressureField
from app.llm.adapter import call_llm
from app.core.logging import log

INTENT_PARSER_SYSTEM_PROMPT = """
You are the Intent Salience Parser for Sentinel.
Given a user's natural language request, extract the fundamental semantic nouns (targets) and verbs (actions).
Then, determine the primary "Semantic Pressure" gradient that should be applied to the system's topology.

Output strictly valid JSON with the following structure:
{
  "extracted_verbs": ["create", "update", "style", "delete", etc],
  "extracted_nouns": ["dashboard", "navbar", "database", "login form", etc],
  "pressure_fields": [
    {
      "focus_area": "visual_hierarchy|security|performance|data_flow",
      "gradient_vector": "increase_density|simplify|add_boundaries|optimize_state",
      "strength": 0.0 to 1.0
    }
  ]
}
"""

class IntentParser:
    """
    Parses natural language requests to anchor topological priorities.
    """

    @staticmethod
    async def parse_and_anchor_intent(user_request: str, intent_field: IntentField) -> IntentField:
        """
        Extracts semantic salience from the user request and anchors it into the IntentField
        via SemanticPressureFields and updated UX invariants.
        """
        log("COGNITION", "🎯 Executing User Intent Salience Mapping pass...")

        try:
            raw_response = await call_llm(
                prompt=f"USER REQUEST:\n{user_request}",
                system_prompt=INTENT_PARSER_SYSTEM_PROMPT,
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

            verbs = parsed.get("extracted_verbs", [])
            nouns = parsed.get("extracted_nouns", [])
            pressure_data = parsed.get("pressure_fields", [])

            log("COGNITION", f"🎯 Intent Anchors Extracted | Verbs: {verbs} | Targets: {nouns}")

            # Create SemanticPressureFields
            new_pressures = []
            for p in pressure_data:
                sp = SemanticPressureField(
                    focus_area=p.get("focus_area", "visual_hierarchy"),
                    gradient_vector=p.get("gradient_vector", "simplify"),
                    strength=float(p.get("strength", 0.5))
                )
                new_pressures.append(sp)

            # Anchor new pressures (replacing old ones to reflect the latest active request)
            intent_field.semantic_pressure_fields = new_pressures
            
            # Store raw extracted salience in ux_intent
            if not hasattr(intent_field, "ux_intent") or intent_field.ux_intent is None:
                intent_field.ux_intent = {}
            intent_field.ux_intent["active_verbs"] = verbs
            intent_field.ux_intent["active_nouns"] = nouns

            # Add anchoring invariant for primary nouns
            if nouns:
                primary_target = nouns[0]
                anchor_invariant = f"Must preserve salience and topological integrity of '{primary_target}'"
                if anchor_invariant not in intent_field.invariants:
                    intent_field.invariants.append(anchor_invariant)

            return intent_field

        except Exception as e:
            log("COGNITION", f"⚠️ Intent Parser failed, falling back to neutral bounds: {e}")
            return intent_field
