#!/bin/bash

echo "========================================================"
echo "  MedMirror Edge - Model Downloader (Mac/Linux)"
echo "========================================================"
echo ""
echo "Running temporary downloader container..."
echo "(Check med-mirror/models folder to see progress)"
echo ""

docker run --rm -v "$(pwd)":/app -w /app -e HF_TOKEN python:3.11-slim sh -c "pip install huggingface_hub && python scripts/download_models.py --model segmentation"

if [ $? -ne 0 ]; then
    echo "[ERROR] Model download failed."
    exit 1
fi

echo ""
echo "[SUCCESS] Models downloaded successfully!"
echo "You can now run ./start_mac.sh to launch the system."
echo ""
