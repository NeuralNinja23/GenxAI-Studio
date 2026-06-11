# app/studio/faculties/atlas_faculty.py
"""
Atlas Repair Faculty — Phase 5.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Optional

import numpy as np

from app.core.logging import log
from app.models.runtime_models import RepairContext, RepairIntent
from app.studio.architecture.workspace_architecture import WorkspaceArchitecture


# ─────────────────────────────────────────────────────────────
# Repair system prompt
# ─────────────────────────────────────────────────────────────

_ATLAS_REPAIR_PROMPT = """\
You are Atlas, a surgical code repair system for the Sentinel AI engine.

Your job is to identify ONE specific file to repair and produce a precise,
actionable repair instruction for an LLM re-emission agent.

You will receive:
  - A list of failure fingerprints (type, file, details)
  - The contents of the affected files
  - The current weighted loss score (oracle_before)
  - The active repair goals

Output ONLY valid JSON in this exact shape (no markdown, no explanation):
{
  "target_file": "<relative/path/to/file>",
  "instruction": "<clear, specific repair instruction>"
}

Rules:
  - Choose the single file most likely to reduce oracle loss if repaired.
  - The instruction must reference specific line numbers, imports, or constructs.
  - Do NOT include a 'scope' field — that is determined by the execution kernel.
  - Do NOT generate code in your response — only the instruction.
"""


# ─────────────────────────────────────────────────────────────
# Atlas Faculty
# ─────────────────────────────────────────────────────────────

class AtlasFaculty:
    """
    Repair Faculty.

    Static methods only — AtlasFaculty has no mutable state.
    The LLM client is always passed as a parameter.
    """

    @staticmethod
    def build_repair_context(
        failures: List[Any],
        state_fingerprint: np.ndarray,
        goals: List[str],
        oracle_before: float,
        workspace_root: Optional[Path] = None,
    ) -> RepairContext:
        """
        Build a RepairContext from the active failure set.
        """
        seen: set = set()
        affected_files: List[Path] = []

        for fp in failures:
            raw = getattr(fp, "file_path", None) or getattr(fp, "file", None)
            if not raw:
                continue
            if workspace_root:
                try:
                    p = WorkspaceArchitecture.resolve(workspace_root, raw)
                except Exception:
                    p = workspace_root / raw
            else:
                p = Path(raw)
            if str(p) in seen:
                continue
            seen.add(str(p))
            print(f"[ATLAS_DEBUG] raw={raw}")
            print(f"[ATLAS_DEBUG] workspace_root={workspace_root}")
            print(f"[ATLAS_DEBUG] resolved={p}")
            print(f"[ATLAS_DEBUG] exists={p.exists()}")
            if workspace_root:
                print(f"[ATLAS_DEBUG] workspace_exists={workspace_root.exists()}")
                print(f"[ATLAS_DEBUG] workspace_contents={list(workspace_root.iterdir())[:5] if workspace_root.exists() else 'MISSING'}")
            else:
                print(f"[ATLAS_DEBUG] workspace_exists=False")
                print(f"[ATLAS_DEBUG] workspace_contents=MISSING")
            if p.exists():
                affected_files.append(p)
            else:
                log("ATLAS", f"⚠️ Skipping non-existent file in RepairContext: {p}")

        log(
            "ATLAS",
            f"📋 RepairContext built: {len(affected_files)} affected files, "
            f"oracle_before={oracle_before:.2f}, goals={len(goals)}"
        )

        return RepairContext(
            affected_files=affected_files,
            failure_fingerprints=failures,
            state_fingerprint=state_fingerprint,
            goals=goals,
            oracle_before=oracle_before,
        )

    @staticmethod
    async def propose_repair_intent(
        context: RepairContext,
        llm_client: Any,
    ) -> Optional[RepairIntent]:
        """
        Propose a RepairIntent by asking the LLM to analyze RepairContext.
        """
        if not context.affected_files:
            log("ATLAS", "⚠️ No affected files in RepairContext — cannot propose repair intent.")
            return None

        # Build file content payload — only affected files, not the full workspace
        file_contents: dict = {}
        for path in context.affected_files:
            try:
                file_contents[str(path)] = path.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                log("ATLAS", f"⚠️ Could not read {path}: {e}")
                file_contents[str(path)] = f"[READ ERROR: {e}]"

        # Build failure fingerprint payload
        failure_data = []
        for fp in context.failure_fingerprints:
            failure_data.append({
                "failure_type": getattr(fp, "failure_type", "UNKNOWN"),
                "file":         str(getattr(fp, "file_path", None) or getattr(fp, "file", "unknown")),
                "details":      getattr(fp, "details", ""),
                "severity":     getattr(fp, "severity", 1.0),
            })

        user_message = json.dumps({
            "oracle_before":      context.oracle_before,
            "goals":              context.goals,
            "state_fingerprint":  context.state_fingerprint.tolist()
                                  if hasattr(context.state_fingerprint, "tolist")
                                  else list(context.state_fingerprint),
            "failure_fingerprints": failure_data,
            "file_contents":      file_contents,
        }, indent=2)

        log("ATLAS", f"🔍 Sending repair context to LLM ({len(context.affected_files)} files, "
                     f"oracle={context.oracle_before:.2f})")

        try:
            response = await llm_client.generate(
                system_prompt=_ATLAS_REPAIR_PROMPT,
                user_message=user_message,
            )
        except Exception as e:
            log("ATLAS", f"❌ LLM call failed in propose_repair_intent: {e}")
            return None

        # Parse LLM response
        try:
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]

            parsed = json.loads(cleaned.strip())

            target_file_raw = parsed.get("target_file")
            instruction = parsed.get("instruction", "").strip()

            if not target_file_raw or not instruction:
                log("ATLAS", f"❌ Incomplete LLM response: {parsed}")
                return None

            # Reject any response that tries to include a scope field
            if "scope" in parsed:
                log("ATLAS", "⚠️ LLM included 'scope' in response — ignored. Scope is kernel-controlled.")

            workspace_root = None
            if context.affected_files:
                for parent in context.affected_files[0].parents:
                    if (parent / "frontend").exists() or (parent / "backend").exists() or (parent / ".genx_staging").exists() or (parent / "Frontend").exists() or (parent / "Backend").exists():
                        workspace_root = parent
                        break
            if workspace_root:
                target_file = Path(WorkspaceArchitecture.to_workspace_relative(workspace_root, target_file_raw))
            else:
                target_file = Path(target_file_raw)

            intent = RepairIntent(target_file=target_file, instruction=instruction)
            log("ATLAS", f"✅ RepairIntent: target={target_file}, instruction={instruction[:80]}...")
            return intent

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            log("ATLAS", f"❌ Failed to parse Atlas LLM response: {e}\nRaw: {response[:300]}")
            return None
