from .flux import SystemTool as FluxSystemTool
from .generic import SystemTool as GenericSystemTool
from .kubernetes import SystemTool as KubernetesSystemTool

system_tools = {
    "flux": FluxSystemTool,
    "generic": GenericSystemTool,
    "kubernetes": KubernetesSystemTool,
}
