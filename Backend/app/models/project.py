from datetime import datetime
from typing import Optional, Literal
from beanie import Document, Indexed
from pydantic import Field

from app.core.time import utc_now


# FIX VALID-001: Define allowed status values as a type
ProjectStatus = Literal["created", "analyzing", "building", "completed", "failed"]


class Project(Document):
    name: Indexed(str)
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    workspace_path: str
    provider: str = "gemini"
    model: str = "gemini-pro"
    status: ProjectStatus = "created"  # Now validated by Pydantic
    
    class Settings:
        name = "projects"
