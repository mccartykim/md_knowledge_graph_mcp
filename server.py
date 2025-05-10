import asyncio
import os
from pathlib import Path
from typing import List, Dict, Optional, Any, Mapping
import sys

from pydantic import BaseModel, Field
from fastmcp import FastMCP, Context
# Hypothetical import for STDIO runner, verify from FastMCP docs
# from fastmcp.stdio import run_server_stdio 

from kg_core import MarkdownKnowledgeGraph

# --- Pydantic Models for API ---
class EntityNameRequest(BaseModel):
    name: str = Field(..., description="Name of the entity.")

class ObservationRequest(BaseModel):
    entity_name: str = Field(..., description="Name of the entity to add observation to.")
    observation: str = Field(..., description="Observation text to add to the entity.")

class RelationshipRequest(BaseModel):
    source_entity_name: str = Field(..., description="Name of the source entity for the relationship.")
    verb_preposition: str = Field(..., description="Verb or preposition for the relationship.")
    target_entity: str = Field(..., description="Name of the target entity for the relationship.")
    context: Optional[str] = Field(default="", description="Optional context for the relationship.")

class StandardResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

class KnowledgeGraphResponse(BaseModel):
    entities: Dict[str, Any]
    relationships: List[Dict[str, str]]

class DeleteEntityRequest(BaseModel):
    name: str = Field(..., description="Name of the entity to delete.")

class DeleteObservationRequest(BaseModel):
    entity_name: str = Field(..., description="Name of the entity from which to delete the observation.")
    observation: str = Field(..., description="The exact text of the observation to delete.")

class DeleteRelationshipRequest(BaseModel):
    source_entity_name: str = Field(..., description="Name of the source entity of the relationship.")
    verb_preposition: str = Field(..., description="Verb or preposition of the relationship.")
    target_entity: str = Field(..., description="Name of the target entity of the relationship.")
    context: Optional[str] = Field(default="", description="Context of the relationship (must match exactly).")

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
@app.tool(name="create_entity", description="Creates a new entity.")
async def create_entity_tool(context: Context, request: EntityNameRequest) -> Dict:
    entity_file = Path(KG_MARKDOWN_BASE_PATH) / f"{request.name}.md"
    if entity_file.exists():
        return StandardResponse(success=False, message=f"Entity '{request.name}' already exists.").model_dump()
    success = await kg_async_service.create_entity(name=request.name)
    if success:
        return StandardResponse(success=True, message=f"Entity '{request.name}' created successfully.").model_dump()
    return StandardResponse(success=False, message=f"Failed to create entity '{request.name}'.").model_dump()

@app.tool(name="get_graph", description="Retrieves the entire knowledge graph.")
async def get_graph_tool(context: Context) -> Dict:
    graph_data = await kg_async_service.get_knowledge_graph()
    return KnowledgeGraphResponse(**graph_data).model_dump()

@app.tool(name="add_observation", description="Adds an observation to an entity.")
async def add_observation_tool(context: Context, request: ObservationRequest) -> Dict:
    entity_path = Path(KG_MARKDOWN_BASE_PATH) / f"{request.entity_name}.md"
    if not entity_path.exists():
        return StandardResponse(success=False, message=f"Entity '{request.entity_name}' not found.").model_dump()
    
    success = await kg_async_service.add_observation(request.entity_name, request.observation)
    if success:
        return StandardResponse(success=True, message=f"Observation added to '{request.entity_name}'.").model_dump()
    return StandardResponse(success=False, message=f"Failed to add observation to '{request.entity_name}'.").model_dump()

@app.tool(name="add_relationship", description="Adds a relationship between entities.")
async def add_relationship_tool(context: Context, request: RelationshipRequest) -> Dict:
    if not (Path(KG_MARKDOWN_BASE_PATH) / f"{request.source_entity_name}.md").exists():
        return StandardResponse(success=False, message=f"Source entity '{request.source_entity_name}' not found.").model_dump()
    if not (Path(KG_MARKDOWN_BASE_PATH) / f"{request.target_entity}.md").exists():
        return StandardResponse(success=False, message=f"Target entity '{request.target_entity}' not found.").model_dump()

    success = await kg_async_service.add_relationship(
        request.source_entity_name, request.verb_preposition, request.target_entity, request.context
    )
    if success:
        return StandardResponse(success=True, message=f"Relationship added from '{request.source_entity_name}' to '{request.target_entity}'.").model_dump()
    return StandardResponse(success=False, message="Failed to add relationship.").model_dump()

@app.tool(name="delete_entity", description="Deletes an entity and its relationships.")
async def delete_entity_tool(context: Context, request: DeleteEntityRequest) -> Dict:
    entity_path = Path(KG_MARKDOWN_BASE_PATH) / f"{request.name}.md"
    if not entity_path.exists():
        return StandardResponse(success=False, message=f"Entity '{request.name}' not found for deletion.").model_dump()

    success = await kg_async_service.delete_entity(name=request.name)
    if success:
        return StandardResponse(success=True, message=f"Entity '{request.name}' and its relationships deleted successfully.").model_dump()
    else:
        return StandardResponse(success=False, message=f"Failed to delete entity '{request.name}'.").model_dump()

@app.tool(name="delete_observation", description="Deletes a specific observation from an entity.")
async def delete_observation_tool(context: Context, request: DeleteObservationRequest) -> Dict:
    entity_path = Path(KG_MARKDOWN_BASE_PATH) / f"{request.entity_name}.md"
    if not entity_path.exists():
        return StandardResponse(success=False, message=f"Entity '{request.entity_name}' not found.").model_dump()

    success = await kg_async_service.delete_observation(request.entity_name, request.observation)
    if success:
        return StandardResponse(success=True, message=f"Observation deleted successfully from '{request.entity_name}'.").model_dump()
    else:
        return StandardResponse(success=False, message=f"Failed to delete observation from '{request.entity_name}'. It might not exist or an error occurred.").model_dump()

@app.tool(name="delete_relationship", description="Deletes a specific relationship from an entity.")
async def delete_relationship_tool(context: Context, request: DeleteRelationshipRequest) -> Dict:
    source_entity_path = Path(KG_MARKDOWN_BASE_PATH) / f"{request.source_entity_name}.md"
    if not source_entity_path.exists():
        return StandardResponse(success=False, message=f"Source entity '{request.source_entity_name}' not found.").model_dump()

    success = await kg_async_service.delete_relationship(
        request.source_entity_name,
        request.verb_preposition,
        request.target_entity,
        request.context
    )
    if success:
        return StandardResponse(success=True, message=f"Relationship deleted successfully from '{request.source_entity_name}'.").model_dump()
    else:
        return StandardResponse(success=False, message=f"Failed to delete relationship from '{request.source_entity_name}'. It might not exist with the exact details provided.").model_dump()

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