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
- **core**: shared assets, primarily the plan/step/config definitions and worker/hub hierarchy roles
- **routes**: server views not related to mcp.
- **databases**: how to save results as we progress in a pipeline (currently we support sqlite and filesystem JSON)

For the above, the engines, tools, ui, databases, and backends are interfaces.

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


## Usage

### Start the Server

Start the server in one terminal. Export `MCPSERVER_TOKEN` if you want some client to use simple token auth.
Leave out the token for local test. Here is an example for http.

```bash
mcpserver start --transport http --port 8089
```

## Endpoints

In addition to standard MCP endpoints that deliver JSON RPC according to [the specification](https://modelcontextprotocol.io/specification/2025-03-26/basic), we provide a set of more easily accessible http endpoints for easy access to server health or metadata.

### Health Check

```bash
# Health check
curl -s http://0.0.0.0:8089/health  | jq
```

### Listing

You can list tools, prompts, and resources.

```bash
curl -s http://0.0.0.0:8089/tools/list  | jq
curl -s http://0.0.0.0:8089/prompts/list  | jq
curl -s http://0.0.0.0:8089/resources/list  | jq
```

We do this internally in the server via discovery by the manager, and then returning a simple JSON response of those found.

## Examples

All of these can be run from a separate terminal when the server is running.

### Simple Echo

Do a simple tool request.

```bash
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

We will provide examples for jobspec translation functions in [fractale](https://github.com/compspec/fractale-mcp) and the agent in [fractale-agents](https://github.com/converged-computing/fractale-agents).

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


## Full Architecture

### Starting a Hub

You'll need to install support for the associated worker and resource discovery:

```bash
pip install mcp-serve[hub]
pip install mcp-serve[all]
```

The mcp-server can register worker hubs, which are other MCP servers that register to it. To start the mcpserver as a hub:

```bash
# Start a hub in one terminal
mcpserver start --hub --hub-secret potato

# Start in dual mode (not recommended for production, primarily for experiments)
mcpserver start --dual --hub-secret potato
```

In another terminal, start a worker using the token that is generated. Add some functions for fun.

```bash
# If it wants to write batch jobs.
pip install hpc-mcp --break-system-packages
mcpserver start --config examples/jobspec/mcpserver.yaml --join http://0.0.0.0:8000 --join-secret potato --port 7777
```

Note that you can also set the secret in the environemnt.

```bash
export MCPSERVER_JOIN_SECRET=potato
mcpserver start --config examples/jobspec/mcpserver.yaml --join http://0.0.0.0:8000 --port 7777
```

You can also start a mock worker. By default, we choose 40/40/20 for archetypes for hpc, cloud, and standalone. You can
also specify an archetype.

```bash
mcpserver start --config examples/jobspec/mcpserver.yaml --join http://0.0.0.0:8000 --port 7777 --mock
mcpserver start --config examples/jobspec/mcpserver.yaml --join http://0.0.0.0:8000 --port 7777 --archetype hpc
```

### Mocking a Hub

If you are doing experiments, you can bring up a hub the same way:

```bash
# Start as a standalone hub (recommended)
mcpserver start --hub --hub-secret potato

# Start in dual mode (not recommended for production or performance experiments
mcpserver start --dual --hub-secret potato
```

To mock (simulate) a worker, add `--mock`, optionally with a particular archetype (one of `hpc`, `cloud`, or `standalone`). A worker ID is suggested to make the seed reproducible.

```bash
mcpserver start --join http://0.0.0.0:8000 --port 7777 --worker-id 10 --mock --join-secret potato
mcpserver start --join http://0.0.0.0:8000 --port 7777 --worker-id 10 --mock hpc --join-secret potato
```

In another terminal, you can request to export the simulation "truth" - the metadata generated for the providers chosen for the archetype.

```bash
mcpserver start --config examples/jobspec/mcpserver.yaml --join http://0.0.0.0:8000 --port 7777 --worker-id 10
```

And export "truth" metadata.

```bash
resource-ask export --output ground-truth.json
```

#### Manual Queries

Test doing raw queries for status. These are manual and local queries.

```bash
# Get listing of workers and metadata
python3 ./examples/mcp-query.py

# Get a specific tool metadata from the worker
python3 ./examples/mcp-query.py http://localhost:7777/mcp get_status

# Call a namespaced tool on the hub (e.g., get the status)
python3 ./examples/mcp-query.py http://localhost:8000/mcp n_781e903e4f10_get_status
```

You can test it without the join secret, or a wrong join secret, to see it fail.

### Resource Secretary Client

This is the client general interface:

```bash
# Includes request, asking secretaries, selection, and dispatch
resource-ask negotiate "I need <resources, constraints>"

# Includes request and asking secretaries
resource-ask satisfy "I need <resources, constraints>"

# Includes request, asking secretaries, and selection
resource-ask select "I need <resources, constraints>"

# The same, but from a proposals file (json dict with data.proposal for each)
resource-ask select --proposals proposals.json "I need <resources, constraints>"

# Dispatch directly to a named cluster
resource-ask dispatch <cluster> "I need <resources>"
```

The `resource-ask` client, which can support using a local model to run selection and other algorithms. You can also "roll your own" stuff using the server endpoints, but this library provides interfaces for doing and extending that already.

```bash
pip install resource-secretary
```


#### Negotiating a Job

When a user has a request, it goes to the hub as a prompt. We use a prompt instead of a set of hard coded policies, because it can technically say anything. E.g.,

> I have a paper due in 3 hours and I need to run LAMMPS. Find me at least 3 nodes and minimize time to completion. My budget is X.

If you are using gemini or openai, make sure to install the libraries.

```bash
pip install -e .[gemini] --break-system-packages
pip install -e .[openai] --break-system-packages
```

For the example, I like to find spack to be discoverable. We can install to spack to see how the responses change.

```bash
git clone --depth 1 https://github.com/spack/spack /tmp/spack
export SPACK_ROOT=/tmp/spack
flux start
```

And start the worker after that. Since we are running in a VSCode environment, let's asked a smaller scoped task.

```bash
# Satisfy request
resource-ask satisfy "Can you run cowsay on one node?"

# List selection algorihtms
resource-ask list select

# Negotiat (sastisfy, select, and dispatch) with a selection algorithm
resource-ask negotiate "I need to run LAMMPS with 1 node." --select agentic
```

You'll notice that the interface suggests using "select" next. The above "negotiate" is akin to a satisfy request. We do the following:

```console
[resource-ask] (client)  --> [negotiate_job] (hub) --> [secretary_ask] (workers) --> return to hub --> [client]
```

A select would take this a step further, and select.

The above is working, and the response comes back! Next I need to work on the selection algorithm and delegation.
Likely to start I'll randomly select (that will be an interface that is valid to choose) and then allow me to implement delegation. The remainder of notes are from before.

For this to work we:

1. Make a call to the mcp server hub to `negotiate_work`
 - Negotiate work is going to prompt the secretary to send back a response with:
   - a quick yes/no response that can eliminate contenders
   - policy specific metrics (e.g., estimated time to start, estimated cost, performance)
   - Importantly, the hub will evaluate the importance of a set of factors for the job. E.g., "this job requires good network, completed in X time, under N cost, storage does not matter." It will come up with factors and weights (importance) and an equation for the factors and not tell the secretaries its relative weights. The hub wil prepare a prompt that describes the needs, not only the importance, but provide reference for the secretary agents. E.g., "Evaluate your network where 1.0 is 100Gbps InfiniBand and 0.0 is 1Gbps Ethernet." The secretaries will then evaluate the quality of their resources toward the goal, and send back scores and reasons/justification to evaluate each variable. We can test binary (0/1), requesting specific ranges, and normalized scores (0 to 1). The hub then just needs to evaluate the returned values against its equation. This needs to be a two step process, first quantiative, and then adjustment based on qualitative. E.g., maybe a specific filesystem is given 0.5, but the secretary also notes it is undergoing a rebuild, so the hub decides to penalize it.
2. The hub sends the request to the children workers (each a different cluster)
3. Each child worker has a secretary that receives it.
 - The secretary has metadata about the cluster that is discovered on startup that does not change (e.g., hardware)
 - The secretary also is able to register handles to detailed discovery tools (e.g., software, you'd do for example, `spack find lammps`)
 - The secretary makes a call to request state data like queue status
 - The secretary also uses the discovery tools to look for the software of choice.
4. Each secretary sends back their response - quantitative scores, plus qualitative reasons.
5. Each secretary has a trust score. It is based on two things:
 - The actual discovery of resources is a known truth that is always returned. What the secretary says is compared against that.
 - An actual performance of a job can be evaluated against what was promised.
 - A trust score can (somehow) go into a future evaluation.

### Design Choices

Here are a few design choices (subject to change, of course). I am starting with re-implementing our fractale agents with this framework. For that, instead of agents being tied to specific functions (as classes on their agent functions) we will have a flexible agent class that changes function based on a chosen prompt. It will use mcp functions, prompts, and resources. In addition:

- Tools hosted here are internal and needed for the library. E.g, we have a prompt that allows getting a final status for an output, in case a tool does not do a good job.
- For those hosted here, we don't use mcp.tool (and associated functions) directly, but instead add them to the mcp manually to allow for dynamic loading.
- Tools that are more general are provided under extral libraries (e.g., flux-mcp and hpc-mcp)
- We can use mcp.mount to extend a server to include others, or the equivalent for proxy (I have not tested this yet).
- Async is annoying but I'm using it. This means debugging is largely print statements and not interactive.
- The backend of FastMCP is essentially starlette, so we define (and add) other routes to the server.

## TODO

- [ ] should we be reporting utilization (e.g., mock or nvidia smi) if it might just be a login node?
- [ ] write function to compare reported agent result from truth? How?
- [ ] need way to "pass forward" an error from a worker that, for example, API key not set.
- [ ] I want to have the equivalent of a satisfy endpoint, checking for the negotiate but not dispatch.
- [ ] I also want an equivalent "just submit to this cluster" endpoint.

Idea:

- the mcp-server worker should have a tool that generates a prompt for an agent. "Here is a request for lammps, this many nodes, and here are the resources we see (call to get_status, which also will be returned to the caller). Can we support it? Use your tools to figure it out. then the created agent should use the tools in the same server it is generated in to answer that question. The response from the agent plus the status should return to the hub. The hub can have the weighted equation to decide on a final cluster.
- TODO: ask agent which flux variables we should eliminate.

## License

HPCIC DevTools is distributed under the terms of the MIT license.
All new contributions must be made under this license.

See [LICENSE](LICENSE),
[COPYRIGHT](COPYRIGHT), and
[NOTICE](NOTICE) for details.

SPDX-License-Identifier: (MIT)

LLNL-CODE- 842614
