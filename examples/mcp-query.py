import asyncio
import sys
import json
import argparse
from fastmcp import Client
from rich.console import Console
from rich.tree import Tree
from rich.json import JSON
from rich.panel import Panel
from rich.table import Table

console = Console()

DEFAULT_URL = "http://localhost:8000/mcp"
DEFAULT_TOOL = "get_fleet_status"

def render_fleet_tree(data: dict):
    """
    Renders the nested Hub/Worker hierarchy as a Tree.
    """
    tree = Tree("🌐 [bold cyan]mcpserver Hierarchy[/bold cyan]")
    
    if not data or not isinstance(data, dict):
        tree.add("[yellow]No worker data returned.[/yellow]")
        return tree

    for worker_id, info in data.items():
        # Status Icon
        online = info.get("online", False)
        icon = "✅" if online else "❌"
        color = "green" if online else "red"
        
        # Worker Node
        worker_node = tree.add(f"{icon} [bold {color}]{worker_id}[/bold {color}]")
        worker_node.add(f"[dim]Type:[/dim] [yellow]{info.get('type', 'generic')}[/yellow]")
        
        if online:
            # Recursively handle metadata or nested fleets
            status_data = info.get("status", {})
            meta_node = worker_node.add("📊 [bold white]Metadata[/bold white]")
            
            # Handle standard fields
            for k, v in status_data.items():
                if k == "fleet":
                    # This node is an intermediate Hub!
                    meta_node.add("🔗 [bold magenta]Sub-Fleet Attached (Intermediate Hub)[/bold magenta]")
                elif k == "labels" and isinstance(v, dict):
                    labels_node = worker_node.add("🏷️  [bold blue]Labels[/bold blue]")
                    for lk, lv in v.items():
                        labels_node.add(f"{lk}: [blue]{lv}[/blue]")
                elif isinstance(v, (dict, list)):
                    continue # Skip nested complex objects in the top-level tree for cleanliness
                else:
                    meta_node.add(f"{k}: [green]{v}[/green]")
        else:
            worker_node.add(f"[red]Error: {info.get('error', 'Unknown failure')}[/red]")

    return tree

async def query_mcp(url, tool_name):
    console.print(f"[bold blue]📡 Connecting to:[/bold blue] {url}")
    
    try:
        async with Client(url) as client:
            with console.status(f"[bold yellow]Calling {tool_name}...[/bold yellow]"):
                result = await client.call_tool(tool_name, {})
            
            # Extract data from FastMCP's result wrapper
            data = result
            if hasattr(result, "content"):
                text_content = result.content[0].text
                try:
                    # Try to parse text as JSON if it looks like it
                    data = json.loads(text_content.replace("'", '"'))
                except:
                    data = text_content

            # MAKE IT PRETTY.
            if tool_name == "get_fleet_status" and isinstance(data, dict):
                console.print("\n")
                console.print(Panel(render_fleet_tree(data), border_style="cyan", expand=False))
            
            elif isinstance(data, (dict, list)):
                console.print("\n")
                console.print(Panel(
                    JSON.from_data(data), 
                    title=f"[bold green]Result: {tool_name}[/bold green]", 
                    border_style="green",
                    expand=False
                ))
            else:
                console.print(f"\n[bold green]Result:[/bold green] {data}")

    except Exception as e:
        console.print(f"\n[bold red]❌ Request Failed:[/bold red] {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query an MCP server/hub and print results prettily.")
    parser.add_argument("url", nargs="?", default=DEFAULT_URL, help=f"Server URL (default: {DEFAULT_URL})")
    parser.add_argument("tool", nargs="?", default=DEFAULT_TOOL, help=f"Tool to call (default: {DEFAULT_TOOL})")
    
    args = parser.parse_args()
    
    asyncio.run(query_mcp(args.url, args.tool))