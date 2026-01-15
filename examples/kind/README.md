# HPC MCP Server Example

> Run the mcpserver in Kubernetes (or OpenShift) with basic manifests

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [kind](https://kind.sigs.k8s.io/docs/user/quick-start/) (Kubernetes in Docker)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [Python 3.11+](https://www.python.org/downloads/) (for local testing)

## 1. Create a Kind Cluster

Start by creating a local Kubernetes cluster (with kind):

```bash
kind create cluster
```

## 2. Build and Load the Image

Build the container image locally and load it into the `kind` nodes so you don't have to push to a remote registry.
You can also pull and load.

```bash
# Build the image
docker build -t ghcr.io/converged-computing/mcp-server:latest .

# OR pull
docker pull ghcr.io/converged-computing/mcp-server:latest

# Load into kind
kind load docker-image ghcr.io/converged-computing/mcp-server:latest
```

## 3. Deploy the Server

The configuration and the custom tools are managed via a Kubernetes `ConfigMap`.
This contains our `mcpserver.yaml` (the configuration) and `echo.py` (the tool code).

```bash
kubectl apply -f config-map.yaml
```

This launches the pod, mounts the configuration, and exposes it via a Service.

```bash
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

Wait for the pod to reach the `Running` state:

```bash
kubectl get pods
```

See the server running:

```bash
kubectl logs mcp-server-5bbdcbbbdf-2sccc -f
```

Expose the service to your local machine:

```bash
kubectl port-forward svc/mcp-server-service 8080:80
```

Check health:

```bash
$ curl -s http://localhost:8080/health  | jq
{
  "status": 200,
  "message": "OK"
}
```

Ask for pancakes (you need fastmcp installed for this).

```bash
$ python3 get_pancakes.py 
  ⭐ Discovered tool: pancakes_tool
  ⭐ Discovered tool: simple_echo

CallToolResult(content=[TextContent(type='text', text='Pancakes for Vanessa 🥞', annotations=None, meta=None)], structured_content={'result': 'Pancakes for Vanessa 🥞'}, meta=None, data='Pancakes for Vanessa 🥞', is_error=False)
```

Note that we can also run the server in stdio mode and then echo json RPC to it, but nah, don't really want to do that. 

## Clean Up

To delete the cluster and start over:

```bash
kind delete cluster
```
