from datetime import datetime
from typing import Optional, Dict, Literal
from beanie import Document, Indexed
from pydantic import Field

from app.core.time import utc_now

DeploymentStatus = Literal["initialized", "deploying", "success", "failed", "rolling_back", "not_deployed"]

class Deployment(Document):
    """Deployment configuration and status."""
    project_id: Indexed(str, unique=True)
    status: DeploymentStatus = "not_deployed"
    project_name: str
    custom_domain: Optional[str] = None
    environment_vars: Dict[str, str] = Field(default_factory=dict)
    
    # Versioning
    version: str = "1.0.0"
    
    # Timestamps
    created_at: datetime = Field(default_factory=utc_now)
    deployed_at: Optional[datetime] = None
    last_updated_at: datetime = Field(default_factory=utc_now)
    
    # Runtime info
    url: Optional[str] = None
    container_health: str = "unknown"
    port: int = 3000

    class Settings:
        name = "deployments"
