# app/agents/__init__.py
"""
V4 Cognitive Faculty Package
Exporting Victoria, Derek, Luna, Reggie, and Marcus clean-room models.
"""

from app.agents.sub_agents import (
    VictoriaUIFaculty,
    DerekAPIFaculty,
    LunaSchemaFaculty,
    ReggieWorkflowFaculty,
    MarcusGovernanceAnalyst,
)

__all__ = [
    "VictoriaUIFaculty",
    "DerekAPIFaculty",
    "LunaSchemaFaculty",
    "ReggieWorkflowFaculty",
    "MarcusGovernanceAnalyst",
]
