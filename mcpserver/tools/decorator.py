from typing import List


class McpProxy:
    """
    Looks like FastMCP. It just marks functions so we can find them later.
    We want to do this so we can dynamically define / add functions.
    We also might want to allow extended attributes to be added.
    """

    def tool(self, name: str = None, description: str = None, tags: List[str] = None):
        """
        MCP tool decorator as proxy to mcp.tool()
        """

        def decorator(func):
            default_name = (func.__module__.lower() + "-" + func.__name__.lower()).replace(".", "-")
            func._mcp_name = name or default_name
            func._mcp_desc = description
            func._mcp_tags = tags
            func._is_mcp_tool = True
            return func

        return decorator

    def prompt(self, name=None, description=None, meta=None, tags: List[str] = None):
        """
        MCP prompt decorator as proxy to mcp.prompt()
        """

        def decorator(func):
            func._mcp_description = description
            func._is_mcp_prompt = True
            func._mcp_name = name
            func._mcp_meta = meta
            func._mcp_tags = tags

            return func

        return decorator

    def resource(self, uri: str, tags: List[str] = None):
        """
        MCP resource decorator as proxy to mcp.resource()
        """

        def decorator(func):
            func._is_mcp_resource = True
            func._mcp_uri = uri
            func._mcp_tags = tags
            return func

        return decorator


mcp = McpProxy()
