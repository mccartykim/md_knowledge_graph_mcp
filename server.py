import asyncio
import os
from pathlib import Path
from typing import List, Dict, Optional, Any
import sys

# Note: Removing request-specific Pydantic models as per simplification goal.
from pydantic import BaseModel, Field # Keep BaseModel and Field for response models/potential future use
from fastmcp import FastMCP, Context

from kg_core import MarkdownKnowledgeGraph

# --- Pydantic Models for API Responses (Keeping these) ---
class StandardResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

class KnowledgeGraphResponse(BaseModel):
    entities: Dict[str, Any]
    relationships: List[Dict[str, str]]

# --- Knowledge Graph Logic ---
KG_MARKDOWN_BASE_PATH = os.getenv("MD_NOTEBOOK_KNOWLEDGE_GRAPH_DIR", os.getenv("KG_MCP_MARKDOWN_PATH", "kg_markdown_data"))
os.makedirs(KG_MARKDOWN_BASE_PATH, exist_ok=True)

class AsyncKnowledgeGraphService:
    def __init__(self, directory_path: str):
        self.sync_kg = MarkdownKnowledgeGraph(directory_path)
        self.lock = asyncio.Lock()

    async def create_entity(self, name: str) -> bool:
        async with self.lock: return self.sync_kg.newEntity(name)
    async def get_knowledge_graph(self) -> Dict:
        async with self.lock: return self.sync_kg.getKnowledgeGraph()
    async def add_observation(self, entity_name: str, observation: str) -> bool:
        async with self.lock: return self.sync_kg.newObservation(entity_name, observation)
    async def add_relationship(self, entity_name: str, verb: str, target: str, ctx: str) -> bool:
        async with self.lock: return self.sync_kg.newRelationship(entity_name, verb, target, ctx)
    async def delete_entity(self, name: str) -> bool:
        async with self.lock: return self.sync_kg.deleteEntity(name)
    async def delete_observation(self, entity_name: str, observation: str) -> bool:
        async with self.lock: return self.sync_kg.deleteObservation(entity_name, observation)
    async def delete_relationship(self, entity_name: str, verb: str, target: str, ctx: str) -> bool:
        async with self.lock: return self.sync_kg.deleteRelationship(entity_name, verb, target, ctx)

kg_async_service = AsyncKnowledgeGraphService(directory_path=KG_MARKDOWN_BASE_PATH)

app = FastMCP(
    title="KnowledgeGraphNotebook-STDIO",
    description="STDIO MCP Server for managing a Markdown-based Knowledge Graph Notebook.",
    version="0.1.0"
)

# --- Tool Definitions (Refactored Signatures) ---
@app.tool()
async def create_entity(context: Context, entity_name: str) -> Dict:
    """Creates a new entity with the given name.
    
    Args:
        entity_name: The name of the entity to create
    
    Returns:
        A response indicating success or failure.
    """
    # Parameter validation - FastMCP already ensures non-None values for required parameters
    entity_file = Path(KG_MARKDOWN_BASE_PATH) / f"{entity_name}.md"
    if entity_file.exists():
        return StandardResponse(
            success=False, 
            message=f"Entity '{entity_name}' already exists.",
            data={"entity_name": entity_name}
        ).model_dump()
    success = await kg_async_service.create_entity(name=entity_name)
    if success:
        return StandardResponse(
            success=True, 
            message=f"Entity '{entity_name}' created successfully.",
            data={"entity_name": entity_name}
        ).model_dump()
    return StandardResponse(
        success=False, 
        message=f"Failed to create entity '{entity_name}'.",
        data={"entity_name": entity_name}
    ).model_dump()

@app.tool()
async def create_entities_batch(context: Context, entity_names: List[str]) -> Dict:
    """Creates multiple new entities in the knowledge graph in a single operation.
    
    Args:
        entity_names: A list of entity names to create (e.g., ['John Doe', 'Company XYZ']).
    
    Returns:
        A response indicating success or failure for each entity.
    """
    
    if not isinstance(entity_names, list):
        return StandardResponse(
            success=False,
            message="Invalid parameter 'entity_names'. Expected a list of strings.",
            data={"error_type": "invalid_parameter", "parameter": "entity_names", "expected_type": "list"}
        ).model_dump()
    
    # Track results for each entity
    results = []
    success_count = 0
    
    # Process each entity
    for entity_name in entity_names:
        entity_file = Path(KG_MARKDOWN_BASE_PATH) / f"{entity_name}.md"
        if entity_file.exists():
            results.append({
                "entity_name": entity_name,
                "success": False,
                "message": f"Entity '{entity_name}' already exists."
            })
            continue
            
        success = await kg_async_service.create_entity(name=entity_name)
        if success:
            success_count += 1
            results.append({
                "entity_name": entity_name,
                "success": True,
                "message": f"Entity '{entity_name}' created successfully."
            })
        else:
            results.append({
                "entity_name": entity_name,
                "success": False,
                "message": f"Failed to create entity '{entity_name}'."
            })
    
    # Return overall summary and detailed results
    return StandardResponse(
        success=success_count > 0,
        message=f"Created {success_count} out of {len(entity_names)} entities.",
        data={"results": results}
    ).model_dump()

