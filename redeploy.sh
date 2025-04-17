#!/bin/bash

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Determine which compose command to use
if command_exists docker-compose; then
    COMPOSE_CMD="docker-compose"
elif command_exists docker && docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
else
    echo "Error: Neither docker-compose nor docker compose command found"
    exit 1
fi

# Ensure data directory exists and has proper permissions
echo "Setting up data directory..."
mkdir -p data
chmod 777 data

# Export current user's UID and GID for container
export UID=$(id -u)
export GID=$(id -g)

# Stop and remove existing container if it exists
echo "Stopping and removing existing container..."
$COMPOSE_CMD down || true

# Build and start the new container
echo "Building and starting new container..."
$COMPOSE_CMD up --build -d

# Show logs
echo "Showing logs (press Ctrl+C to exit)..."
$COMPOSE_CMD logs -f 