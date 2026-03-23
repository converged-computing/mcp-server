import asyncio
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
    Renders the Level 1 Hub/Worker hierarchy as a Tree.
    """
    tree = Tree("🌐 [bold cyan]mcpserver Fleet[/bold cyan]")
    
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
            status_data = info.get("status", {})
            meta_node = worker_node.add("📊 [bold white]Status Snapshot[/bold white]")
            
            # Extract key metrics for the tree view
            if isinstance(status_data, dict):
                # Check for hardware summary
                if "hardware" in status_data:
                    hw = status_data["hardware"]
                    cpu = hw.get("cpu", {}).get("cores", "??")
                    mem = hw.get("memory", {}).get("total_gb", "??")
                    net = hw.get("network", {}).get("interconnect", "ethernet")
                    meta_node.add(f"Cores: [green]{cpu}[/green] | RAM: [green]{mem}GB[/green] | Net: [blue]{net}[/blue]")
                
                # Check for scheduler summary
                if "scheduler" in status_data:
                    sch = status_data["scheduler"]
                    free = sch.get("cores", {}).get("free", "??")
                    pend = sch.get("queue", {}).get("pending", 0)
                    meta_node.add(f"Free Cores: [bold green]{free}[/bold green] | Pending: [bold yellow]{pend}[/bold yellow]")

                # Labels
                labels = info.get("labels", {})
                if labels:
                    labels_node = worker_node.add("🏷️  [bold blue]Labels[/bold blue]")
                    for lk, lv in labels.items():
                        labels_node.add(f"{lk}: [blue]{lv}[/blue]")
        else:
            worker_node.add(f"[red]Error: {info.get('error', 'Unknown failure')}[/red]")

    return tree

def render_negotiation_results(data: dict):
    """
    Renders the Level 2 'negotiate_job' output as a side-by-side comparison table.
    """
    negotiation_id = data.get("negotiation_id", "Unknown")
    table = Table(title=f"🤝 Job Negotiation: {negotiation_id}", border_style="cyan", show_header=True, header_style="bold magenta")
    
    table.add_column("Cluster ID", style="bold magenta", width=15)
    table.add_column("Type", style="yellow", width=12)
    table.add_column("Descriptive Proposal / Reasoning", style="white")
    table.add_column("Verdict", style="bold", width=15, justify="center")

    proposals = data.get("proposals", {})
    if not proposals:
        return Panel("[red]No proposals were received from the fleet.[/red]")

    for wid, prop in proposals.items():
        p_type = prop.get("type", "unknown")
        
        if p_type == "agentic_proposal":
            p_data = prop.get("data", {})
            # Extract reasoning and decision from the secretary agent's response
            reasoning = p_data.get("reasoning", p_data.get("proposal_text", "No detailed reasoning provided."))
            verdict = str(p_data.get("status", p_data.get("decision", "Unknown"))).upper()
            
            # Color coding based on common response patterns
            color = "green" if any(x in verdict.lower() for x in ["ready", "yes", "feasible", "success"]) else "yellow"
            if "error" in verdict.lower() or "no" == verdict.lower():
                color = "red"
                
            table.add_row(wid, "🤖 Secretary", reasoning, f"[{color}]{verdict}[/{color}]")
        
        elif p_type == "manifest_only":
            reason = prop.get("reasoning", "Static manifest fallback.")
            table.add_row(wid, "📜 Manifest", reason, "[dim]EVALUATING[/dim]")
            
        else:
            msg = prop.get("message", "Connection or Tool error")
            table.add_row(wid, "❌ Error", f"[red]{msg}[/red]", "[bold red]OFFLINE[/bold red]")

    return table

async def query_mcp(url, tool_name, prompt=None):
    """
    Main query loop connecting to the FastMCP client.
    """
    console.print(f"[bold blue]📡 Connecting to Hub:[/bold blue] {url}")
    
    try:
        async with Client(url) as client:
            # Prepare arguments for the tool call
            # 'negotiate_job' expects 'prompt'
            call_args = {}
            if tool_name == "negotiate_job" and prompt:
                call_args = {"prompt": prompt}
            
            with console.status(f"[bold yellow]Calling {tool_name}...[/bold yellow]"):
                result = await client.call_tool(tool_name, call_args)
            
            # Extract data from FastMCP content block
            data = result
            if hasattr(result, "content") and len(result.content) > 0:
                text_content = result.content[0].text
                try:
                    # Clean potential single quotes and parse JSON
                    data = json.loads(text_content.replace("'", '"'))
                except:
                    data = text_content

            # Visual Routing based on tool called
            if tool_name == "get_fleet_status" and isinstance(data, dict):
                console.print("\n")
                console.print(Panel(render_fleet_tree(data), border_style="cyan", expand=False))
            
            elif tool_name == "negotiate_job" and isinstance(data, dict):
                console.print("\n")
                console.print(render_negotiation_results(data))
                # Print raw JSON in a collapsed panel for debugging/verification
                console.print(Panel(JSON.from_data(data), title="Raw Negotiation Data", border_style="dim", expand=False))

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
    parser = argparse.ArgumentParser(description="Query an MCP hub and render descriptive expressions.")
    parser.add_argument("url", nargs="?", default=DEFAULT_URL, help=f"Server URL (default: {DEFAULT_URL})")
    parser.add_argument("tool", nargs="?", default=DEFAULT_TOOL, help=f"Tool to call (default: {DEFAULT_TOOL})")
    parser.add_argument("--prompt", help="The natural language job request for negotiate_job")
    
    args = parser.parse_args()
    
    # Interactive prompt for negotiation if not provided via CLI
    if args.tool == "negotiate_job" and not args.prompt:
        args.prompt = console.input("[bold yellow]Enter your job request (e.g., 'Run LAMMPS on 32 nodes'): [/bold yellow]")
    
    asyncio.run(query_mcp(args.url, args.tool, args.prompt))