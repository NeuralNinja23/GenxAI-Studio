from datetime import datetime
from typing import Dict
from beanie import Document
from pydantic import Field

from app.core.time import utc_now

class Snapshot(Document):
    project_id: str
    step: str
    agent: str
    quality_score: int
    approved: bool
    created_at: datetime = Field(default_factory=utc_now)
    files_snapshot: Dict[str, str] = Field(default_factory=dict)
    
    class Settings:
        name = "snapshots"
