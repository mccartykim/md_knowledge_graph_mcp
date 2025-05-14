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
@app.tool(name="create_entity", description="Creates a new entity with the given name. Use PascalCase for entity names (e.g., 'JohnDoe').")
async def create_entity_tool(context: Context, entity_name: str) -> Dict:
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

@app.tool(name="get_graph", description="Retrieves the entire knowledge graph.")
async def get_graph_tool(context: Context) -> Dict:
    graph_data = await kg_async_service.get_knowledge_graph()
    # Assuming get_knowledge_graph returns a dict compatible with KnowledgeGraphResponse
    return KnowledgeGraphResponse(**graph_data).model_dump()

@app.tool(name="add_observation", description="Adds a single fact or piece of information about an entity.")
async def add_observation_tool(context: Context, entity_name: str, observation_text: str) -> Dict:
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

@app.tool(name="add_relationship", description="Adds a relationship between two entities. Both entities must already exist.")
async def add_relationship_tool(context: Context, from_entity: str, relationship_type: str, to_entity: str, details: Optional[str] = None) -> Dict:
    # Check if source entity exists
    if not (Path(KG_MARKDOWN_BASE_PATH) / f"{from_entity}.md").exists():
        return StandardResponse(
            success=False, 
            message=f"Source entity '{from_entity}' not found. Please create it first using create_entity.",
            data={
                "from_entity": from_entity,
                "error_type": "entity_not_found"
            }
        ).model_dump()
    
    # Check if target entity exists
    if not (Path(KG_MARKDOWN_BASE_PATH) / f"{to_entity}.md").exists():
        return StandardResponse(
            success=False, 
            message=f"Target entity '{to_entity}' not found. Please create it first using create_entity.",
            data={
                "to_entity": to_entity, 
                "error_type": "entity_not_found"
            }
        ).model_dump()

    # Add the relationship
    success = await kg_async_service.add_relationship(
        from_entity, relationship_type, to_entity, details or "" # Pass empty string if details is None
    )
    
    if success:
        return StandardResponse(
            success=True, 
            message=f"Relationship added: '{from_entity}' {relationship_type} '{to_entity}'",
            data={
                "from_entity": from_entity,
                "relationship_type": relationship_type,
                "to_entity": to_entity,
                "details": details
            }
        ).model_dump()
    
    return StandardResponse(
        success=False, 
        message="Failed to add relationship. The entities might be the same or an internal error occurred.",
        data={
            "from_entity": from_entity,
            "to_entity": to_entity
        }
    ).model_dump()

@app.tool(name="delete_entity", description="Deletes an entity and all its relationships.")
async def delete_entity_tool(context: Context, entity_name: str) -> Dict:
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

@app.tool(name="delete_observation", description="Deletes a specific observation from an entity. The observation text must match exactly.")
async def delete_observation_tool(context: Context, entity_name: str, observation_text: str) -> Dict:
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

@app.tool(name="delete_relationship", description="Deletes a specific relationship between entities. All fields must match exactly what was used when creating.")
async def delete_relationship_tool(context: Context, from_entity: str, relationship_type: str, to_entity: str, details: Optional[str] = None) -> Dict:
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
