# app/api/agents.py
"""
Agent status routes.
"""
from fastapi import APIRouter

from app.core.constants import AgentName

router = APIRouter(prefix="/api/agents", tags=["Agents"])


@router.get("/status")
async def get_agents_status():
    """Get status of all agents."""
    return {
        "agents": [

            {
                "name": AgentName.VICTORIA,
                "role": "Software Architect", 
                "status": "available",
            },
            {
                "name": AgentName.DEREK,
                "role": "Full-Stack Developer",
                "status": "available",
            },
            {
                "name": AgentName.LUNA,
                "role": "QA Engineer",
                "status": "available",
            },
        ]
    }


@router.get("/active")
async def get_active_workflows():
    """Get list of active workflows from MongoDB."""
    from app.models.workflow import WorkflowSession
    
    # Query database for all sessions that are currently running
    active_sessions = await WorkflowSession.find(WorkflowSession.is_running == True).to_list()
    
    return {
        "active": [
            {"project_id": session.project_id, "running": True}
            for session in active_sessions
        ]
    }

