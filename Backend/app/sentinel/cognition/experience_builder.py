# app/sentinel/cognition/experience_builder.py
"""
V4 Cognition Subsystem — Phase 7: Experience Builder

Constructs the purely in-memory ExperienceGraph by reasoning over a user prompt.
This happens *before* UI or data component generation, establishing a semantic
hierarchy of goals, journeys, flows, screens, and actions.
"""

import json
from typing import Dict, Any, Optional
from app.sentinel.cognition.experience_graph import ExperienceGraph
from app.sentinel.topology.node_types import NodeType
from app.llm.adapter import call_llm
from app.core.logging import log
from app.sentinel.meaning_memory.meaning_recorder import record_meaning, PatternType

PROMPT_TEMPLATE = """
You are the Sentinel Core Cognition Engine.
Your task is to analyze the user's intent and produce an Experience Graph.

The Experience Graph must be returned as a JSON object representing the hierarchical structure:
EXPERIENCE -> GOAL -> JOURNEY -> FLOW -> SCREEN -> ACTION

Output a valid JSON object matching this schema:
{
  "experience": {
    "id": "exp_main",
    "name": "Main Experience",
    "goals": [
      {
        "id": "goal_1",
        "name": "Purchase Product",
        "journeys": [
          {
            "id": "journey_1",
            "name": "Search -> Cart -> Checkout",
            "flows": [
              {
                "id": "flow_1",
                "name": "Search Product Flow",
                "screens": [
                  {
                    "id": "screen_1",
                    "name": "Search Results Screen",
                    "actions": [
                      {"id": "action_1", "name": "Click Item"},
                      {"id": "action_2", "name": "Filter Results"}
                    ]
                  }
                ]
              }
            ]
          }
        ]
      }
    ]
  }
}

User Prompt:
{user_prompt}

Generate only the JSON output. Do not include markdown formatting or explanations.
"""

class ExperienceGraphBuilder:
    """
    Builds the Experience Graph from user intent.
    Operates within the Sentinel Core before component reasoning begins.
    """
    
    @classmethod
    async def build(cls, project_id: str, user_prompt: str) -> ExperienceGraph:
        """Generate an in-memory ExperienceGraph from a prompt."""
        log("ExperienceBuilder", f"Building experience graph for project {project_id}")
        
        system_prompt = "You are a UX Architect mapping user intent to experience nodes."
        prompt = PROMPT_TEMPLATE.format(user_prompt=user_prompt)
        
        try:
            # We don't want stop_sequences here since it's JSON output
            response = await call_llm(
                prompt=prompt,
                system_prompt=system_prompt,
                step_name="experience_reasoning"
            )
            
            # Clean possible markdown formatting
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
                
            data = json.loads(response.strip())
            
            graph = ExperienceGraph(project_id=project_id)
            cls._populate_graph(graph, data)
            
            log("ExperienceBuilder", f"Successfully built ExperienceGraph with {len(graph.nodes)} nodes")
            
            # Record Intent Pattern to Semantic Memory
            try:
                record_meaning(
                    pattern_type=PatternType.INTENT,
                    payload={"user_prompt": user_prompt, "extracted_json": data},
                    project_id=project_id,
                    prompt=user_prompt,
                    node_count=len(graph.nodes),
                    edge_count=len(graph.edges)
                )
            except Exception as mem_err:
                log("ExperienceBuilder", f"Failed to record intent pattern to semantic memory: {mem_err}")
                
            return graph
            
        except Exception as e:
            log("ExperienceBuilder", f"Failed to build experience graph: {e}")
            raise

    @classmethod
    def _populate_graph(cls, graph: ExperienceGraph, data: Dict[str, Any]) -> None:
        """Parses the LLM JSON output and constructs graph nodes and edges."""
        exp_data = data.get("experience")
        if not exp_data:
            return

        exp_id = exp_data.get("id", "exp_main")
        graph.add_experience_node(exp_id, NodeType.EXPERIENCE_NODE, {"name": exp_data.get("name")})
        
        for goal in exp_data.get("goals", []):
            goal_id = goal.get("id")
            graph.add_experience_node(goal_id, NodeType.GOAL_NODE, {"name": goal.get("name")})
            graph.add_edge(exp_id, goal_id, "experience_contains_goal")
            
            for journey in goal.get("journeys", []):
                journey_id = journey.get("id")
                graph.add_experience_node(journey_id, NodeType.JOURNEY_NODE, {"name": journey.get("name")})
                graph.add_edge(goal_id, journey_id, "goal_contains_journey")
                
                for flow in journey.get("flows", []):
                    flow_id = flow.get("id")
                    graph.add_experience_node(flow_id, NodeType.FLOW_NODE, {"name": flow.get("name")})
                    graph.add_edge(journey_id, flow_id, "journey_contains_flow")
                    
                    for screen in flow.get("screens", []):
                        screen_id = screen.get("id")
                        graph.add_experience_node(screen_id, NodeType.SCREEN_NODE, {"name": screen.get("name")})
                        graph.add_edge(flow_id, screen_id, "flow_contains_screen")
                        
                        for action in screen.get("actions", []):
                            action_id = action.get("id")
                            graph.add_experience_node(action_id, NodeType.ACTION_NODE, {"name": action.get("name")})
                            graph.add_edge(screen_id, action_id, "screen_contains_action")
