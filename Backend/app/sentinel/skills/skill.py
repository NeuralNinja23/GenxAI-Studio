from pydantic import BaseModel
from typing import List

class Skill(BaseModel):
    """
    Metadata-only model for an ECC engineering skill.
    Content is intentionally omitted to avoid memory bloat during startup.
    Content will be Just-In-Time (JIT) loaded by the SkillRetriever.
    """
    id: str
    version: str
    faculty: str
    domain: str
    tags: List[str]
    file: str
    active: bool = False
