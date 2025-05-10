import unittest
import tempfile
import shutil
from pathlib import Path
import os
import asyncio
import sys # Added

from fastmcp import Client, FastMCP

# Add parent directory (new project root) to sys.path for direct import of server and kg_core
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server import ( # Now direct
    app,
    EntityNameRequest,
    ObservationRequest,
    RelationshipRequest,
    DeleteEntityRequest,
    DeleteObservationRequest,
    DeleteRelationshipRequest,
    StandardResponse,
    KnowledgeGraphResponse,
)
import server # Import the module itself for patching

class TestMCPServerTools(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.test_dir = tempfile.mkdtemp()
        
        # Create a new service instance specifically for this test, using the temp directory
        # Access original class via the imported module's current kg_async_service
        self.test_kg_service = server.kg_async_service.__class__(directory_path=self.test_dir)
        
        # Store and patch the kg_async_service attribute in the imported server module
        self.original_kg_service_attribute = server.kg_async_service
        server.kg_async_service = self.test_kg_service

        self.client = Client(app) # mcp_app should now use the patched service for this test
        await self.client.__aenter__()

    async def asyncTearDown(self):
        await self.client.__aexit__(None, None, None)
        # Restore the original kg_async_service attribute in the server module
        server.kg_async_service = self.original_kg_service_attribute 
        shutil.rmtree(self.test_dir)

    async def test_create_entity_tool(self):
        entity_name = "ToolTestEntity"
        payload = EntityNameRequest(name=entity_name)
        raw_response = await self.client.call_tool("create_entity", payload.model_dump())
        self.assertIsInstance(raw_response, list)
        self.assertEqual(len(raw_response), 1)
        response = StandardResponse(**raw_response[0])
        self.assertTrue(response.success)
        self.assertEqual(response.message, f"Entity '{entity_name}' created successfully.")
        self.assertTrue((Path(self.test_dir) / f"{entity_name}.md").exists())

    async def test_create_existing_entity_tool_fails(self):
        entity_name = "ToolTestEntityExists"
        await self.client.call_tool("create_entity", EntityNameRequest(name=entity_name).model_dump())
        raw_response = await self.client.call_tool("create_entity", EntityNameRequest(name=entity_name).model_dump())
        self.assertIsInstance(raw_response, list)
        self.assertEqual(len(raw_response), 1)
        response = StandardResponse(**raw_response[0])
        self.assertFalse(response.success)
        self.assertEqual(response.message, f"Entity '{entity_name}' already exists.")

    async def test_get_graph_tool_empty(self):
        raw_response = await self.client.call_tool("get_graph", {})
        self.assertIsInstance(raw_response, list)
        self.assertEqual(len(raw_response), 1)
        response = KnowledgeGraphResponse(**raw_response[0])
        self.assertEqual(response.entities, {})
        self.assertEqual(response.relationships, [])

    async def test_get_graph_tool__with_data(self):
        entity_name = "GraphDataEntity"
        await self.client.call_tool("create_entity", EntityNameRequest(name=entity_name).model_dump())
        raw_response = await self.client.call_tool("get_graph", {})
        self.assertIsInstance(raw_response, list)
        self.assertEqual(len(raw_response), 1)
        response = KnowledgeGraphResponse(**raw_response[0])
        self.assertIn(entity_name, response.entities)

    async def test_add_observation_tool(self):
        entity_name = "ObsToolEntity"
        observation_text = "This is a test observation via tool."
        await self.client.call_tool("create_entity", {"name": entity_name})

        payload = ObservationRequest(entity_name=entity_name, observation=observation_text)
        
        raw_response = await self.client.call_tool("add_observation", payload.model_dump())
        
        self.assertIsInstance(raw_response, list)
        self.assertEqual(len(raw_response), 1)
        response = StandardResponse(**raw_response[0])
        self.assertTrue(response.success, response.message)

        with open(Path(self.test_dir) / f"{entity_name}.md", 'r') as f:
            content = f.read()
        self.assertIn(observation_text, content)

    async def test_add_relationship_tool(self):
        source_entity = "SourceEntityForRel"
        target_entity = "TargetEntityForRel"
        verb = "connects to"
        context_text = "via a test relationship"

        await self.client.call_tool("create_entity", {"name": source_entity})
        await self.client.call_tool("create_entity", {"name": target_entity})

        payload = RelationshipRequest(
            source_entity_name=source_entity,
            verb_preposition=verb,
            target_entity=target_entity,
            context=context_text
        )
        raw_response = await self.client.call_tool("add_relationship", payload.model_dump())
        
        self.assertIsInstance(raw_response, list)
        self.assertEqual(len(raw_response), 1)
        response = StandardResponse(**raw_response[0])
        self.assertTrue(response.success, response.message)

        with open(Path(self.test_dir) / f"{source_entity}.md", 'r') as f:
            content = f.read()
        self.assertIn(f"- {verb} [[{target_entity}]] {context_text}", content)
    

    async def test_delete_entity_tool_success(self):
        entity_name = "EntityToDeleteViaTool"
        
        create_payload = EntityNameRequest(name=entity_name)
        await self.client.call_tool("create_entity", create_payload.model_dump())
        
        self.assertTrue((Path(self.test_dir) / f"{entity_name}.md").exists(), "Entity was not created for delete test")

        delete_payload = DeleteEntityRequest(name=entity_name)
        raw_response = await self.client.call_tool("delete_entity", delete_payload.model_dump())

        self.assertIsInstance(raw_response, list)
        self.assertEqual(len(raw_response), 1)
        response = StandardResponse(**raw_response[0])

        self.assertTrue(response.success, f"Delete entity failed: {response.message}")
        self.assertEqual(response.message, f"Entity '{entity_name}' and its relationships deleted successfully.")
        
        self.assertFalse((Path(self.test_dir) / f"{entity_name}.md").exists(), "Entity file was not deleted")

    async def test_delete_entity_tool_not_found(self):
        entity_name = "NonExistentForDelete"
        
        delete_payload = DeleteEntityRequest(name=entity_name)
        raw_response = await self.client.call_tool("delete_entity", delete_payload.model_dump())

        self.assertIsInstance(raw_response, list)
        self.assertEqual(len(raw_response), 1)
        response = StandardResponse(**raw_response[0])

        self.assertFalse(response.success)
        self.assertEqual(response.message, f"Entity '{entity_name}' not found for deletion.")
    async def test_delete_observation_tool_success(self):
        entity_name = "EntityForObsDelete"
        obs_to_keep = "This observation stays."
        obs_to_delete = "This observation will be deleted."

        await self.client.call_tool("create_entity", {"name": entity_name})
        obs_payload1 = ObservationRequest(entity_name=entity_name, observation=obs_to_keep)
        await self.client.call_tool("add_observation", obs_payload1.model_dump())
        obs_payload2 = ObservationRequest(entity_name=entity_name, observation=obs_to_delete)
        await self.client.call_tool("add_observation", obs_payload2.model_dump())

        delete_obs_payload = DeleteObservationRequest(entity_name=entity_name, observation=obs_to_delete)
        raw_response = await self.client.call_tool("delete_observation", delete_obs_payload.model_dump())
        
        self.assertIsInstance(raw_response, list)
        response = StandardResponse(**raw_response[0])
        self.assertTrue(response.success, response.message)

        with open(Path(self.test_dir) / f"{entity_name}.md", 'r') as f:
            content = f.read()
        self.assertNotIn(obs_to_delete, content)
        self.assertIn(obs_to_keep, content)

    async def test_delete_observation_tool_entity_not_found(self):
        payload = DeleteObservationRequest(entity_name="NonExistentEntityObs", observation="Any obs")
        raw_response = await self.client.call_tool("delete_observation", payload.model_dump())
        response = StandardResponse(**raw_response[0])
        self.assertFalse(response.success)
        self.assertEqual(response.message, "Entity 'NonExistentEntityObs' not found.")
        
    async def test_delete_observation_tool_obs_not_found(self):
        entity_name = "EntityObsNotFound"
        await self.client.call_tool("create_entity", {"name": entity_name})
        
        payload = DeleteObservationRequest(entity_name=entity_name, observation="This observation does not exist.")
        raw_response = await self.client.call_tool("delete_observation", payload.model_dump())
        response = StandardResponse(**raw_response[0])
        self.assertFalse(response.success)
        self.assertIn("Failed to delete observation", response.message)
    async def test_delete_relationship_tool_success(self):
        src = "RelDelSrc"
        tgt = "RelDelTgt"
        verb = "to be deleted"
        ctx = "exact context"
        
        await self.client.call_tool("create_entity", {"name": src})
        await self.client.call_tool("create_entity", {"name": tgt})
        rel_payload = RelationshipRequest(source_entity_name=src, verb_preposition=verb, target_entity= tgt, context=ctx)
        await self.client.call_tool("add_relationship", rel_payload.model_dump())
        rel_payload_keep = RelationshipRequest(source_entity_name=src, verb_preposition="to keep", target_entity=tgt, context="different")
        await self.client.call_tool("add_relationship", rel_payload_keep.model_dump())

        del_rel_payload = DeleteRelationshipRequest(
            source_entity_name=src, verb_preposition=verb, target_entity=tgt, context=ctx
        )
        raw_response = await self.client.call_tool("delete_relationship", del_rel_payload.model_dump())
        response = StandardResponse(**raw_response[0])
        self.assertTrue(response.success, response.message)

        with open(Path(self.test_dir) / f"{src}.md", 'r') as f:
            content = f.read()
        self.assertNotIn(f"- {verb} [[{tgt}]] {ctx}", content)
        self.assertIn(f"- to keep [[{tgt}]] different", content)

    async def test_delete_relationship_tool_source_not_found(self):
        payload = DeleteRelationshipRequest(source_entity_name="NonExistentSourceRel", verb_preposition="v", target_entity="t", context="c")
        raw_response = await self.client.call_tool("delete_relationship", payload.model_dump())
        response = StandardResponse(**raw_response[0])
        self.assertFalse(response.success)
        self.assertEqual(response.message, "Source entity 'NonExistentSourceRel' not found.")

    async def test_delete_relationship_tool_rel_not_found(self):
        src = "RelNotFoundSrc"
        tgt = "RelNotFoundTgt"
        await self.client.call_tool("create_entity", {"name": src})
        await self.client.call_tool("create_entity", {"name": tgt})

        payload = DeleteRelationshipRequest(
            source_entity_name=src, verb_preposition="non-existent verb", target_entity=tgt, context="no match"
        )
        raw_response = await self.client.call_tool("delete_relationship", payload.model_dump())
        response = StandardResponse(**raw_response[0])
        self.assertFalse(response.success)
        self.assertIn("Failed to delete relationship", response.message)
    
if __name__ == '__main__':
    unittest.main()
