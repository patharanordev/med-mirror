#!/bin/bash

echo "========================================================"
echo "  MedMirror Edge - Model Downloader (Mac/Linux)"
echo "========================================================"
echo ""
echo "Running temporary downloader container..."
echo "(Check med-mirror/models folder to see progress)"
echo ""

echo "Checking for existing segmentation model..."
if [ -d "models/segmentation" ]; then
    echo "[SKIP] Segmentation model already exists in models/segmentation."
else
    docker run --rm -v "$(pwd)":/app -w /app -e HF_TOKEN python:3.11-slim sh -c "pip install huggingface_hub && python scripts/download_models.py --model segmentation"

    if [ $? -ne 0 ]; then
        echo "[ERROR] Model download failed."
        exit 1
    fi
fi

echo ""
echo "========================================================"
echo "  Starting MedGemma Setup (Host)"
echo "========================================================"
echo ""
echo "Checking if model medgemma-1.5:4b already exists..."
if ollama list | grep -q "medgemma-1.5:4b"; then
    echo "[SKIP] Model medgemma-1.5:4b already exists."
else
    chmod +x scripts/import_medgemma_model.sh
    ./scripts/import_medgemma_model.sh
fi

echo ""
echo "[SUCCESS] Models downloaded successfully!"
echo "You can now run ./start_mac.sh to launch the system."
echo ""
