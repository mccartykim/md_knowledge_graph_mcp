# Markdown Knowledge Graph Notebook MCP Server
## A simple and readable external memory system for AI tools

This project is a FastMCP-based server that provides tools to manage a simple "knowledge graph notebook" stored as Markdown files. Each entity in the knowledge graph is a separate Markdown file, and relationships are defined within these files.

The intended usecase is for users to set up this tool to point to an empty Obsidian vault that humans can read and update on their own. With this workflow, a casual description can become a tidy and detailed structured graph, ideal for search and diagrams. 

This means your robot friend's memory is easy to review and fix, making the world outside their context something you can hold and touch. Add on version control, and you can roll back your bud's memory to before you said something weird, which is normal, cool, and also healthy behavior.

## Features

*   **Entity Management:** Create, delete entities.
*   **Observation Management:** Add, delete observations (textual notes) within an entity.
*   **Relationship Management:** Add, delete relationships between entities.
*   **Graph Retrieval:** Get a representation of the entire knowledge graph.

## Tools Exposed

The server exposes the following MCP tools:

*   `create_entity`: Creates a new entity.
    *   Payload: `{"name": "entity_name"}`
*   `get_graph`: Retrieves the entire knowledge graph.
    *   Payload: `{}`
*   `add_observation`: Adds an observation to an entity.
    *   Payload: `{"entity_name": "name", "observation": "text"}`
*   `add_relationship`: Adds a relationship between entities.
    *   Payload: `{"source_entity_name": "source", "verb_preposition": "verb", "target_entity": "target", "context": "optional_text"}`
*   `delete_entity`: Deletes an entity.
    *   Payload: `{"name": "entity_name"}`
*   `delete_observation`: Deletes an observation from an entity.
    *   Payload: `{"entity_name": "name", "observation": "exact_text_to_delete"}`
*   `delete_relationship`: Deletes a relationship.
    *   Payload: `{"source_entity_name": "source", "verb_preposition": "verb", "target_entity": "target", "context": "exact_context"}`

## Installation
Right now, I'm invoking it with a nix flake because I'm a crazy person who loves nix. The happiest path will be for you to install nix with the Determinate Installer, and add the stdio invocation for `nix run github:mccartykim/md_knowledge_graph_mcp`. 

Claude/Windsurf config style:

```
"mcp_servers" : { 
  "md_knowledge_graph": {
      "command": "nix",
      "args": [
        "run",
        "github:mccartykim/md_knowledge_graph_mcp"
      ],
      "env" : {
        "MD_NOTEBOOK_KNOWLEDGE_GRAPH_DIR": "/Users/your_name/personal/knowledge_graph"
      }
  }
}
```

This can also run via uv. Clone this repo and `uv run server`, I'm hoping to publish this soon on pypy for easier setup.

The Markdown files for the knowledge graph are stored in a directory specified by the `KG_MCP_MARKDOWN_PATH` environment variable. If not set, it defaults to a local directory named `kg_markdown_data`.


## Example entity:
```
# Pleiades

Pleiades is Kimberly's cat, also called Plady for short

Named after the Pleiades star system, which is also what Subaru is named after. Cat is short and rumbly like a Subaru car.

## Relationships
- named_after [[Subaru]] Pleiades (Plady) the cat was named after Kimberly's Subaru.
```

As you can see, we have the Name, Observations separated by newlines, and then a list of relationships in a `verb [[link]] maybe some context afterwards` type pattern.

## Testing

Unit tests are provided in the `tests/` directory:

*   `test_kg_core.py`: Tests the core Markdown file manipulation logic.
*   `test_server_tools.py`: Tests the MCP tools using the `fastmcp.Client`.

To run tests (assuming they are in a package structure):
```bash
# From the root of this server's directory
python -m unittest discover tests
# Or if pytest is used:
# pytest tests/
```

## Examples

The `examples/` directory contains resources to help you get started:

* `system_prompt.md` - A sample system prompt for LLMs interacting with this knowledge graph system, designed for long-context models that can reload the knowledge graph as needed.
* `sample_kg_entry.md` - An example entity entry showing the expected markdown format.
* `mcp_server_guide.md` - Comprehensive guide for integrating this MCP server with various LLM agents and clients, including configuration examples for Claude Desktop, Goose, Continue, and others. Includes best practices for agent memory management.
