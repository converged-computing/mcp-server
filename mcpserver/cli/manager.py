from mcpserver.core.config import MCPConfig
from mcpserver.tools.manager import ToolManager

# Discover and register defaults
manager = ToolManager()
manager.register()


def get_manager(mcp, cfg):
    """
    Get the common tool manager and register tools.
    """
    # Add additional module paths (custom out of tree modules)
    for path in cfg.discovery:
        print(f"🧐 Registering additional module: {path}")
        manager.register(path)

    # explicit egistration
    for endpoint in register(mcp, cfg):
        print(f"   ✅ Registered: {endpoint.name}")

    # Load into the manager (tools, resources, prompts)
    for tool in manager.load_tools(mcp, cfg.include, cfg.exclude):
        print(f"   ✅ Registered: {tool.name}")

    # Visual to show user we have ssl
    if cfg.server.ssl_keyfile is not None and cfg.server.ssl_certfile is not None:
        print(f"   🔐 SSL Enabled")


def register(mcp, cfg: MCPConfig):
    """
    Registers specific tools, prompts, and resources defined in the config.
    Replaces the previous args-based register function.
    """
    # Define which config lists map to which manager methods
    registries = [
        (cfg.tools, manager.register_tool),
        (cfg.prompts, manager.register_prompt),
        (cfg.resources, manager.register_resource),
    ]

    for capability_list, register_func in registries:
        for item in capability_list:
            # item is a CapabilityConfig object with .path and .name
            yield register_func(mcp, item.path, name=item.name)
