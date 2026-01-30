# mcp-serve

> Agentic Server to support MCP Tools and Science

![https://github.com/converged-computing/mcpserver/blob/main/img/mcpserver.png?raw=true](https://github.com/converged-computing/mcpserver/blob/main/img/mcpserver.png?raw=true)

[![PyPI version](https://badge.fury.io/py/mcp-serve.svg)](https://badge.fury.io/py/mcp-serve)

## Design

This is a customizable, asynchronous server that can register and load tools of interest. Endpoints include functions (tools), prompts, resources. Those are now (for the most part) separated into modular projects:

- [flux-mcp](https://github.com/converged-computing/flux-mcp): MCP tools for Flux Framework
- [hpc-mcp](https://github.com/converged-computing/hpc-mcp): HPC tools for a larger set of HPC and converged computing use cases.

### Abstractions

The library here has the following abstractions.

- **tools**: server tools, prompts, and resources
- **ui**: user interface that an engine (with a main manager) uses
- **core**: shared assets, primarily the plan/step/config definitions
- **routes**: server views not related to mcp.
- **backends**: child of an engine, these are the model services (llama, openai, gemini)
- **databases**: how to save results as we progress in a pipeline (currently we support sqlite and filesystem JSON)

For the above, the engines, tools, ui, databases, and backends are interfaces.

### Tools

There are different means to add tools here:

 - **internal** are discovered in `mcpserver/tools` (assist the server).
 - **external modules**: externally discovered via the same mechanism.
 - **external one-off**: add a specific tool, prompt, or resource to a server (suggested)

I am suggesting a combined approach of the first and last bullet for security. E.g., when we deploy, we do not want to open a hole to add functions that are not known. In the context of a job, we likely have a specific need or use case and can select from a library. I am developing scoped tools with this aim or goal -- to be able to deploy a job and start a server within the context of the job with exactly what is needed. Here is how the module discovery works:

```python
from mcpserver.tools.manager import ToolManager

# Discover and register defaults
manager = ToolManager()

# The tools vendored here are automatically discovered..
manager.register("mcpserver.tools")

# Register a different module
manager.register("mymodule.tools")
```

## Development

It is recommended to open in VSCode container. Then install:

```bash
pip install --break-system-packages -e .
```

### Docker

To build the Docker container:

```bash
make
```

To run a dummy example:

```bash
docker run -p 8089:8089 -it ghcr.io/converged-computing/mcp-server:latest
```

And then interact from the outside:

```bash
python3 ./examples/echo/test_echo.py
```

### Environment

The following variables can be set in the environment.

| Name | Description | Default       |
|-------|------------|---------------|
| `MCPSERVER_PORT` | Port to run MCP server on, if using http variant | `8089` |
| `MCPSERVER_HOST` | Default host to run MCP server (http) | `0.0.0.0` |
| `MCPSERVER_PATH` | Default path for server endpoint | `/mcp` |
| `MCPSERVER_TOKEN` | Token to use for testing | unset |

## Examples

### Simple Echo

Start the server in one terminal. Export `MCPSERVER_TOKEN` if you want some client to use simple token auth.
Leave out the token for local test. Here is an example for http.

```bash
mcpserver start --transport http --port 8089
```

In another terminal, check the health endpoint or do a simple tool request.

```bash
# Health check
curl -s http://0.0.0.0:8089/health  | jq

# Tool to echo back message
python3 examples/echo/test_echo.py
```

### Docker Build

Here is an example to deploy a server to build a Docker container.
We first need to install the functions from [hpc-mcp](https://github.com/converged-computing/hpc-mcp):

```bash
pip install hpc-mcp --break-system-packages
```

Start the server with the functions and prompt we need:

```bash
# In one terminal (start MCP)
mcpserver start -t http --port 8089 \
  --prompt hpc_mcp.t.build.docker.docker_build_persona_prompt \
  --tool hpc_mcp.t.build.docker.docker_build_container

# Start with a configuration file instead
mcpserver start -t http --port 8089 --config ./examples/docker-build/mcpserver.yaml
```

And then use an agentic framework to run some plan to interact with tools. Here is how you would call them manually, assuming the second start method above with custom function names. Note for docker build you need the server running on a system with docker or podman.

```bash
# Generate a build prompt
python3 examples/docker-build/docker_build_prompt.py

# Build a docker container (requires mcp server to see docker)
python3 examples/docker-build/test_docker_build.py
```

### Listing

Agents discover tools with this endpoint. We can call it too!

```bash
python3 examples/list_tools.py
python3 examples/list_prompts.py
```

### JobSpec Translation

Here is a server that shows translation of a job specification with Flux.
To prototype with Flux, open the code in the devcontainer. Install the library and start a flux instance.

```bash
pip install -e .[all] --break-system-packages
pip install flux-mcp IPython --break-system-packages
flux start
```

We will need to start the server and add the validation functions and prompt.

```bash
mcpserver start -t http --port 8089 \
  --tool flux_mcp.validate.flux_validate_jobspec \
  --prompt flux_mcp.validate.flux_validate_jobspec_persona \
  --tool flux_mcp.transformer.transform_jobspec \
  --prompt flux_mcp.transformer.transform_jobspec_persona
```

And with the configuration file instead:

```bash
mcpserver start -t http --port 8089 --config ./examples/jobspec/mcpserver.yaml
```

We will provide examples for jobspec translation functions in [fractale-mcp](https://github.com/compspec/fractale-mcp).

### Kubernetes (kind)

This example is for basic manifests to work in Kind (or Kubernetes/Openshift). Note that we use the default base container with a custom function added via ConfigMap. You can take this approach, or build ON our base container and pip install your own functions for use.

- [examples/kind](examples/kind)

We will be making a Kubernetes Operator to create this set of stuff soon.

### SSL

Generate keys

```bash
mkdir -p ./certs
openssl req -x509 -newkey rsa:4096 -keyout ./certs/key.pem -out ./certs/cert.pem -sha256 -days 365 -nodes -subj '/CN=localhost'
```

And start the server, indicating you want to use them.

```bash
mcpserver start --transport http --port 8089 --ssl-keyfile ./certs/key.pem --ssl-certfile ./certs/cert.pem
```

For the client, the way that it works is that httpx discovers the certs via [environment variables](https://github.com/modelcontextprotocol/python-sdk/issues/870#issuecomment-3449911720). E.g., try the test first without them:

```bash
python3 examples/ssl/test_ssl_client.py
📡 Connecting to https://localhost:8089/mcp...
❌ Connection failed: Client failed to connect: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate (_ssl.c:1000)
```

Now export the envars:

```bash
export SSL_CERT_DIR=$(pwd)/certs
export SSL_CERT_FILE=$(pwd)/certs/cert.pem
```
```console
📡 Connecting to https://localhost:8089/mcp...
  ⭐ Discovered tool: simple_echo

✅ Connection successful!
```
And you'll see the server get hit.

### Design Choices

Here are a few design choices (subject to change, of course). I am starting with re-implementing our fractale agents with this framework. For that, instead of agents being tied to specific functions (as classes on their agent functions) we will have a flexible agent class that changes function based on a chosen prompt. It will use mcp functions, prompts, and resources. In addition:

- Tools hosted here are internal and needed for the library. E.g, we have a prompt that allows getting a final status for an output, in case a tool does not do a good job.
- For those hosted here, we don't use mcp.tool (and associated functions) directly, but instead add them to the mcp manually to allow for dynamic loading.
- Tools that are more general are provided under extral libraries (e.g., flux-mcp and hpc-mcp)
- We can use mcp.mount to extend a server to include others, or the equivalent for proxy (I have not tested this yet).
- Async is annoying but I'm using it. This means debugging is largely print statements and not interactive.
- The backend of FastMCP is essentially starlette, so we define (and add) other routes to the server.

## TODO

- Full operator with Flux example (Flux operator with HPC apps and jobspec translation)

## License

HPCIC DevTools is distributed under the terms of the MIT license.
All new contributions must be made under this license.

See [LICENSE](LICENSE),
[COPYRIGHT](COPYRIGHT), and
[NOTICE](NOTICE) for details.

SPDX-License-Identifier: (MIT)

LLNL-CODE- 842614
