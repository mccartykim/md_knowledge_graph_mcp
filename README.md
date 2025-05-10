# Knowledge Graph Notebook (MCP Server - STDIO)

This project is a FastMCP-based server that provides tools to manage a simple "knowledge graph notebook" stored as Markdown files. Each entity in the knowledge graph is a separate Markdown file, and relationships are defined within these files.

This server is designed to be run over STDIO, allowing communication with MCP clients (like Goose or other agents) that support this transport.

## Features

*   **Entity Management:** Create, delete entities.
*   **Observation Management:** Add, delete observations (textual notes) within an entity.
*   **Relationship Management:** Add, delete relationships between entities.
*   **Graph Retrieval:** Get a representation of the entire knowledge graph.

## Core Components

*   `kg_core.py`: Contains the `MarkdownKnowledgeGraph` class, which handles the direct logic of reading, writing, and parsing the Markdown files.
*   `server.py`: Defines the FastMCP application (`mcp_app`), Pydantic models for requests/responses, and exposes the knowledge graph operations as MCP tools.
*   `tests/`: Contains unit tests for `kg_core.py` and integration tests for the MCP tools in `server.py`.

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

## Running the Server (STDIO)

This server is designed to be run using the FastMCP command-line interface.

1.  **Ensure Dependencies:** Make sure `fastmcp` and `pydantic` are installed in your Python environment (e.g., via `uv pip install fastmcp pydantic` or from a `pyproject.toml` if this server is a separate package).

2.  **Run using `fastmcp run`:**
    The `fastmcp run` command is used to launch the server. You'll need to specify the path to the server module and the `mcp_app` instance, along with the desired transport. For STDIO:

    Option A (if running from the parent directory of `extensions`):
    ```bash
    uvx fastmcp run extensions.knowledge_graph_mcp.server:mcp_app --transport stdio
    ```

    Option B (if `fastmcp run` can take a direct file path and you are inside the `knowledge_graph_mcp` directory):
    ```bash
    uvx fastmcp run server.py --transport stdio 
    ```
    *(Consult FastMCP documentation for the exact syntax of `fastmcp run` regarding file paths vs module paths.)*

    The server will then listen on `stdin` for JSON-RPC requests and send responses to `stdout`. Log messages (if any from FastMCP or your tools) might go to `stderr`.

**Example Manual Invocation (using `fastmcp run`):**
Assuming you are in the `knowledge_graph_mcp` directory and Option B works:
```bash
echo '{"jsonrpc": "2.0", "method": "create_entity", "params": {"name": "MyTestEntityFromSTDIO"}, "id": 1}' | uvx fastmcp run server.py --transport stdio
```
Or using Option A (from parent of `extensions`):
```bash
echo '{"jsonrpc": "2.0", "method": "create_entity", "params": {"name": "MyTestEntityFromSTDIO"}, "id": 1}' | uvx fastmcp run extensions.knowledge_graph_mcp.server:mcp_app --transport stdio
```

## Storage

The Markdown files for the knowledge graph are stored in a directory specified by the `KG_MCP_MARKDOWN_PATH` environment variable. If not set, it defaults to a local directory named `kg_markdown_data`.

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

## Dependencies

*   `fastmcp` (version used during development: >=2.0.0)
*   `pydantic` (version used during development: >=2.0.0)

These should be listed in a `pyproject.toml` if this server is maintained as a separate project.

## Examples

The `examples/` directory contains resources to help you get started:

* `system_prompt.md` - A sample system prompt for LLMs interacting with this knowledge graph system, designed for long-context models that can reload the knowledge graph as needed.
* `sample_kg_entry.md` - An example entity entry showing the expected markdown format.
* `mcp_server_guide.md` - Comprehensive guide for integrating this MCP server with various LLM agents and clients, including configuration examples for Claude Desktop, Goose, Continue, and others. Includes best practices for agent memory management.
