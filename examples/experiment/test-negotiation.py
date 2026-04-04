import argparse
import asyncio
import json
import time
from pathlib import Path

from fastmcp import Client
from resource_secretary.simulation import GlobalCatalog, PromptGenerator, SimulationAuditor
from rich import print
from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()


class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return super().default(obj)


async def get_workers_truth(url):
    async with Client(url) as hub:
        return await hub.call_tool("export_fleet_truth", {})


async def run_simulation(url, num_prompts, output_path):
    """
    Main Orchestrator for the Resource Secretary Reliability Experiment.
    """
    console.print(f"\n🚀 [bold cyan]Starting Resource Secretary Simulation[/bold cyan]")
    console.print(f"📡 Target Hub: [blue]{url}[/blue]")
    console.print(f"📊 Prompt Count: {num_prompts}\n")

    async with Client(url) as hub:

        # Fleet ground truth
        with console.status("[bold green]Exporting Ground Truth from fleet..."):
            truth_resp = await hub.call_tool("export_fleet_truth", {})

            # Handle FastMCP vs standard MCP return types
            fleet_truth = getattr(truth_resp, "structured_content", None)
            if not fleet_truth:
                fleet_truth = json.loads(truth_resp.content[0].text)

            # The actual truth is nested in 'ground_truth' key from our HubManager
            workers_truth = fleet_truth.get("ground_truth", {})

        if not workers_truth:
            console.print("[bold red]Error:[/bold red] No workers found or fleet truth is empty.")
            return

        console.print(f"✅ Discovered [magenta]{len(workers_truth)}[/magenta] workers.")

        # Initialize Simulation Logic
        catalog = GlobalCatalog(workers_truth)
        generator = PromptGenerator(catalog)
        auditor = SimulationAuditor()

        # Generate Test Suite
        test_suite = [generator.generate_requirement() for _ in range(num_prompts)]
        console.print(
            f"✅ Generated {num_prompts} unique prompts across {len(catalog.software)} applications.\n"
        )

        results = []
        to_save = []
        stats = {"correct": 0, "total": 0}

        # Execution Loop
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            transient=True,
        ) as progress:
            task = progress.add_task("Evaluating Agents...", total=num_prompts)

            for req in test_suite:
                prompt_text = req["prompt"]
                print(prompt_text)

                # Broadcast the prompt to every worker in the fleet
                # The Hub handles rate-limiting via its internal semaphore
                negotiation_resp = await hub.call_tool("negotiate_job", {"prompt": prompt_text})
                neg_data = getattr(negotiation_resp, "structured_content", None)
                if not neg_data:
                    neg_data = json.loads(negotiation_resp.content[0].text)
                proposals = neg_data.get("proposals", {})

                # Audit every worker's response to this prompt
                for wid, agent_response in proposals.items():

                    # Get the ground truth for THIS specific worker
                    truth = workers_truth.get(wid)
                    if not truth:
                        print(f"Warning: missing ground truth for {wid} (should not happen)")
                        continue

                    audit = auditor.evaluate(
                        worker_truth=workers_truth[wid]["truth"],
                        requirement=req,
                        agent_resp=agent_response,
                        tool_registry=workers_truth[wid]["registry"],
                    )

                    record = {
                        "prompt": prompt_text,
                        "worker_id": wid,
                        "specificity_index": req["specificity_index"],
                        "requirement_logic": req["logic"],
                        "ground_truth": truth,
                        "audit": audit,
                    }
                    results.append(record)

                    stats["total"] += 1
                    if audit["verdict"]["is_correct"]:
                        stats["correct"] += 1

                progress.advance(task)

        # 5. Summary Report
        accuracy = (stats["correct"] / stats["total"]) * 100 if stats["total"] > 0 else 0

        console.print(f"\n🏁 [bold green]Simulation Complete[/bold green]")
        console.print(f"Total Evaluations: [bold]{stats['total']}[/bold]")
        console.print(f"Global Accuracy: [bold cyan]{accuracy:.2f}%[/bold cyan]")

        # 6. Dimensional Analysis (Difficulty Check)
        table = Table(title="Accuracy by Specificity Index", border_style="dim")
        table.add_column("SI (Complexity)", justify="center")
        table.add_column("Count", justify="right")
        table.add_column("Accuracy", justify="right")

        for si in range(1, 8):
            si_results = [r for r in results if r["specificity_index"] == si]
            if not si_results:
                continue

            si_correct = len([r for r in si_results if r["audit"]["verdict"]["is_correct"]])
            si_acc = (si_correct / len(si_results)) * 100
            table.add_row(str(si), str(len(si_results)), f"{si_acc:.1f}%")

        console.print(table)
        final_results = {"summary": stats, "timestamp": time.time(), "interactions": results}
        with open(output_path, "w") as f:
            json.dump(final_results, f, indent=2, cls=SetEncoder)

        console.print(f"\n💾 Forensic data saved to [blue]{output_path}[/blue]")
        return final_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000/mcp", help="Hub MCP URL")
    parser.add_argument("--count", type=int, default=1, help="Number of prompts to generate")
    parser.add_argument("--output", default="forensic_results.json", help="Path to save results")

    args = parser.parse_args()
    results = asyncio.run(run_simulation(args.url, args.count, Path(args.output)))
