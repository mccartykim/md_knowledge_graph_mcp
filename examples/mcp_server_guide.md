# Guide: Using the Knowledge Graph MCP Server with LLM Agents

This guide explains how to integrate this Knowledge Graph MCP Server with various LLM agents to create an agent that can actively maintain its own memory system.

## Why Use This Tool?

This Knowledge Graph MCP Server provides essential capabilities for LLM agents to create, maintain, and recall information in a persistent, structured manner:

1. **Persistent Memory**: Long-term, structured storage of information beyond a single conversation
2. **Bidirectional Relationships**: Explicitly model how entities relate to each other
3. **Semantic Structure**: Information is organized in a meaningful, navigable way
4. **Contextual Recall**: Bring relevant information into context when needed

## Integration Examples

Below are examples of how to configure popular MCP clients to use this Knowledge Graph server.

### For Claude Desktop App

1. Go to Settings → MCP Servers → Add New Server
2. Configure with the following settings:
   - Name: `Knowledge Graph Notebook`
   - Description: `Markdown-based persistent memory system for storing entities and relationships`
   - Transport: `stdio`
   - Command: Path to your Python interpreter followed by the server.py path
     ```
     /path/to/python /path/to/knowledge_graph_mcp_server/server.py
     ```
   - Environment Variables: Add `MD_NOTEBOOK_KNOWLEDGE_GRAPH_DIR` with path to your desired markdown storage location

3. Sample System Prompt Addition:
   ```
   You have access to a Knowledge Graph memory system through MCP tools. Use these tools to:
   
   1. Record important information about people, places, concepts, and things
   2. Create relationships between entities
   3. Recall information when needed for current conversations
   
   Your memory storage is in {MD_NOTEBOOK_KNOWLEDGE_GRAPH_DIR}. Remember to:
   - Create entities for important concepts that will need referencing later
   - Add observations as atomic facts
   - Create bidirectional relationships between entities
   - Periodically reload your memory to ensure you have the latest information
   ```

### For Goose

Add to your Goose configuration file:

```yaml
extensions:
  - name: "Knowledge Graph Notebook"
    type: "mcp"
    transport:
      type: "stdio"
      command: "python /path/to/knowledge_graph_mcp_server/server.py"
    env:
      MD_NOTEBOOK_KNOWLEDGE_GRAPH_DIR: "/path/to/your/markdown/storage"
```

### For Continue

Add to your Continue configuration:

```json
{
  "mcpServers": [
    {
      "name": "Knowledge Graph Memory",
      "description": "Persistent memory system for storing entities and relationships",
      "transport": {
        "type": "stdio",
        "command": "python /path/to/knowledge_graph_mcp_server/server.py"
      },
      "env": {
        "MD_NOTEBOOK_KNOWLEDGE_GRAPH_DIR": "/path/to/your/markdown/storage"
      }
    }
  ]
}
```

## Best Practices for Agent Memory Management

For optimal use of this memory system with agents:

1. **Active Memory Management**: Encourage your agent to:
   - Create entities for important information that will be referenced later
   - Add observations proactively during conversations
   - Create relationships to connect related information
   - Look up relevant entities at the start of conversations about known topics

2. **Memory Refreshing Pattern**: For long-context models, use this pattern:
   ```
   AGENT: Let me check my memory for relevant information.
   *Uses get_graph tool to load the entire knowledge graph*
   AGENT: Based on my memory, I recall that...
   ```

3. **Double Bookkeeping**: When creating relationships, always create reciprocal relationships in both directions:
   ```
   # First relationship (Person to Company)
   {"from_entity": "JohnDoe", "relationship_type": "works at", "to_entity": "TechCorp", "details": "as engineer"}
   
   # Second relationship (Company to Person)
   {"from_entity": "TechCorp", "relationship_type": "employs", "to_entity": "JohnDoe", "details": "as engineer"}
   ```
   
   This ensures bidirectional navigation and completeness of your knowledge graph.

4. **Progressive Detail**: Start with basic entity information, then add detail over time as you learn more.

## Sample Agent Configuration

This sample system prompt section helps agents effectively use the Knowledge Graph:

```
# Memory Management

You have access to a persistent knowledge graph memory system through MCP tools. This system stores information as markdown files with named entities and relationships between them.

## Available Memory Tools:
- `create_entity`: Creates a new entity with a given name (field: `entity_name`)
- `add_observation`: Adds factual information to an entity (fields: `entity_name`, `observation_text`)
- `add_relationship`: Creates a relationship between two entities (fields: `from_entity`, `relationship_type`, `to_entity`, `details`)
- `get_graph`: Retrieves the entire knowledge graph
- `delete_entity`: Removes an entity and its relationships (field: `entity_name`)
- `delete_observation`: Removes specific information from an entity (fields: `entity_name`, `observation_text`)
- `delete_relationship`: Removes a relationship between entities (fields: `from_entity`, `relationship_type`, `to_entity`, `details`)

## When to Use Memory:
- CREATE entities for important people, places, concepts, or things
- ADD observations when you learn new facts about entities
- CONNECT entities with explicit relationships
- RETRIEVE relevant information at the start of conversations
- REFRESH your knowledge when significant updates occur

Remember that you should practice "double bookkeeping" - if entity A relates to entity B, create a reciprocal relationship from B to A.
```

By configuring your agent with this memory system, it can develop a sophisticated, bidirectional knowledge graph that grows and evolves with use.