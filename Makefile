IMAGE_NAME ?= ghcr.io/converged-computing/mcp-server
IMAGE_TAG ?= latest
FULL_IMAGE_NAME = $(IMAGE_NAME):$(IMAGE_TAG)
FULL_ARM_IMAGE = $(IMAGE_NAME):arm
DOCKERFILE_PATH = Dockerfile
BUILD_CONTEXT = .

# Default target: builds the Docker image
all: build

# Build the Docker image
build:
	@echo "Building Docker image $(FULL_IMAGE_NAME)..."
	docker build \
		-f $(DOCKERFILE_PATH) \
		-t $(FULL_IMAGE_NAME) \
		.
	@echo "Docker image $(FULL_IMAGE_NAME) built successfully."

# Push the docker image
push:
	@echo "Pushing image $(FULL_IMAGE_NAME)..."
	docker push $(IMAGE_NAME) --all-tags

# Remove the image (clean with rmi)
clean:
	@echo "Removing Docker image $(FULL_IMAGE_NAME)..."
	docker rmi $(FULL_IMAGE_NAME) || true
	@echo "Docker image $(FULL_IMAGE_NAME) removed (if it existed)."

arm:
	@echo "Building arm Docker image $(FULL_IMAGE_NAME)..."
	docker buildx build \
		--platform linux/amd64,linux/arm64 \
		-f $(DOCKERFILE_PATH) \
		-t $(FULL_ARM_IMAGE) \
		--load .
	@echo "Docker image $(FULL_ARM_IMAGE) built successfully."

.PHONY: all build push clean arm
