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
# Removed imports for EntityNameRequest, ObservationRequest, RelationshipRequest
from server import (
    StandardResponse,
    KnowledgeGraphResponse
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
    
    # Removed test_model_serialization as the request models were removed
    # def test_model_serialization(self):
    #     """Test that Pydantic models properly serialize to JSON."""
    #     ...

    
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
    
