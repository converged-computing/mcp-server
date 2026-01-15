import mcpserver.tools.status.prompts as prompts
from mcpserver.tools.base import BaseTool
from mcpserver.tools.decorator import mcp


class StatusTool(BaseTool):

    @mcp.prompt(
        name="check_finished_prompt", description="Look at step outputs and determined if finished"
    )
    def check_finished_prompt(self, content: str) -> dict:
        """
        Generates agent instructions for determining if a step is completed, successful, failed.
        """
        prompt_text = prompts.get_status_text(content)
        return {"messages": [{"role": "user", "content": {"type": "text", "text": prompt_text}}]}
