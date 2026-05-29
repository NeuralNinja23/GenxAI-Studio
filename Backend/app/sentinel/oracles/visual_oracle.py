# app/oracles/visual_oracle.py
"""
V4 Visual Oracle — Stage 4: Oracle Layer

SOFT-STRUCTURAL Oracle checking layout DOM containers, accessibility, and Tailwind classes.
"""

from pathlib import Path
from typing import Any
import re
import uuid

from app.core.logging import log
from app.sentinel.oracles.base import BaseOracle, OracleResult

class VisualOracle(BaseOracle):
    """
    Structural UI Advisory Oracle (SOFT).
    Asserts layout spacing, Tailwind keyword spelling, and HTML accessibility tags.
    """

    def __init__(self):
        super().__init__(name="visual_oracle", is_hard=False)

    async def validate(self, project_id: str, project_path: Path, cycle_ctx: Any) -> OracleResult:
        log("ORACLE", f"🔍 Running Visual Oracle soft structural checks on {project_id}")

        frontend_src = project_path / "Frontend" / "src"
        if not frontend_src.exists():
            return OracleResult(
                passed=True,
                reason="Soft visual checks skipped: no frontend src files configured.",
                evidence_key=f"ev-visual-skip-{str(uuid.uuid4())[:8]}"
            )

        violations = []
        files_checked = 0

        # Scan for TSX files
        for p in frontend_src.glob("**/*.tsx"):
            files_checked += 1
            try:
                with open(p, "r", encoding="utf-8") as f:
                    content = f.read()

                # Rule 1: Check Tailwind class validity (simple spell-check for common classes)
                # Look for className="..." blocks
                class_names = re.findall(r"className=['\"]([^'\"]+)['\"]", content)
                for cn in class_names:
                    words = cn.split()
                    for w in words:
                        # Simple rule check: alert on raw numbers without bounds
                        if w.startswith("p-") or w.startswith("m-") or w.startswith("w-") or w.startswith("h-"):
                            val = w.split("-")[-1]
                            if not val.isdigit() and val not in ["auto", "full", "screen", "min", "max", "fit"]:
                                violations.append(f"Mispelled/Invalid Tailwind spacing utility '{w}' inside {p.name}")

                # Rule 2: Ensure basic accessibility tags (alt in <img>)
                img_tags = re.findall(r"<img\s+[^>]*>", content)
                for img in img_tags:
                    if "alt=" not in img:
                        violations.append(f"Accessibility violation: <img> tag lacks 'alt' attribute in {p.name}")

            except Exception as read_err:
                violations.append(f"Could not read {p.name} for visual assertions: {read_err}")

        passed = len(violations) == 0
        reason = "All frontend components adhere to Tailwind and structural spacing guidelines." if passed else f"Visual structural recommendations: {violations}"
        evidence_key = f"ev-visual-pass-{str(uuid.uuid4())[:8]}" if passed else f"ev-visual-advisory-{str(uuid.uuid4())[:8]}"

        return OracleResult(
            passed=True,  # SOFT Oracle always passes cycle validation, regardless of violations count
            reason=reason,
            metrics={"files_checked": files_checked, "advisories_count": len(violations)},
            evidence_key=evidence_key
        )
