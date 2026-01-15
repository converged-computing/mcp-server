import asyncio
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp import Client
import sys
import os


port = 8080
if len(sys.argv) > 1:
    port = sys.argv[1]

client = Client(f"http://localhost:{port}/mcp")

async def call_tool(message: str):
    async with client:
        tools = await client.list_tools()
        for tool in tools:
            print(f"  ⭐ Discovered tool: {tool.name}")
        print()
        result = await client.call_tool("pancakes_tool", {"name": message})
        print(result)

try:
    asyncio.run(call_tool("Vanessa"))
except RuntimeError:
    print("Please set the correct FRACTALE_MCP_TOKEN")
