import os
import json
from typing import List, Dict
from pathlib import Path

from .skill import Skill
from app.core.logging import log

class SkillRegistry:
    _skills: Dict[str, Skill] = {}
    _registry_loaded: bool = False
    _valid_faculties = {"Sophia", "Victoria", "Derek", "Luna", "Reggie"}

    @classmethod
    def initialize(cls, registry_path: str = None) -> None:
        """
        Loads the registry.json, validates metadata and active skill files,
        and caches the Skill objects (metadata-only) in memory.
        Raises ValueError if validation fails.
        """
        if cls._registry_loaded:
            return

        if registry_path is None:
            # Default to the same directory as this file
            current_dir = Path(__file__).parent
            registry_path = current_dir / "registry.json"
        
        registry_path = Path(registry_path)
        
        if not registry_path.exists():
            raise FileNotFoundError(f"Skill registry not found at {registry_path}")

        try:
            with open(registry_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in registry: {e}")

        for item in data:
            skill = Skill(**item)

            # Validate duplicate ID
            if skill.id in cls._skills:
                raise ValueError(f"Duplicate skill ID found in registry: {skill.id}")

            # Validate Faculty
            if skill.faculty not in cls._valid_faculties:
                raise ValueError(f"Invalid faculty '{skill.faculty}' mapped for skill '{skill.id}'")

            # Validate markdown file existence for active skills
            if skill.active:
                skill_file_path = registry_path.parent / skill.file
                if not skill_file_path.exists():
                    raise FileNotFoundError(
                        f"CRITICAL: Active skill '{skill.id}' is missing its markdown file at {skill_file_path}. "
                        "The system cannot boot missing active skills."
                    )

            cls._skills[skill.id] = skill

        cls._registry_loaded = True
        log("SYSTEM", f"[SKILL_REGISTRY] Successfully validated and loaded {len(cls._skills)} metadata records "
                      f"({sum(1 for s in cls._skills.values() if s.active)} active).")

    @classmethod
    def get_all_skills(cls) -> List[Skill]:
        cls.initialize()
        return list(cls._skills.values())

    @classmethod
    def get_skills_by_faculty(cls, faculty: str, active_only: bool = True) -> List[Skill]:
        cls.initialize()
        skills = []
        for skill in cls._skills.values():
            if skill.faculty == faculty:
                if active_only and not skill.active:
                    continue
                skills.append(skill)
        return skills
