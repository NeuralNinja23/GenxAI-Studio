# app/sentinel/cognition/ontology_discovery.py
"""
V4 Cognition Subsystem — Phase 8: Product Ontology Reasoner

Discovers high-level, purely abstract semantic models (Entities, Relationships, Roles, Capabilities, Workflows)
based on the ExperienceGraph. Remains purely abstract in meaning, avoid database schema or service topologies.
Includes hooks for Phase 9 Semantic Memory persistence.
"""

import json
from typing import Dict, Any, Optional, List
from app.sentinel.cognition.experience_graph import ExperienceGraph
from app.sentinel.cognition.ontology_graph import OntologyGraph
from app.sentinel.topology.node_types import NodeType
from app.llm.adapter import call_llm
from app.core.logging import log
from app.sentinel.meaning_memory.meaning_recorder import record_meaning, PatternType

PROMPT_TEMPLATE = """
You are the Sentinel Core Ontology Discovery Engine.
Your task is to analyze the Experience Graph (user experience goals, journeys, flows, screens, and actions)
and discover the underlying abstract Product Ontology.

Do NOT output database schemas, API routes, react views, or implementation/code details.
Focus exclusively on abstract meaning and concepts:
1. Entities: The core business domain nouns/objects (e.g., Customer, Contact, Order, Invoice).
2. Roles: User and system personas involved (e.g., Sales Rep, Manager, Admin, Billing Agent).
3. Capabilities: The semantic actions and faculties enabled by the product (e.g., Manage Opportunity, Process Payment).
4. Relationships: How entities and roles connect (e.g., Customer owns Contacts, Sales Rep manages Customer).
5. Workflows: The logical processes and states of lifecycle items (e.g., Lead Conversion lifecycle).

Based on the following Experience Graph:
{experience_graph_json}

Produce a valid JSON object matching this schema exactly:
{{
  "ontology": {{
    "entities": [
      {{
        "id": "entity_customer",
        "name": "Customer",
        "description": "Represents a business or client."
      }}
    ],
    "roles": [
      {{
        "id": "role_sales_rep",
        "name": "Sales Rep",
        "description": "Responsible for managing deals."
      }}
    ],
    "capabilities": [
      {{
        "id": "capability_manage_opportunity",
        "name": "Manage Opportunity",
        "description": "Facilitates tracking business opportunity stages."
      }}
    ],
    "relationships": [
      {{
        "id": "rel_customer_owns_contacts",
        "source": "entity_customer",
        "target": "entity_contact",
        "name": "owns",
        "description": "A Customer owns one or more Contacts."
      }}
    ],
    "workflows": [
      {{
        "id": "ont_wf_lead_conversion",
        "name": "Lead Conversion Workflow",
        "description": "A high-level workflow mapping prospect conversion stages."
      }}
    ]
  }}
}}

Ensure all fields are present, and generate ONLY valid JSON without any markdown formatting or surrounding explanations.
"""