@app.tool()
async def get_graph(context: Context) -> Dict:
    """Retrieves the complete knowledge graph with all entities, observations, and relationships.
    
    Returns:
        The complete knowledge graph structure.
    """
    graph_data = await kg_async_service.get_knowledge_graph()
    return KnowledgeGraphResponse(**graph_data).model_dump()

@app.tool()
async def add_observations_batch(context: Context, observations: List[Dict]) -> Dict:
    """Adds multiple observations to entities in a single operation.
    
    Args:
        observations: A list of dictionaries, each containing 'entity_name' and 'observation_text'.
    
    Returns:
        A response indicating success or failure for each observation.
    """
    
    if not isinstance(observations, list):
        return StandardResponse(
            success=False,
            message="Invalid parameter 'observations'. Expected a list of objects.",
            data={"error_type": "invalid_parameter", "parameter": "observations", "expected_type": "list"}
        ).model_dump()
    
    # Track results for each observation
    results = []
    success_count = 0
    
    # Process each observation
    for item in observations:
        if not isinstance(item, dict):
            results.append({
                "success": False,
                "message": "Invalid observation format. Expected an object with entity_name and observation_text."
            })
            continue
            
        # Extract entity_name and observation_text with fallbacks
        entity_name = item.get("entity_name", item.get("entityName"))
        observation_text = item.get("observation_text", item.get("observation"))
        
        # Basic validation
        if not entity_name:
            results.append({
                "success": False,
                "message": "Missing entity_name in observation object."
            })
            continue
            
        if not observation_text:
            results.append({
                "success": False,
                "message": f"Missing observation_text for entity '{entity_name}'."
            })
            continue
        
        # Check if entity exists
        entity_path = Path(KG_MARKDOWN_BASE_PATH) / f"{entity_name}.md"
        if not entity_path.exists():
            results.append({
                "entity_name": entity_name,
                "success": False,
                "message": f"Entity '{entity_name}' not found. Please create it first using create_entity."
            })
            continue
        
        # Add the observation
        success = await kg_async_service.add_observation(entity_name, observation_text)
        if success:
            success_count += 1
            results.append({
                "entity_name": entity_name,
                "observation_text": observation_text,
                "success": True,
                "message": f"Observation added to '{entity_name}'."
            })
        else:
            results.append({
                "entity_name": entity_name,
                "success": False,
                "message": f"Failed to add observation to '{entity_name}'."
            })
    
    # Return overall summary and detailed results
    return StandardResponse(
        success=success_count > 0,
        message=f"Added {success_count} out of {len(observations)} observations.",
        data={"results": results}
    ).model_dump()

@app.tool()
async def add_observation(context: Context, entity_name: str, observation_text: str) -> Dict:
    """Adds a single fact or piece of information about an entity.
    
    Args:
        entity_name: The name of the entity to add an observation to.
        observation_text: The text of the observation to add.
    
    Returns:
        A response indicating success or failure.
    """
    
    entity_path = Path(KG_MARKDOWN_BASE_PATH) / f"{entity_name}.md"
    if not entity_path.exists():
        return StandardResponse(
            success=False, 
            message=f"Entity '{entity_name}' not found. Please create it first using create_entity.",
            data={"entity_name": entity_name, "error_type": "entity_not_found"}
        ).model_dump()
    
    success = await kg_async_service.add_observation(entity_name, observation_text)
    if success:
        return StandardResponse(
            success=True, 
            message=f"Observation added to '{entity_name}'.",
            data={
                "entity_name": entity_name,
                "observation_text": observation_text
            }
        ).model_dump()
    
    return StandardResponse(
        success=False, 
        message=f"Failed to add observation to '{entity_name}'.",
        data={"entity_name": entity_name}
    ).model_dump()

