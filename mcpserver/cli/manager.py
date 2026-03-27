from mcpserver.core.config import MCPConfig
from mcpserver.tools.manager import ToolManager

# Initialize the global ToolManager instance
manager = ToolManager()


def get_manager(mcp, cfg: MCPConfig):
    """
    Initializes the ToolManager and registers all configured tools and system identity.

    Inputs:
        mcp (FastMCP): The MCP server instance.
        cfg (MCPConfig): The loaded server configuration.
        system_type (str): Optional legacy system type identifier.
    """

    # Load fleet tools
    # This automatically boots the SystemTool and any discovery modules
    print(f"📡 Initializing System Identity...")
    manager.load_fleet_tools(mcp, include=cfg.discovery)

    # Handle explicit registration of specific paths (Tools, Prompts, Resources)
    for endpoint, emoji in register_explicit_capabilities(mcp, cfg):
        print(f"   {emoji} Registered: {endpoint.name}")

    # Handle SSL
    if cfg.server.ssl_keyfile is not None and cfg.server.ssl_certfile is not None:
        print(f"   🔐 SSL Enabled")

    return manager


def register_explicit_capabilities(mcp, cfg: MCPConfig):
    """
    Registers specific tools, prompts, and resources defined explicitly in the config.

    Inputs:
        mcp (FastMCP): The MCP server instance.
        cfg (MCPConfig): The loaded configuration object.
    """
    # Map configuration lists to the manager's registration methods
    registries = [
        (cfg.tools, manager.register_tool, "✅"),
        (cfg.prompts, manager.register_prompt, "💬"),
        (cfg.resources, manager.register_resource, "⛰️"),
        (cfg.events, manager.register_event, "📡"),
    ]

    for capability_list, register_func, emoji in registries:
        for item in capability_list:
            # item is a CapabilityConfig object with .path and .name
            yield register_func(mcp, item.path, name=item.name), emoji
