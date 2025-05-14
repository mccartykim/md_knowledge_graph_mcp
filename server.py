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
    entity_name: str = Field(
        ..., 
        description="Name of the entity (use PascalCase, e.g., 'JohnDoe' or 'ProjectAlpha').",
        examples=["JohnDoe", "ProjectAlpha", "CompanyXYZ"]
    )

class ObservationRequest(BaseModel):
    entity_name: str = Field(
        ..., 
        description="Name of the entity to add observation to (must exist already)",
        examples=["JohnDoe", "CompanyXYZ"]
    )
    observation_text: str = Field(
        ..., 
        description="A single fact or piece of information about the entity (one per line)",
        examples=[
            "Born in New York in 1980.", 
            "Graduated from Stanford University.", 
            "Has expertise in Python programming."
        ]
    )

class RelationshipRequest(BaseModel):
    from_entity: str = Field(
        ..., 
        description="Name of the source entity (must exist already)",
        examples=["JohnDoe", "CompanyXYZ"]
    )
    relationship_type: str = Field(
        ..., 
        description="The relationship verb or phrase (e.g., 'works at', 'is friends with', 'belongs to')",
        examples=["works at", "is friends with", "belongs to", "contains", "created by"]
    )
    to_entity: str = Field(
        ..., 
        description="Name of the target entity (must exist already)",
        examples=["CompanyXYZ", "ProjectAlpha"]
    )
    details: Optional[str] = Field(
        default="", 
        description="Optional details about the relationship (e.g., 'since 2020', 'as developer')",
        examples=["since 2020", "as developer", "primary location"]
    )

class StandardResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

class KnowledgeGraphResponse(BaseModel):
    entities: Dict[str, Any]
    relationships: List[Dict[str, str]]

class DeleteEntityRequest(BaseModel):
    entity_name: str = Field(
        ..., 
        description="Name of the entity to delete",
        examples=["JohnDoe", "CompanyXYZ"]
    )

class DeleteObservationRequest(BaseModel):
    entity_name: str = Field(
        ..., 
        description="Name of the entity from which to delete the observation",
        examples=["JohnDoe", "CompanyXYZ"]
    )
    observation_text: str = Field(
        ..., 
        description="The exact text of the observation to delete (must match exactly)",
        examples=["Born in New York in 1980.", "Graduated from Stanford University."]
    )

class DeleteRelationshipRequest(BaseModel):
    from_entity: str = Field(
        ..., 
        description="Name of the source entity",
        examples=["JohnDoe", "CompanyXYZ"]
    )
    relationship_type: str = Field(
        ..., 
        description="The relationship verb or phrase to delete",
        examples=["works at", "is friends with", "belongs to"]
    )
    to_entity: str = Field(
        ..., 
        description="Name of the target entity",
        examples=["CompanyXYZ", "ProjectAlpha"]
    )
    details: Optional[str] = Field(
        default="", 
        description="Details of the relationship to match exactly (must match what was used when creating)",
        examples=["since 2020", "as developer"]
    )

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
async def create_entity_tool(context: Context, request: EntityNameRequest) -> Dict:
    entity_file = Path(KG_MARKDOWN_BASE_PATH) / f"{request.entity_name}.md"
    if entity_file.exists():
        return StandardResponse(
            success=False, 
            message=f"Entity '{request.entity_name}' already exists.",
            data={"entity_name": request.entity_name}
        ).model_dump()
    success = await kg_async_service.create_entity(name=request.entity_name)
    if success:
        return StandardResponse(
            success=True, 
            message=f"Entity '{request.entity_name}' created successfully.",
            data={"entity_name": request.entity_name}
        ).model_dump()
    return StandardResponse(
        success=False, 
        message=f"Failed to create entity '{request.entity_name}'.",
        data={"entity_name": request.entity_name}
    ).model_dump()

@app.tool(name="get_graph", description="Retrieves the entire knowledge graph.")
async def get_graph_tool(context: Context) -> Dict:
    graph_data = await kg_async_service.get_knowledge_graph()
    return KnowledgeGraphResponse(**graph_data).model_dump()

@app.tool(name="add_observation", description="Adds a single fact or piece of information about an entity.")
async def add_observation_tool(context: Context, request: ObservationRequest) -> Dict:
    entity_path = Path(KG_MARKDOWN_BASE_PATH) / f"{request.entity_name}.md"
    if not entity_path.exists():
        return StandardResponse(
            success=False, 
            message=f"Entity '{request.entity_name}' not found. Please create it first using create_entity.",
            data={"entity_name": request.entity_name, "error_type": "entity_not_found"}
        ).model_dump()
    
    success = await kg_async_service.add_observation(request.entity_name, request.observation_text)
    if success:
        return StandardResponse(
            success=True, 
            message=f"Observation added to '{request.entity_name}'.",
            data={
                "entity_name": request.entity_name,
                "observation_text": request.observation_text
            }
        ).model_dump()
    
    return StandardResponse(
        success=False, 
        message=f"Failed to add observation to '{request.entity_name}'.",
        data={"entity_name": request.entity_name}
    ).model_dump()

