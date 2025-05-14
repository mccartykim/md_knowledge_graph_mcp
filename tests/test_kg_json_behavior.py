import json
import pytest
import tempfile
import shutil
import sys
from pathlib import Path
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kg_core import MarkdownKnowledgeGraph
from server import (
    EntityNameRequest, ObservationRequest, StandardResponse,
    KnowledgeGraphResponse, RelationshipRequest
)

class TestJSONHandling:
    """Tests to verify JSON handling in the knowledge graph, especially related to the
    Colonial Williamsburg bug report."""
    
    def setup_method(self):
        """Set up a temporary directory for tests."""
        self.test_dir = tempfile.mkdtemp()
        self.kg = MarkdownKnowledgeGraph(directory_path=self.test_dir)
        
        # Create test entities including Colonial Williamsburg
        self.kg.newEntity("Colonial Williamsburg")
        
        # Add the observation about malformed JSON from the markdown
        self.kg.newObservation(
            "Colonial Williamsburg", 
            "In Colonial Williamsburg, a sophisticated LLM occasionally behaves strangely, producing malformed JSON instead of expected digits."
        )
    
    def teardown_method(self):
        """Clean up temporary files after tests."""
        shutil.rmtree(self.test_dir)
    
    def test_kg_loads_colonial_williamsburg_observation(self):
        """Test that the Colonial Williamsburg entity loads properly with observations."""
        graph = self.kg.getKnowledgeGraph()
        
        # Verify Colonial Williamsburg exists in the graph
        assert "Colonial Williamsburg" in graph["entities"]
        
        # Verify the malformed JSON observation exists
        observations = graph["entities"]["Colonial Williamsburg"]["observations"]
        assert any("malformed JSON" in obs for obs in observations)
    
    def test_entities_serialize_to_valid_json(self):
        """Test that entities can be serialized to valid JSON."""
        graph = self.kg.getKnowledgeGraph()
        
        # Test JSON serialization of the entire graph
        try:
            json_str = json.dumps(graph)
            # Verify we can parse it back
            parsed = json.loads(json_str)
            assert parsed["entities"]["Colonial Williamsburg"]["name"] == "Colonial Williamsburg"
        except json.JSONDecodeError as e:
            pytest.fail(f"Failed to serialize graph to valid JSON: {e}")
    
    def test_model_serialization(self):
        """Test that Pydantic models properly serialize to JSON."""
        # Create a relationship
        self.kg.newEntity("General Store")
        self.kg.newRelationship(
            "Colonial Williamsburg", 
            "contains", 
            "General Store", 
            "which sells period-appropriate goods"
        )
        
        # Test that entity request serializes correctly
        entity_req = EntityNameRequest(entity_name="Test Entity")
        entity_json = entity_req.model_dump_json()
        assert json.loads(entity_json)["entity_name"] == "Test Entity"
        
        # Test that observation request serializes correctly
        obs_req = ObservationRequest(
            entity_name="Colonial Williamsburg",
            observation_text="New observation about JSON"
        )
        obs_json = obs_req.model_dump_json()
        parsed_obs = json.loads(obs_json)
        assert parsed_obs["entity_name"] == "Colonial Williamsburg"
        assert parsed_obs["observation_text"] == "New observation about JSON"
        
        # Test that relationship request serializes correctly
        rel_req = RelationshipRequest(
            from_entity="Colonial Williamsburg",
            relationship_type="has",
            to_entity="General Store",
            details="with historical items"
        )
        rel_json = rel_req.model_dump_json()
        parsed_rel = json.loads(rel_json)
        assert parsed_rel["from_entity"] == "Colonial Williamsburg"
        assert parsed_rel["relationship_type"] == "has"
        
        # Test graph response serialization
        graph = self.kg.getKnowledgeGraph()
        response = KnowledgeGraphResponse(**graph)
        response_json = response.model_dump_json()
        parsed_response = json.loads(response_json)
        assert "entities" in parsed_response
        assert "relationships" in parsed_response
    
    def test_standard_response_with_complex_data(self):
        """Test StandardResponse with complex nested data."""
        # Create a complex data structure
        complex_data = {
            "nested": {
                "array": [1, 2, 3],
                "object": {"key": "value"}
            },
            "items": [
                {"id": 1, "name": "Item 1"},
                {"id": 2, "name": "Item 2"}
            ]
        }
        
        # Create a StandardResponse with the complex data
        response = StandardResponse(success=True, message="Test message", data=complex_data)
        
        # Test serialization
        try:
            response_json = response.model_dump_json()
            parsed = json.loads(response_json)
            
            # Verify structure is maintained
            assert parsed["success"] is True
            assert parsed["message"] == "Test message"
            assert parsed["data"]["nested"]["array"] == [1, 2, 3]
            assert parsed["data"]["items"][1]["name"] == "Item 2"
        except json.JSONDecodeError as e:
            pytest.fail(f"Failed to serialize StandardResponse to valid JSON: {e}")
    