class OntologyDiscoveryEngine:
    """
    Analyzes the ExperienceGraph and maps it to a pure-meaning OntologyGraph.
    Integrates with MeaningRecorder to passively persist discovered patterns.
    """

    @classmethod
    async def discover(cls, project_id: str, experience_graph: ExperienceGraph) -> OntologyGraph:
        """
        Derive an in-memory OntologyGraph from an ExperienceGraph.
        Includes a passive hook to record the experience graph and prompt to Semantic Memory.
        """
        log("OntologyDiscoveryEngine", f"Starting product ontology discovery for project {project_id}")
        
        # 1. Prepare Experience Graph summary
        exp_graph_dump = experience_graph.serialize()
        
        # 2. Passive Hook: Record Experience Pattern in Semantic Memory (Phase 9)
        try:
            record_meaning(
                pattern_type=PatternType.EXPERIENCE,
                payload=exp_graph_dump,
                project_id=project_id,
                node_count=len(experience_graph.nodes),
                edge_count=len(experience_graph.edges)
            )
        except Exception as e:
            log("OntologyDiscoveryEngine", f"Failed to record Experience Pattern to memory: {e}")

        # 3. Call LLM for Ontology discovery
        system_prompt = "You are a Product Ontologist and Domain-Driven Design Architect."
        prompt = PROMPT_TEMPLATE.format(experience_graph_json=json.dumps(exp_graph_dump, indent=2))

        try:
            response = await call_llm(
                prompt=prompt,
                system_prompt=system_prompt,
                step_name="ontology_reasoning"
            )

            # Clean possible markdown formatting
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]

            data = json.loads(response.strip())
            
            ontology_graph = OntologyGraph(project_id=project_id)
            cls._populate_ontology(ontology_graph, data)

            log("OntologyDiscoveryEngine", f"Successfully discovered OntologyGraph with {len(ontology_graph.nodes)} nodes")

            # 4. Passive Hook: Record Ontology Pattern in Semantic Memory (Phase 9)
            try:
                record_meaning(
                    pattern_type=PatternType.ONTOLOGY,
                    payload=ontology_graph.serialize(),
                    project_id=project_id,
                    node_count=len(ontology_graph.nodes),
                    edge_count=len(ontology_graph.edges)
                )
            except Exception as e:
                log("OntologyDiscoveryEngine", f"Failed to record Ontology Pattern to memory: {e}")

            return ontology_graph

        except Exception as e:
            log("OntologyDiscoveryEngine", f"Failed to discover ontology graph: {e}")
            raise

    @classmethod
    def _populate_ontology(cls, graph: OntologyGraph, data: Dict[str, Any]) -> None:
        """Parses the discovered LLM schema and populates the OntologyGraph."""
        ontology_data = data.get("ontology", {})
        
        # 1. Add Entity Nodes
        for entity in ontology_data.get("entities", []):
            node_id = entity.get("id")
            if node_id:
                graph.add_ontology_node(
                    node_id,
                    NodeType.ENTITY_NODE,
                    {"name": entity.get("name"), "description": entity.get("description")}
                )

        # 2. Add Role Nodes
        for role in ontology_data.get("roles", []):
            node_id = role.get("id")
            if node_id:
                graph.add_ontology_node(
                    node_id,
                    NodeType.ROLE_NODE,
                    {"name": role.get("name"), "description": role.get("description")}
                )

        # 3. Add Capability Nodes
        for cap in ontology_data.get("capabilities", []):
            node_id = cap.get("id")
            if node_id:
                graph.add_ontology_node(
                    node_id,
                    NodeType.CAPABILITY_NODE,
                    {"name": cap.get("name"), "description": cap.get("description")}
                )

        # 4. Add Workflow Nodes
        for wf in ontology_data.get("workflows", []):
            node_id = wf.get("id")
            if node_id:
                graph.add_ontology_node(
                    node_id,
                    NodeType.ONTOLOGY_WORKFLOW_NODE,
                    {"name": wf.get("name"), "description": wf.get("description")}
                )

        # 5. Add Relationship Nodes & Edges
        # Relationships are represented as RELATIONSHIP_NODEs with edges connecting them to their source and target
        for rel in ontology_data.get("relationships", []):
            node_id = rel.get("id")
            source_id = rel.get("source")
            target_id = rel.get("target")
            
            if node_id and source_id and target_id:
                # Add relationship node itself to capture attributes/properties
                graph.add_ontology_node(
                    node_id,
                    NodeType.RELATIONSHIP_NODE,
                    {"name": rel.get("name"), "description": rel.get("description")}
                )
                
                # Connect source entity/role to relationship node
                if source_id in graph.nodes:
                    graph.add_edge(source_id, node_id, "ontology_relates_to")
                
                # Connect relationship node to target entity/role
                if target_id in graph.nodes:
                    graph.add_edge(node_id, target_id, "ontology_relates_to")
