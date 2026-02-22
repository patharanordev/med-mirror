#!/bin/bash

echo "========================================================"
echo "  MedMirror Edge - Stop Services  "
echo "========================================================"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "[ERROR] Docker is not installed or not in PATH."
    exit 1
fi

echo "1. Stopping old services..."
docker-compose -f docker-compose.mac.yml down -v

echo "2. Cleaning up dangling images..."
docker rmi -f $(docker images -q --filter "dangling=true")