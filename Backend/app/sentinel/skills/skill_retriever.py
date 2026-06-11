import os
from typing import List, Dict
from pathlib import Path

from .skill_registry import SkillRegistry
from app.core.logging import log

class SkillRetriever:

    @classmethod
    def retrieve(cls, intent: str, faculty: str, top_k: int = 3) -> List[Dict]:
        """
        Retrieves the top K relevant skills for the given faculty based on user intent.
        Just-in-Time loads the markdown content for only the selected skills.
        """
        # 1. Filter by Faculty (only active ones that actually have markdown files)
        available_skills = SkillRegistry.get_skills_by_faculty(faculty, active_only=True)
        if not available_skills:
            return []

        # 2. Tag Match & Rank
        intent_lower = intent.lower()
        scored_skills = []
        for skill in available_skills:
            score = sum(1 for tag in skill.tags if tag.lower() in intent_lower)
            # Default score of 1 if no direct tag match but we want to provide something?
            # Actually, let's keep it strictly rank based.
            # We can also add points if the skill ID is in the intent.
            if skill.id.replace('-', ' ').lower() in intent_lower:
                score += 2
            scored_skills.append((score, skill))

        # Sort by score descending
        scored_skills.sort(key=lambda x: x[0], reverse=True)

        # 3. Select Top K
        top_skills = [skill for score, skill in scored_skills[:top_k]]

        if not top_skills:
            return []

        # 4. Load Content (JIT)
        results = []
        registry_path = Path(__file__).parent / "registry.json"
        skills_dir = registry_path.parent

        retrieved_ids = []
        for skill in top_skills:
            skill_file_path = skills_dir / skill.file
            content = ""
            if skill_file_path.exists():
                with open(skill_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            else:
                log("WARNING", f"Skill file missing during JIT load: {skill_file_path}")

            results.append({
                "metadata": skill,
                "content": content
            })
            retrieved_ids.append(skill.id)

        # 5. Log as specified
        retrieved_list_str = "\n".join(f"- {sid}" for sid in retrieved_ids)
        log_msg = f"\n[SKILL_RETRIEVER]\nFaculty={faculty}\nIntent=\"{intent}\"\n\nRetrieved:\n{retrieved_list_str}"
        log("COGNITION", log_msg)

        # 6. Telemetry (ValidationBus)
        from app.sentinel.validation.validation_bus import ValidationBus
        import uuid
        bus = ValidationBus()
        for sid in retrieved_ids:
            bus.emit("skill_usage_event", {
                "event_id": f"skill_evt_{uuid.uuid4().hex[:8]}",
                "faculty": faculty,
                "skill_id": sid,
                "intent": intent,
                "used": True
            })

        return results
