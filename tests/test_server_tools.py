import unittest
import tempfile
import shutil
from pathlib import Path
import os
import asyncio
import sys # Added
import json
from typing import Any, Dict, Optional, TypeVar, Type

from fastmcp import Client, FastMCP

# Add parent directory (new project root) to sys.path for direct import of server and kg_core
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server import (
    app,
    # Removed imports for request Pydantic models
    StandardResponse,
    KnowledgeGraphResponse,
)
import server # Import the module itself for patching

# Generic type for Pydantic models
T = TypeVar('T')

def parse_tool_response(response: list, model_class: Type[T]) -> T:
    """Helper function to parse FastMCP tool responses which may be TextContent objects."""
    if not response or not isinstance(response, list) or len(response) == 0:
        raise ValueError("Invalid response format: empty or not a list")
    
    item = response[0]
    
    # Handle TextContent objects (which have a text attribute containing JSON)
    if hasattr(item, 'text'):
        try:
            content_dict = json.loads(item.text)
            return model_class(**content_dict)
        except Exception as e:
            raise ValueError(f"Error parsing TextContent: {e}")
    
    # Handle direct dict responses
    return model_class(**item)

class TestMCPServerTools(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        # Create a unique temp directory for each test
        self.test_dir = tempfile.mkdtemp(prefix=f"kg_test_{self._testMethodName}_")
        print(f"Created test directory: {self.test_dir}")
        
        # Create a fresh service instance for each test
        self.test_kg_service = server.AsyncKnowledgeGraphService(directory_path=self.test_dir)
        
        # Store the original service and replace it with our test instance
        self.original_kg_service_attribute = server.kg_async_service
        server.kg_async_service = self.test_kg_service
        
        # Update path in server module
        self.original_kg_path = server.KG_MARKDOWN_BASE_PATH
        server.KG_MARKDOWN_BASE_PATH = self.test_dir

        # Set up the client
        self.client = Client(app)
        await self.client.__aenter__()

    async def asyncTearDown(self):
        try:
            await self.client.__aexit__(None, None, None)
        except Exception as e:
            print(f"WARNING: Error during client exit: {e}")
            
        # Restore original service and path
        server.kg_async_service = self.original_kg_service_attribute
        server.KG_MARKDOWN_BASE_PATH = self.original_kg_path
        
        # Clean up the test directory
        try:
            if os.path.exists(self.test_dir):
                print(f"Cleaning up test directory: {self.test_dir}")
                shutil.rmtree(self.test_dir)
        except Exception as e:
            print(f"WARNING: Error during directory cleanup: {e}")

    async def test_create_entity_tool(self):
        entity_name = "ToolTestEntity"
        # Calling tool with parameters in a dictionary
        raw_response = await self.client.call_tool("create_entity", {"entity_name": entity_name})
        
        self.assertIsInstance(raw_response, list)
        self.assertEqual(len(raw_response), 1)
        
        response = parse_tool_response(raw_response, StandardResponse)
        self.assertTrue(response.success)
        self.assertEqual(response.message, f"Entity '{entity_name}' created successfully.")
        self.assertTrue((Path(self.test_dir) / f"{entity_name}.md").exists())

    async def test_create_existing_entity_tool_fails(self):
        entity_name = "ToolTestEntityExists"
        # Create first entity with parameters in a dictionary
        await self.client.call_tool("create_entity", {"entity_name": entity_name})
        # Attempt to create again with parameters in a dictionary
        raw_response = await self.client.call_tool("create_entity", {"entity_name": entity_name})
        self.assertIsInstance(raw_response, list)
        self.assertEqual(len(raw_response), 1)
        response = parse_tool_response(raw_response, StandardResponse)
        self.assertFalse(response.success)
        self.assertEqual(response.message, f"Entity '{entity_name}' already exists.")

    async def test_get_graph_tool_empty(self):
        raw_response = await self.client.call_tool("get_graph", {}) # This tool takes no arguments, pass empty dictionary
        self.assertIsInstance(raw_response, list)
        self.assertEqual(len(raw_response), 1)
        
        response = parse_tool_response(raw_response, KnowledgeGraphResponse)
        self.assertEqual(response.entities, {})
        self.assertEqual(response.relationships, [])

    async def test_get_graph_tool__with_data(self):
        entity_name = "GraphDataEntity"
        # Create entity with parameters in a dictionary
        await self.client.call_tool("create_entity", {"entity_name": entity_name})
        raw_response = await self.client.call_tool("get_graph", {}) # This tool takes no arguments, pass empty dictionary
        self.assertIsInstance(raw_response, list)
        self.assertEqual(len(raw_response), 1)
        response = parse_tool_response(raw_response, KnowledgeGraphResponse)
        self.assertIn(entity_name, response.entities)

    async def test_add_observation_tool(self):
        entity_name = "ObsToolEntity"
        observation_text = "This is a test observation via tool."
        # Ensure the entity is created
        await self.client.call_tool("create_entity", {"entity_name": entity_name})

        # Add observation with parameters in a dictionary
        raw_response = await self.client.call_tool("add_observation", {"entity_name": entity_name, "observation_text": observation_text})
        
        self.assertIsInstance(raw_response, list)
        self.assertEqual(len(raw_response), 1)
        response = parse_tool_response(raw_response, StandardResponse)
        self.assertTrue(response.success, response.message)

        with open(Path(self.test_dir) / f"{entity_name}.md", 'r') as f:
            content = f.read()
        self.assertIn(observation_text, content)

    async def test_add_relationship_tool(self):
        source_entity = "SourceEntityForRel"
        target_entity = "TargetEntityForRel"
        verb = "connects to"
        context_text = "via a test relationship"

        # Ensure entities are created
        await self.client.call_tool("create_entity", {"entity_name": source_entity})
        await self.client.call_tool("create_entity", {"entity_name": target_entity})

        # Add relationship with parameters in a dictionary
        raw_response = await self.client.call_tool(
            "add_relationship", 
            {
                "from_entity": source_entity,
                "relationship_type": verb,
                "to_entity": target_entity,
                "details": context_text
            }
        )
        
        self.assertIsInstance(raw_response, list)
        self.assertEqual(len(raw_response), 1)
        response = parse_tool_response(raw_response, StandardResponse)
        self.assertTrue(response.success, response.message)

        with open(Path(self.test_dir) / f"{source_entity}.md", 'r') as f:
            content = f.read()
        # Adjusted assertion to match potential formatting in MarkdownKnowledgeGraph
        # Assuming it adds the details after the link
        self.assertIn(f"- {verb} [[{target_entity}]] {context_text}", content)
    
    async def test_delete_entity_tool_success(self):
        entity_name = "EntityToDeleteViaTool"
        
        # Create entity with parameters in a dictionary
        await self.client.call_tool("create_entity", {"entity_name": entity_name})
        
        self.assertTrue((Path(self.test_dir) / f"{entity_name}.md").exists(), "Entity was not created for delete test")

        # Delete entity with parameters in a dictionary
        raw_response = await self.client.call_tool("delete_entity", {"entity_name": entity_name})

        self.assertIsInstance(raw_response, list)
        self.assertEqual(len(raw_response), 1)
        response = parse_tool_response(raw_response, StandardResponse)

        self.assertTrue(response.success, f"Delete entity failed: {response.message}")
        self.assertEqual(response.message, f"Entity '{entity_name}' and its relationships deleted successfully.")
        
        self.assertFalse((Path(self.test_dir) / f"{entity_name}.md").exists(), "Entity file was not deleted")

    async def test_delete_entity_tool_not_found(self):
        entity_name = "NonExistentForDelete"
        
        # Delete non-existent entity with parameters in a dictionary
        raw_response = await self.client.call_tool("delete_entity", {"entity_name": entity_name})

        self.assertIsInstance(raw_response, list)
        self.assertEqual(len(raw_response), 1)
        response = parse_tool_response(raw_response, StandardResponse)

        self.assertFalse(response.success)
        self.assertEqual(response.message, f"Entity '{entity_name}' not found for deletion.")

    async def test_delete_observation_tool_success(self):
        entity_name = "EntityForObsDelete"
        obs_to_keep = "This observation stays."
        obs_to_delete = "This observation will be deleted."

        # Ensure the entity is created
        await self.client.call_tool("create_entity", {"entity_name": entity_name})
        # Add observations with parameters in a dictionary
        await self.client.call_tool("add_observation", {"entity_name": entity_name, "observation_text": obs_to_keep})
        await self.client.call_tool("add_observation", {"entity_name": entity_name, "observation_text": obs_to_delete})

        # Delete observation with parameters in a dictionary
        raw_response = await self.client.call_tool("delete_observation", {"entity_name": entity_name, "observation_text": obs_to_delete})
        
        self.assertIsInstance(raw_response, list)
        response = parse_tool_response(raw_response, StandardResponse)
        self.assertTrue(response.success, response.message)

        with open(Path(self.test_dir) / f"{entity_name}.md", 'r') as f:
            content = f.read()
        self.assertNotIn(obs_to_delete, content)
        self.assertIn(obs_to_keep, content)

    async def test_delete_observation_tool_entity_not_found(self):
        # Attempt to delete observation for non-existent entity with parameters in a dictionary
        raw_response = await self.client.call_tool("delete_observation", {"entity_name": "NonExistentEntityObs", "observation_text": "Any obs"})
        response = parse_tool_response(raw_response, StandardResponse)
        self.assertFalse(response.success)
        self.assertEqual(response.message, "Entity 'NonExistentEntityObs' not found.")
        
    async def test_delete_observation_tool_obs_not_found(self):
        entity_name = "EntityObsNotFound"
        # Ensure the entity is created
        await self.client.call_tool("create_entity", {"entity_name": entity_name})
        
        # Attempt to delete non-existent observation with parameters in a dictionary
        raw_response = await self.client.call_tool("delete_observation", {"entity_name": entity_name, "observation_text": "This observation does not exist."})
        response = parse_tool_response(raw_response, StandardResponse)
        self.assertFalse(response.success)
        self.assertIn("Failed to delete observation", response.message)

    async def test_delete_relationship_tool_success(self):
        src = "RelDelSrc"
        tgt = "RelDelTgt"
        verb = "to be deleted"
        ctx = "exact context"
        
        # Ensure entities are created
        await self.client.call_tool("create_entity", {"entity_name": src})
        await self.client.call_tool("create_entity", {"entity_name": tgt})
        # Add relationships with parameters in a dictionary
        await self.client.call_tool("add_relationship", {"from_entity": src, "relationship_type": verb, "to_entity": tgt, "details": ctx})
        await self.client.call_tool("add_relationship", {"from_entity": src, "relationship_type": "to keep", "to_entity": tgt, "details": "different"})

        # Delete relationship with parameters in a dictionary
        raw_response = await self.client.call_tool(
            "delete_relationship",
            {
                "from_entity": src,
                "relationship_type": verb,
                "to_entity": tgt,
                "details": ctx
            }
        )
        response = parse_tool_response(raw_response, StandardResponse)
        self.assertTrue(response.success, response.message)

        with open(Path(self.test_dir) / f"{src}.md", 'r') as f:
            content = f.read()
        # Adjusted assertion to match potential formatting in MarkdownKnowledgeGraph
        # Assuming it adds the details after the link
        self.assertNotIn(f"- {verb} [[{tgt}]] {ctx}", content)
        self.assertIn(f"- to keep [[{tgt}]] different", content)

    async def test_delete_relationship_tool_source_not_found(self):
        # Attempt to delete relationship for non-existent source with parameters in a dictionary
        raw_response = await self.client.call_tool("delete_relationship", {"from_entity": "NonExistentSourceRel", "relationship_type": "v", "to_entity": "t", "details": "c"})
        response = parse_tool_response(raw_response, StandardResponse)
        self.assertFalse(response.success)
        self.assertEqual(response.message, "Source entity 'NonExistentSourceRel' not found.")

    async def test_delete_relationship_tool_rel_not_found(self):
        src = "RelNotFoundSrc"
        tgt = "RelNotFoundTgt"
        # Ensure entities are created
        await self.client.call_tool("create_entity", {"entity_name": src})
        await self.client.call_tool("create_entity", {"entity_name": tgt})

        # Attempt to delete non-existent relationship with parameters in a dictionary
        raw_response = await self.client.call_tool(
            "delete_relationship", 
            {
                "from_entity": src,
                "relationship_type": "non-existent verb",
                "to_entity": tgt,
                "details": "no match"
            }
        )
        response = parse_tool_response(raw_response, StandardResponse)
        self.assertFalse(response.success)
        self.assertIn("Failed to delete relationship", response.message)
    
if __name__ == '__main__':
    unittest.main()
