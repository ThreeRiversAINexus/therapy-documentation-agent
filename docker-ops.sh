#!/bin/bash

# Function to calculate hash of relevant files
calculate_hash() {
    local podmanfile=$1
    # Only hash files that have changed in the last hour to improve caching
    find . -type f \( -name "*.py" -o -name "requirements.txt" -o -name "$podmanfile" \) -mmin -60 -exec sha256sum {} \; 2>/dev/null | sort | sha256sum | cut -d' ' -f1
}

# Function to clean up old images
cleanup_images() {
    local prefix=$1
    local current_hash=$2
    
    echo "Cleaning up old images..."
    # Remove untagged/dangling images
    podman image prune -f
    # Keep only the 2 most recent tagged versions
    podman images "$prefix:*" --format "{{.ID}} {{.Tag}}" | 
        grep -v "$current_hash" | grep -v "latest" |
        sort -k2 -r | tail -n +2 | 
        awk '{print $1}' | xargs -r podman rmi
}

# Global variable for image tag
IMAGE_TAG=""

# Function to build or reuse image
build_image() {
    local prefix=$1
    local podmanfile=$2

    # Check if rebuild is explicitly requested
    if [ "${FORCE_REBUILD:-false}" = "true" ]; then
        echo "Force rebuild requested..."
        local hash=$(calculate_hash "$podmanfile")
        IMAGE_TAG="$prefix:${hash}"
        
        if ! podman build -q -t "$IMAGE_TAG" -f "$podmanfile" . > /dev/null; then
            echo "podman build failed"
            return 1
        fi
        podman tag "$IMAGE_TAG" "$prefix:latest"
        cleanup_images "$prefix" "$hash"
    else
        # Use latest tag if it exists, otherwise build new image
        if podman image inspect "$prefix:latest" >/dev/null 2>&1; then
            echo "Using existing latest image"
            IMAGE_TAG="$prefix:latest"
        else
            echo "No existing image found, building new one..."
            local hash=$(calculate_hash "$podmanfile")
            IMAGE_TAG="$prefix:${hash}"
            
            if ! podman build -q -t "$IMAGE_TAG" -f "$podmanfile" . > /dev/null; then
                echo "podman build failed"
                return 1
            fi
            podman tag "$IMAGE_TAG" "$prefix:latest"
        fi
    fi
    return 0
}

# Function to stop and remove containers
cleanup_containers() {
    local prefix=$1
    podman ps -a | grep "$prefix" | awk '{print $1}' | xargs -r podman stop
    podman ps -a | grep "$prefix" | awk '{print $1}' | xargs -r podman rm
}

# Parse command line arguments
MODE=$1
shift

case "$MODE" in
    "app")
        cleanup_containers "personal-metrics-agent"
        if ! build_image "personal-metrics-agent" "podmanfile"; then
            exit 1
        fi
        podman run -d -p 5000:5000 \
            -v "$(pwd)/data:/app/data" \
            -e OPENAI_API_KEY="$OPENAI_API_KEY" \
            "$IMAGE_TAG" "$@"
        ;;
    "test")
        cleanup_containers "personal-metrics-agent-test"
        if ! build_image "personal-metrics-agent-test" "podmanfile.test"; then
            exit 1
        fi
        podman run --rm \
            -v "$(pwd):/app" \
            -v "$(pwd)/data:/app/data" \
            -e OPENAI_API_KEY="$OPENAI_API_KEY" \
            -e INIT_DB="${INIT_DB:-false}" \
            "$IMAGE_TAG" "$@"
        ;;
    "cli")
        cleanup_containers "personal-metrics-agent-cli"
        if ! build_image "personal-metrics-agent-cli" "podmanfile.test"; then
            exit 1
        fi
        podman run --rm -it \
            -v "$(pwd):/app" \
            -v "$(pwd)/data:/app/data" \
            -e OPENAI_API_KEY="$OPENAI_API_KEY" \
            -e INIT_DB="${INIT_DB:-false}" \
            --entrypoint /app/cli-entrypoint.sh \
            "$IMAGE_TAG" "$@"
        ;;
    "dev")
        cleanup_containers "personal-metrics-agent"
        if ! build_image "personal-metrics-agent" "Podmanfile"; then
            exit 1
        fi
        podman run -d -p 5000:5000 \
            -v "$(pwd):/app" \
            -v "$(pwd)/data:/app/data" \
            -e FLASK_ENV=development \
            -e OPENAI_API_KEY="$OPENAI_API_KEY" \
            "$IMAGE_TAG" "$@"
        ;;
    *)
        echo "Usage: $0 <mode> [args...]"
        echo "Modes:"
        echo "  app   - Run the main application"
        echo "  test  - Run tests"
        echo "  cli   - Run CLI interface"
        echo "  dev   - Run in development mode with auto-reload"
        echo ""
        echo "Environment variables:"
        echo "  FORCE_REBUILD - Set to 'true' to force rebuild image (default: false)"
        exit 1
        ;;
esac
