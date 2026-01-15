from mcpserver.tools.base import BaseTool
from mcpserver.tools.decorator import mcp


class EchoTool(BaseTool):
    """
    The EchoTool is primarily for testing.
    """

    def setup(self):
        pass

    @mcp.tool(name="simple_echo")
    def echo(self, message: str):
        """Echo the message back (return it)"""
        return message
