import asyncio
import argparse
from fastmcp import Client
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

async def run_negotiation(url, prompt):
    console.print(f"🤝 [bold cyan]Initiating Negotiation with Fleet...[/bold cyan]")
    console.print(f"[dim]Request: {prompt}[/dim]\n")
    
    async with Client(url) as hub:
        result = await hub.call_tool("negotiate_job", {"prompt": prompt})
        data = result.structured_content

        table = Table(title="Cluster Proposal Comparison", border_style="green")
        table.add_column("Worker ID", style="magenta")
        table.add_column("Proposal / Reasoning", style="white")
        table.add_column("Verdict", justify="center")

        for wid, response in data.get("proposals", {}).items():
            cluster_result = response.get("data", {})
            proposal_text = cluster_result.get("proposal", "No response.")
            status = response.get("status", "UNKNOWN")            
            table.add_row(wid, proposal_text, f"[bold]{status}[/bold]")

        console.print(table)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000/mcp")
    parser.add_argument("prompt", help="The job description to negotiate")
    args = parser.parse_args()
    
    asyncio.run(run_negotiation(args.url, args.prompt))