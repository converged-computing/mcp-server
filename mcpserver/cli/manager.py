from mcpserver.core.config import MCPConfig
from mcpserver.tools.manager import ToolManager

# Initialize the global ToolManager instance
manager = ToolManager()


def get_manager(mcp, cfg: MCPConfig, register_id: str):
    """
    Initializes the ToolManager and registers all configured tools and system identity.

    Inputs:
        mcp (FastMCP): The MCP server instance.
        cfg (MCPConfig): The loaded server configuration.
        system_type (str): Optional legacy system type identifier.
    """

    # 1. Load the Federated Fleet Tools
    # This automatically boots the SystemTool and any discovery modules
    print(f"📡 Initializing System Identity...")
    manager.load_fleet_tools(mcp, include=cfg.discovery, worker_id=register_id)

    # 2. Handle explicit registration of specific paths (Tools, Prompts, Resources)
    for endpoint in register_explicit_capabilities(mcp, cfg):
        print(f"   ✅ Registered Explicit: {endpoint.name}")

    # 3. Handle SSL Visualization
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
    # Note: These methods must be present in your ToolManager implementation
    registries = [
        (cfg.tools, manager.register_tool),
        (cfg.prompts, manager.register_prompt),
        (cfg.resources, manager.register_resource),
    ]

    for capability_list, register_func in registries:
        for item in capability_list:
            # item is a CapabilityConfig object with .path and .name
            yield register_func(mcp, item.path, name=item.name)
