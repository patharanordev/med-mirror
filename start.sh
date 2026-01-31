#!/bin/bash

# MedMirror macOS Launcher
# Use this script to run the application on Mac (Apple Silicon).

echo "Starting MedMirror for macOS (Metal Optimized)..."

# Ensure script is executable
# chmod +x start.sh

# Run Docker Compose with the Mac configuration
docker-compose -f docker-compose.mac.yml up -d --build

if [ $? -eq 0 ]; then
    echo "✅ MedMirror started successfully!"
    echo "Frontend: http://localhost:3000"
    echo "Agent API: http://localhost:8001"
else
    echo "❌ Failed to start MedMirror. Please check errors above."
fi