@app.tool(name="add_relationship", description="Adds a relationship between two entities. Both entities must already exist.")
async def add_relationship_tool(context: Context, request: RelationshipRequest) -> Dict:
    # Check if source entity exists
    if not (Path(KG_MARKDOWN_BASE_PATH) / f"{request.from_entity}.md").exists():
        return StandardResponse(
            success=False, 
            message=f"Source entity '{request.from_entity}' not found. Please create it first using create_entity.",
            data={
                "from_entity": request.from_entity,
                "error_type": "entity_not_found"
            }
        ).model_dump()
    
    # Check if target entity exists
    if not (Path(KG_MARKDOWN_BASE_PATH) / f"{request.to_entity}.md").exists():
        return StandardResponse(
            success=False, 
            message=f"Target entity '{request.to_entity}' not found. Please create it first using create_entity.",
            data={
                "to_entity": request.to_entity, 
                "error_type": "entity_not_found"
            }
        ).model_dump()

    # Add the relationship
    success = await kg_async_service.add_relationship(
        request.from_entity, request.relationship_type, request.to_entity, request.details
    )
    
    if success:
        return StandardResponse(
            success=True, 
            message=f"Relationship added: '{request.from_entity}' {request.relationship_type} '{request.to_entity}'",
            data={
                "from_entity": request.from_entity,
                "relationship_type": request.relationship_type,
                "to_entity": request.to_entity,
                "details": request.details
            }
        ).model_dump()
    
    return StandardResponse(
        success=False, 
        message="Failed to add relationship. The entities might be the same or an internal error occurred.",
        data={
            "from_entity": request.from_entity,
            "to_entity": request.to_entity
        }
    ).model_dump()

@app.tool(name="delete_entity", description="Deletes an entity and all its relationships.")
async def delete_entity_tool(context: Context, request: DeleteEntityRequest) -> Dict:
    entity_path = Path(KG_MARKDOWN_BASE_PATH) / f"{request.entity_name}.md"
    if not entity_path.exists():
        return StandardResponse(
            success=False, 
            message=f"Entity '{request.entity_name}' not found for deletion.",
            data={"entity_name": request.entity_name, "error_type": "entity_not_found"}
        ).model_dump()

    success = await kg_async_service.delete_entity(name=request.entity_name)
    if success:
        return StandardResponse(
            success=True, 
            message=f"Entity '{request.entity_name}' and its relationships deleted successfully.",
            data={"entity_name": request.entity_name}
        ).model_dump()
    else:
        return StandardResponse(
            success=False, 
            message=f"Failed to delete entity '{request.entity_name}'.",
            data={"entity_name": request.entity_name}
        ).model_dump()

@app.tool(name="delete_observation", description="Deletes a specific observation from an entity. The observation text must match exactly.")
async def delete_observation_tool(context: Context, request: DeleteObservationRequest) -> Dict:
    entity_path = Path(KG_MARKDOWN_BASE_PATH) / f"{request.entity_name}.md"
    if not entity_path.exists():
        return StandardResponse(
            success=False, 
            message=f"Entity '{request.entity_name}' not found.",
            data={"entity_name": request.entity_name, "error_type": "entity_not_found"}
        ).model_dump()

    success = await kg_async_service.delete_observation(request.entity_name, request.observation_text)
    if success:
        return StandardResponse(
            success=True, 
            message=f"Observation deleted successfully from '{request.entity_name}'.",
            data={
                "entity_name": request.entity_name,
                "observation_text": request.observation_text
            }
        ).model_dump()
    else:
        return StandardResponse(
            success=False, 
            message=f"Failed to delete observation from '{request.entity_name}'. Make sure the text matches exactly what was added.",
            data={
                "entity_name": request.entity_name,
                "error_type": "observation_not_found"
            }
        ).model_dump()

@app.tool(name="delete_relationship", description="Deletes a specific relationship between entities. All fields must match exactly what was used when creating.")
async def delete_relationship_tool(context: Context, request: DeleteRelationshipRequest) -> Dict:
    source_entity_path = Path(KG_MARKDOWN_BASE_PATH) / f"{request.from_entity}.md"
    if not source_entity_path.exists():
        return StandardResponse(
            success=False, 
            message=f"Source entity '{request.from_entity}' not found.",
            data={"from_entity": request.from_entity, "error_type": "entity_not_found"}
        ).model_dump()

    success = await kg_async_service.delete_relationship(
        request.from_entity,
        request.relationship_type,
        request.to_entity,
        request.details
    )
    
    if success:
        return StandardResponse(
            success=True, 
            message=f"Relationship deleted successfully: '{request.from_entity}' {request.relationship_type} '{request.to_entity}'",
            data={
                "from_entity": request.from_entity,
                "relationship_type": request.relationship_type,
                "to_entity": request.to_entity
            }
        ).model_dump()
    else:
        return StandardResponse(
            success=False, 
            message=f"Failed to delete relationship from '{request.from_entity}'. Make sure all fields match exactly with what was used when creating the relationship.",
            data={
                "from_entity": request.from_entity, 
                "to_entity": request.to_entity,
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
