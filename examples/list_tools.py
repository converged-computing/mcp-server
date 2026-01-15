import asyncio
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp import Client
import sys
import os


port = 8089
if len(sys.argv) > 1:
    port = sys.argv[1]

token = os.environ.get('MCPSERVER_TOKEN')
url = f"http://localhost:{port}/mcp"
if token is not None:
    transport = StreamableHttpTransport(
        url=url, headers={"Authorization": token}
    )
    client = Client(transport)
else:
    client = Client(url)

async def list_tools():
    async with client:
        tools = await client.list_tools()
        for tool in tools:
            print(f"  ⭐ Discovered tool: {tool.name}")
        print()

try:
    asyncio.run(list_tools())
except RuntimeError:
    print("Please set the correct MCPSERVER_TOKEN")