@app.tool()
async def add_relationships_batch(context: Context, relationships: List[Dict]) -> Dict:
    """Adds multiple relationships between entities in a single operation.
    
    Args:
        relationships: A list of dictionaries, each containing 'from_entity', 'relationship_type', 
                      'to_entity', and optional 'details' properties.
    
    Returns:
        A response indicating success or failure for each relationship.
    """
    
    if not isinstance(relationships, list):
        return StandardResponse(
            success=False,
            message="Invalid parameter 'relationships'. Expected a list of objects.",
            data={"error_type": "invalid_parameter", "parameter": "relationships", "expected_type": "list"}
        ).model_dump()
    
    # Track results for each relationship
    results = []
    success_count = 0
    
    # Process each relationship
    for item in relationships:
        if not isinstance(item, dict):
            results.append({
                "success": False,
                "message": "Invalid relationship format. Expected an object with source/target entities and relationship type."
            })
            continue
            
        # Extract relationship components with fallbacks for various naming conventions
        source_entity = item.get("source_entity_name", 
                               item.get("from_entity", 
                                      item.get("from_entity_name", 
                                             item.get("entity_name"))))
                                             
        verb = item.get("verb_preposition",
                      item.get("relationship_type"))
                      
        target_entity = item.get("target_entity", 
                               item.get("to_entity"))
                               
        details = item.get("details", item.get("context", ""))
        
        # Basic validation
        if not source_entity:
            results.append({
                "success": False,
                "message": "Missing source entity name in relationship object."
            })
            continue
            
        if not verb:
            results.append({
                "success": False,
                "message": f"Missing relationship type/verb for source entity '{source_entity}'."
            })
            continue
            
        if not target_entity:
            results.append({
                "success": False,
                "message": f"Missing target entity for relationship from '{source_entity}'."
            })
            continue
        
        # Check if source entity exists
        if not (Path(KG_MARKDOWN_BASE_PATH) / f"{source_entity}.md").exists():
            results.append({
                "source_entity_name": source_entity,
                "success": False,
                "message": f"Source entity '{source_entity}' not found. Please create it first using create_entity."
            })
            continue
        
        # Check if target entity exists
        if not (Path(KG_MARKDOWN_BASE_PATH) / f"{target_entity}.md").exists():
            results.append({
                "target_entity": target_entity,
                "success": False,
                "message": f"Target entity '{target_entity}' not found. Please create it first using create_entity."
            })
            continue
        
        # Add the relationship
        success = await kg_async_service.add_relationship(source_entity, verb, target_entity, details or "")
        if success:
            success_count += 1
            results.append({
                "source_entity_name": source_entity,
                "verb_preposition": verb,
                "target_entity": target_entity,
                "details": details,
                "success": True,
                "message": f"Relationship added: '{source_entity}' {verb} '{target_entity}'"
            })
        else:
            results.append({
                "source_entity_name": source_entity,
                "target_entity": target_entity,
                "success": False,
                "message": "Failed to add relationship. The entities might be the same or an internal error occurred."
            })
    
    # Return overall summary and detailed results
    return StandardResponse(
        success=success_count > 0,
        message=f"Added {success_count} out of {len(relationships)} relationships.",
        data={"results": results}
    ).model_dump()

@app.tool()
async def add_relationship(context: Context, from_entity: str, relationship_type: str, to_entity: str, details: Optional[str] = None) -> Dict:
    """Adds a relationship between two entities. Both entities must already exist.
    
    Args:
        from_entity: The source entity name.
        relationship_type: The type of relationship (verb or preposition).
        to_entity: The target entity name.
        details: Optional details about the relationship.
    
    Returns:
        A response indicating success or failure.
    """
    # Rename variables for clarity within function
    source_entity = from_entity
    verb = relationship_type
    target_entity = to_entity
    
    # Check if source entity exists
    if not (Path(KG_MARKDOWN_BASE_PATH) / f"{source_entity}.md").exists():
        return StandardResponse(
            success=False, 
            message=f"Source entity '{source_entity}' not found. Please create it first using create_entity.",
            data={
                "source_entity_name": source_entity,
                "error_type": "entity_not_found"
            }
        ).model_dump()
    
    # Check if target entity exists
    if not (Path(KG_MARKDOWN_BASE_PATH) / f"{target_entity}.md").exists():
        return StandardResponse(
            success=False, 
            message=f"Target entity '{target_entity}' not found. Please create it first using create_entity.",
            data={
                "target_entity": target_entity, 
                "error_type": "entity_not_found"
            }
        ).model_dump()

    # Add the relationship
    success = await kg_async_service.add_relationship(
        source_entity, verb, target_entity, details or "" # Pass empty string if details is None
    )
    
    if success:
        return StandardResponse(
            success=True, 
            message=f"Relationship added: '{source_entity}' {verb} '{target_entity}'",
            data={
                "source_entity_name": source_entity,
                "verb_preposition": verb,
                "target_entity": target_entity,
                "details": details
            }
        ).model_dump()
    
    return StandardResponse(
        success=False, 
        message="Failed to add relationship. The entities might be the same or an internal error occurred.",
        data={
            "source_entity_name": source_entity,
            "target_entity": target_entity
        }
    ).model_dump()

