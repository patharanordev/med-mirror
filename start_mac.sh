#!/bin/bash

echo "========================================================"
echo "  MedMirror Edge - First Time Setup (Mac M1/M2/M3)"
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

echo "2.2 Starting Ollama Service (Required for Import)..."
docker-compose -f docker-compose.mac.yml up -d ollama
echo "Waiting for Ollama to initialize..."
sleep 10

echo "2.5 Checking/Downloading Models..."
./download_models.sh

echo "3. Building and Starting Remaining Services..."
docker-compose -f docker-compose.mac.yml up -d --build

echo "4. Waiting for Local LLM (Ollama) to start..."
sleep 10

echo "5. Using local MedGemma model..."
echo "   (Ensure you ran ./download_models.sh to import medgemma-1.5:4b)"
# docker exec med_mirror_ollama ollama list

echo "========================================================"
echo "  Setup Complete!"
echo "  - Frontend: http://localhost:3000"
echo "  - Segmentation: http://localhost:8000"
echo "  - Agent: http://localhost:8001"
echo "========================================================"
