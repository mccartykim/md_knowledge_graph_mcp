import asyncio
import json
from fastmcp import Client
from server import EntityNameRequest, StandardResponse

async def create_entity():
    """Create an entity for 'Kimberly McCarty' using the MCP client."""
    # Create a client connection to the local stdio server
    client = Client("stdio://")
    await client.__aenter__()
    
    try:
        # Create the entity request payload
        entity_name = "Kimberly McCarty"
        payload = EntityNameRequest(name=entity_name)
        
        # Make the request
        raw_response = await client.call_tool("create_entity", {"request": payload.model_dump()})
        
        # Assuming we get a TextContent object with JSON in it (like in tests)
        if not raw_response or not isinstance(raw_response, list) or len(raw_response) == 0:
            print("Error: Invalid response format")
            return
        
        item = raw_response[0]
        
        # Handle TextContent objects (which have a text attribute containing JSON)
        if hasattr(item, 'text'):
            try:
                response_dict = json.loads(item.text)
                response = StandardResponse(**response_dict)
            except Exception as e:
                print(f"Error parsing response: {e}")
                return
        else:
            # Handle direct dict responses
            response = StandardResponse(**item)
        
        if response.success:
            print(f"Success: {response.message}")
        else:
            print(f"Failed: {response.message}")
    
    finally:
        await client.__aexit__(None, None, None)

if __name__ == "__main__":
    asyncio.run(create_entity())