@app.tool()
async def delete_entity(context: Context, entity_name: str) -> Dict:
    """Deletes an entity and all its relationships from the knowledge graph.
    
    Args:
        entity_name: The name of the entity to delete.
        
    Returns:
        A response indicating success or failure.
    """
    entity_path = Path(KG_MARKDOWN_BASE_PATH) / f"{entity_name}.md"
    if not entity_path.exists():
        return StandardResponse(
            success=False, 
            message=f"Entity '{entity_name}' not found for deletion.",
            data={"entity_name": entity_name, "error_type": "entity_not_found"}
        ).model_dump()

    success = await kg_async_service.delete_entity(name=entity_name)
    if success:
        return StandardResponse(
            success=True, 
            message=f"Entity '{entity_name}' and its relationships deleted successfully.",
            data={"entity_name": entity_name}
        ).model_dump()
    else:
        return StandardResponse(
            success=False, 
            message=f"Failed to delete entity '{entity_name}'.",
            data={"entity_name": entity_name}
        ).model_dump()

@app.tool()
async def delete_observation(context: Context, entity_name: str, observation_text: str) -> Dict:
    """Deletes a specific observation from an entity.
    
    Args:
        entity_name: The name of the entity containing the observation.
        observation_text: The text of the observation to delete. Must match exactly.
        
    Returns:
        A response indicating success or failure.
    """
    entity_path = Path(KG_MARKDOWN_BASE_PATH) / f"{entity_name}.md"
    if not entity_path.exists():
        return StandardResponse(
            success=False, 
            message=f"Entity '{entity_name}' not found.",
            data={"entity_name": entity_name, "error_type": "entity_not_found"}
        ).model_dump()

    success = await kg_async_service.delete_observation(entity_name, observation_text)
    if success:
        return StandardResponse(
            success=True, 
            message=f"Observation deleted successfully from '{entity_name}'.",
            data={
                "entity_name": entity_name,
                "observation_text": observation_text
            }
        ).model_dump()
    else:
        return StandardResponse(
            success=False, 
            message=f"Failed to delete observation from '{entity_name}'. Make sure the text matches exactly what was added.",
            data={
                "entity_name": entity_name,
                "error_type": "observation_not_found"
            }
        ).model_dump()

@app.tool()
async def delete_relationship(context: Context, from_entity: str, relationship_type: str, to_entity: str, details: Optional[str] = None) -> Dict:
    """Deletes a specific relationship between entities.
    
    Args:
        from_entity: The source entity name.
        relationship_type: The type of relationship (verb or preposition).
        to_entity: The target entity name.
        details: Optional details about the relationship. Must match exactly what was used when creating.
        
    Returns:
        A response indicating success or failure.
    """
    source_entity_path = Path(KG_MARKDOWN_BASE_PATH) / f"{from_entity}.md"
    if not source_entity_path.exists():
        return StandardResponse(
            success=False, 
            message=f"Source entity '{from_entity}' not found.",
            data={"from_entity": from_entity, "error_type": "entity_not_found"}
        ).model_dump()

    # Note: Delete relationship in kg_core might not require the target entity to exist? 
    # Assuming it might fail internally if not, based on the add_relationship checks.
    # Keeping the call signature consistent with add for symmetry.

    success = await kg_async_service.delete_relationship(
        from_entity,
        relationship_type,
        to_entity,
        details or "" # Pass empty string if details is None
    )
    
    if success:
        return StandardResponse(
            success=True, 
            message=f"Relationship deleted successfully: '{from_entity}' {relationship_type} '{to_entity}'",
            data={
                "from_entity": from_entity,
                "relationship_type": relationship_type,
                "to_entity": to_entity
            }
        ).model_dump()
    else:
        return StandardResponse(
            success=False, 
            message=f"Failed to delete relationship from '{from_entity}'. Make sure all fields match exactly with what was used when creating the relationship.",
            data={
                "from_entity": from_entity, 
                "to_entity": to_entity,
                "error_type": "relationship_not_found"
            }
        ).model_dump()

# All CRUD tools defined.

# To run this server, use the FastMCP CLI. For example, for STDIO:
# From the directory containing 'extensions':
# uvx fastmcp run extensions.knowledge_graph_mcp.server:mcp_app --transport stdio
#
# Or, if 'fastmcp run' directly takes the file path (check FastMCP docs):
# From the 'extensions/knowledge_graph_mcp' directory:
# uvx fastmcp run server.py --transport stdio
#
# Ensure 'fastmcp' is installed in your uv environment.

def main():
    app.run()
