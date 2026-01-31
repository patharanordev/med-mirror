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
docker-compose -f docker-compose.mac.yml down

echo "2. Cleaning up dangling images..."
docker rmi -f $(docker images -q --filter "dangling=true")

echo "2.5 Skipping Model Download..."
echo "    (If first time, run ./download_models.sh first)"

echo "3. Building and Starting Services (for Apple Silicon)..."
docker-compose -f docker-compose.mac.yml up -d --build

echo "4. Waiting for Local LLM (Ollama) to start..."
sleep 10

echo "5. Pulling MedGemma/Gemma model to Ollama..."
docker exec -it med_mirror_ollama ollama pull gemma:2b

echo "========================================================"
echo "  Setup Complete!"
echo "  - Frontend: http://localhost:3000"
echo "  - Segmentation: http://localhost:8000"
echo "  - Agent: http://localhost:8001"
echo "========================================================"
