FROM python:3.12-slim

# Install system-level dependencies for HPC introspection
RUN apt-get update && apt-get install -y --no-install-recommends \
    hwloc \
    libhwloc-dev \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/code

WORKDIR /code
COPY . /code
RUN pip install --no-cache-dir .
EXPOSE 8089
ENTRYPOINT ["mcpserver", "start"]

# Default command if no arguments are provided.
# We bind to 0.0.0.0 so the server is reachable outside the container.
CMD ["-t", "http", "--host", "0.0.0.0", "--port", "8089"]
