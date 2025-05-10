import unittest
import tempfile
import shutil
from pathlib import Path
import os

import sys # Added
from pathlib import Path # Added

# Add parent directory (new project root) to sys.path for direct import of kg_core
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kg_core import MarkdownKnowledgeGraph

class TestMarkdownKnowledgeGraph(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.kg = MarkdownKnowledgeGraph(directory_path=self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_01_create_new_entity(self):
        entity_name = "TestEntity1"
        self.assertTrue(self.kg.newEntity(entity_name), "newEntity should return True on success")
        entity_file = Path(self.test_dir) / f"{entity_name}.md"
        self.assertTrue(entity_file.exists(), "Entity markdown file was not created")
        with open(entity_file, 'r') as f:
            content = f.read()
        self.assertEqual(content, f"# {entity_name}\n\n", "Entity file content is incorrect")

    def test_02_create_existing_entity_fails(self):
        entity_name = "TestEntity_Exists"
        self.kg.newEntity(entity_name) 
        self.assertFalse(self.kg.newEntity(entity_name), "newEntity should return False for existing entity")

    def test_03_add_observation_new_entity(self):
        entity_name = "ObsTestEntity"
        self.kg.newEntity(entity_name)
        observation1 = "This is observation one."
        self.assertTrue(self.kg.newObservation(entity_name, observation1), "newObservation should return True")
        
        entity_file = Path(self.test_dir) / f"{entity_name}.md"
        with open(entity_file, 'r') as f:
            content = f.read()
        
        expected_content = f"# {entity_name}\n\n{observation1}\n\n"
        self.assertEqual(content, expected_content, "Observation was not added correctly")

        observation2 = "This is observation two, added later."
        self.assertTrue(self.kg.newObservation(entity_name, observation2))
        with open(entity_file, 'r') as f:
            content = f.read()
        expected_content_after_obs2 = f"# {entity_name}\n\n{observation1}\n\n{observation2}\n\n"
        self.assertEqual(content, expected_content_after_obs2, "Second observation not appended correctly")

    def test_04_add_observation_to_nonexistent_entity(self):
        self.assertFalse(self.kg.newObservation("NonExistentEntity", "Some observation"))

    def test_05_add_relationship_simple(self):
        entity_a = "EntityA"
        entity_b = "EntityB"
        self.kg.newEntity(entity_a)
        self.kg.newEntity(entity_b)

        verb = "links to"
        context = "as a test"
        self.assertTrue(self.kg.newRelationship(entity_a, verb, entity_b, context))

        entity_a_file = Path(self.test_dir) / f"{entity_a}.md"
        with open(entity_a_file, 'r') as f:
            content = f.read()
        
        expected_relationship_line = f"- {verb} [[{entity_b}]] {context}"
        self.assertIn("## Relationships", content)
        self.assertIn(expected_relationship_line, content)

    def test_06_add_relationship_no_context(self):
        entity_c = "EntityC"
        entity_d = "EntityD"
        self.kg.newEntity(entity_c)
        self.kg.newEntity(entity_d)
        verb = "points at"
        self.assertTrue(self.kg.newRelationship(entity_c, verb, entity_d, ""))
        self.assertTrue(self.kg.newRelationship(entity_c, verb, entity_d, None))

        entity_c_file = Path(self.test_dir) / f"{entity_c}.md"
        with open(entity_c_file, 'r') as f:
            content = f.read()
        
        expected_line_empty_ctx = f"- {verb} [[{entity_d}]]"
        self.assertIn(expected_line_empty_ctx, content.replace(" \n","\n"))

    def test_07_add_relationship_to_nonexistent_source(self):
        self.assertFalse(self.kg.newRelationship("NonExistentSource", "verb", "EntityA"))
    
    def test_08_add_self_referential_relationship_fails(self):
        entity_self_ref = "SelfRefEntity"
        self.kg.newEntity(entity_self_ref)
        self.assertFalse(self.kg.newRelationship(entity_self_ref, "self links", entity_self_ref, "should fail"))

    def test_09_get_knowledge_graph_empty(self):
        graph = self.kg.getKnowledgeGraph()
        self.assertEqual(graph, {"entities": {}, "relationships": []})

    def test_10_get_knowledge_graph_populated(self):
        self.kg.newEntity("Node1")
        self.kg.newEntity("Node2")
        self.kg.newObservation("Node1", "Obs 1 for Node1")
        self.kg.newRelationship("Node1", "connects to", "Node2", "via test")

        graph = self.kg.getKnowledgeGraph()
        self.assertIn("Node1", graph["entities"])
        self.assertIn("Node2", graph["entities"])
        self.assertEqual(len(graph["entities"]["Node1"]["observations"]), 1)
        self.assertEqual(graph["entities"]["Node1"]["observations"][0], "Obs 1 for Node1")
        self.assertEqual(len(graph["relationships"]), 1)
        rel = graph["relationships"][0]
        self.assertEqual(rel["source"], "Node1")
        self.assertEqual(rel["verb"], "connects to")
        self.assertEqual(rel["target"], "Node2")
        self.assertEqual(rel["context"], "via test")

    def test_11_delete_entity(self):
        entity_to_delete = "ToDelete"
        other_entity = "Other"
        self.kg.newEntity(entity_to_delete)
        self.kg.newEntity(other_entity)
        self.kg.newRelationship(other_entity, "links to", entity_to_delete, "will vanish")
        
        self.assertTrue(self.kg.deleteEntity(entity_to_delete))
        entity_file = Path(self.test_dir) / f"{entity_to_delete}.md"
        self.assertFalse(entity_file.exists(), "Deleted entity file still exists")

        other_entity_file = Path(self.test_dir) / f"{other_entity}.md"
        with open(other_entity_file, 'r') as f:
            content = f.read()
        self.assertNotIn(f"[[{entity_to_delete}]]", content, "Link to deleted entity not removed")

    def test_12_delete_nonexistent_entity(self):
        self.assertFalse(self.kg.deleteEntity("NonExistentToDelete"))

    def test_13_delete_observation(self):
        entity = "ObsDelEntity"
        obs1 = "Observation to keep"
        obs2 = "Observation to delete"
        self.kg.newEntity(entity)
        self.kg.newObservation(entity, obs1)
        self.kg.newObservation(entity, obs2)

        self.assertTrue(self.kg.deleteObservation(entity, obs2))
        entity_file = Path(self.test_dir) / f"{entity}.md"
        with open(entity_file, 'r') as f:
            content = f.read()
        self.assertIn(obs1, content)
        self.assertNotIn(obs2, content)
    
    def test_14_delete_relationship(self):
        entity1 = "RelDelSource"
        entity2 = "RelDelTarget"
        verb = "will be deleted"
        context = "this specific one"
        self.kg.newEntity(entity1)
        self.kg.newEntity(entity2)
        self.kg.newRelationship(entity1, verb, entity2, context)
        self.kg.newRelationship(entity1, "another link", entity2, "to keep")

        self.assertTrue(self.kg.deleteRelationship(entity1, verb, entity2, context))
        entity_file = Path(self.test_dir) / f"{entity1}.md"
        with open(entity_file, 'r') as f:
            content = f.read()
        
        deleted_line_fragment = f"- {verb} [[{entity2}]] {context}" 
        kept_line_fragment = f"- another link [[{entity2}]] to keep"
        
        self.assertNotIn(deleted_line_fragment, content)
        self.assertIn(kept_line_fragment, content)

if __name__ == '__main__':
    unittest.main()
