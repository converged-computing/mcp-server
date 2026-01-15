import asyncio
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp import Client
from rich import print
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

async def call_tool(application: str):
    async with client:
        tools = await client.list_prompts()
        for tool in tools:
            print(f"  ⭐ Discovered prompt: {tool.name}")
        print()
        result = await client.get_prompt("build_expert", {"application": application})
        print(result.messages[0])

try:
    asyncio.run(call_tool("LAMMPS"))
except RuntimeError:
    print("Please set the correct MCPSERVER_TOKEN")
