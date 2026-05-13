# app/orchestration/phase_review.py
"""
Phase Review Function.

INVARIANTS:
- Never halts
- Never retries
- Never decides
- Only observes and returns structured report
"""

from pathlib import Path
from typing import List, Optional
import json

from app.core.logging import log
from app.orchestration.review_report import ReviewReport, empty_review


# Marcus Review Prompt - OBSERVATION ONLY
MARCUS_REVIEW_PROMPT = """You are Marcus, a code quality observer.

YOUR ROLE:
You are reviewing artifacts from a completed workflow phase.
You may ONLY describe observations.

CRITICAL CONSTRAINTS:
- You may NOT suggest retries, fixes, or actions
- You may NOT say "this should be changed to..."
- You may NOT recommend next steps
- You may NOT pass or fail anything
- You are a WITNESS, not a JUDGE

OUTPUT FORMAT (JSON only):
{
    "strengths": ["observation 1", "observation 2"],
    "weaknesses": ["observation 1", "observation 2"],
    "missing_elements": ["element 1", "element 2"],
    "inconsistencies": ["inconsistency 1", "inconsistency 2"],
    "risks": ["risk 1", "risk 2"],
    "summary": "A neutral summary of what was observed."
}

RULES FOR EACH FIELD:
- strengths: What is well-implemented or clear
- weaknesses: What is poorly implemented or unclear
- missing_elements: What was expected but not present
- inconsistencies: Contradictions between artifacts
- risks: Potential issues that may cause problems later
- summary: 2-3 sentences describing the overall state

DO NOT include:
- Recommendations
- Action items
- Pass/fail judgments
- Quality scores
- Suggestions for improvement

You are describing reality. Nothing more."""


async def run_phase_review(
    phase_name: str,
    artifacts: List[Path],
    intent: str,
    prior_reviews: List[ReviewReport],
) -> ReviewReport:
    """
    Run Marcus review on phase artifacts.
    
    INVARIANTS:
    - Never halts execution
    - Never retries on failure
    - Never makes decisions
    - Returns empty_review on any error
    
    Args:
        phase_name: Name of the phase being reviewed
        artifacts: Paths to generated files
        intent: Original user request
        prior_reviews: Reviews from previous phases (for context)
    
    Returns:
        ReviewReport (always - never raises)
    """
    from app.llm import call_llm
    from app.core.config import settings
    
    log("MARCUS", f"📋 Reviewing phase: {phase_name}")
    
    try:
        # Build artifact context
        artifact_content = []
        for artifact_path in artifacts[:10]:  # Limit to 10 files
            try:
                if artifact_path.exists():
                    content = artifact_path.read_text(encoding="utf-8")
                    artifact_content.append(f"### {artifact_path.name}\n```\n{content[:2000]}\n```")
            except Exception:
                pass
        
        if not artifact_content:
            log("MARCUS", "⚠️ No artifacts to review")
            return empty_review(phase_name)
        
        # Build prior review context
        prior_context = ""
        if prior_reviews:
            prior_context = "\n\n## Prior Phase Reviews:\n"
            for pr in prior_reviews[-3:]:  # Last 3 reviews
                prior_context += f"\n{pr.to_evidence_string()}\n"
        
        # Build user prompt
        user_prompt = f"""## Phase: {phase_name}

## Original Intent:
{intent[:500]}

{prior_context}

## Artifacts to Review:
{chr(10).join(artifact_content)}

Provide your observations in the specified JSON format."""

        # Call Marcus (LLM)
        result = await call_llm(
            prompt=user_prompt,
            provider=settings.llm.default_provider,
            model=settings.llm.default_model,
            system_prompt=MARCUS_REVIEW_PROMPT,
            temperature=0.1,  # Low temperature for consistency
            max_tokens=2000,
        )
        
        # Parse response
        raw = result if isinstance(result, str) else result.get("text", "")
        
        # Clean JSON from markdown fences
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            if lines[-1].strip() == "```":
                cleaned = "\n".join(lines[1:-1])
            else:
                cleaned = "\n".join(lines[1:])
        
        # Parse JSON
        data = json.loads(cleaned)
        
        # Build ReviewReport (ignore any action-oriented fields)
        review = ReviewReport(
            phase=phase_name,
            strengths=data.get("strengths", [])[:5],
            weaknesses=data.get("weaknesses", [])[:5],
            missing_elements=data.get("missing_elements", [])[:5],
            inconsistencies=data.get("inconsistencies", [])[:5],
            risks=data.get("risks", [])[:5],
            summary=data.get("summary", "")[:500],
        )
        
        log("MARCUS", f"✅ Review complete: {len(review.strengths)} strengths, {len(review.weaknesses)} weaknesses")
        return review
        
    except json.JSONDecodeError as e:
        log("MARCUS", f"⚠️ Failed to parse review JSON: {e}")
        return empty_review(phase_name)
    except Exception as e:
        log("MARCUS", f"⚠️ Review failed (non-fatal): {e}")
        return empty_review(phase_name)
