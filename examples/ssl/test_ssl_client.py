import asyncio
import sys
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

port = 8089
if len(sys.argv) > 1:
    port = sys.argv[1]

# Use https for SSL stuff
url = f"https://localhost:{port}/mcp"

# Create the transport with the verification
transport = StreamableHttpTransport(url=url)
client = Client(transport)

async def list_tools():
    """
    Connects to the Flux MCP server via SSL and lists discovered tools.
    WITH SSL! Oohlala.
    """
    print(f"📡 Connecting to {url}...")
    async with client:
        tools = await client.list_tools()
        if not tools:
            print("  ⚠️ No tools discovered.")
        for tool in tools:
            print(f"  ⭐ Discovered tool: {tool.name}")
        print("\n✅ Connection successful!")

if __name__ == "__main__":
    try:
        asyncio.run(list_tools())
    except Exception as e:
        print(f"❌ Connection failed: {e}")