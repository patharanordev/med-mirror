#!/bin/bash

# ==============================================================================
# CONFIGURATION
# ==============================================================================
# The official Google MedGemma 4B Instruction Tuned model
# Note: Use "google/medgemma-1.5-4b-it" if you want the newer Jan 2026 version
MODEL_REPO="google/medgemma-1.5-4b-it"
MODEL_NAME="medgemma-1.5-4b"
OLLAMA_MODEL_NAME="medgemma-1.5:4b"

# Directories
WORK_DIR="$HOME/medgemma_work"
MODEL_DIR="$WORK_DIR/hf_model"
LLAMACPP_DIR="$WORK_DIR/llama.cpp"
OLLAMA_DIR="$HOME/.ollama"
VENV_DIR="$WORK_DIR/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"
VENV_HF_CLI="$VENV_DIR/bin/huggingface-cli"

# Quantization Level (Q4_K_M is the best balance of speed/accuracy for 4B)
QUANT_METHOD="Q4_K_M"

# ==============================================================================
# 0. PRE-FLIGHT CHECKS & CLEANUP
# ==============================================================================
echo ">>> Checking if model '$OLLAMA_MODEL_NAME' already exists in Ollama..."
if ollama list | grep -q "$OLLAMA_MODEL_NAME"; then
    echo "✅ Model '$OLLAMA_MODEL_NAME' already exists! Skipping installation."
    exit 0
fi

echo ">>> Creating workspace at $WORK_DIR..."
mkdir -p "$WORK_DIR"
mkdir -p "$MODEL_DIR"

# Check for uv
if ! command -v uv &> /dev/null; then
    echo ">>> 'uv' not found. Installing via pip..."
    pip install uv
fi

# Create Venv
echo ">>> Setting up virtual environment with uv..."
uv venv "$VENV_DIR"

# Install Dependencies
echo ">>> Installing dependencies into venv..."
uv pip install -p "$VENV_DIR" "huggingface_hub[cli]<0.25.0" "numpy<2" "transformers<4.40" "sentencepiece" "gguf" "protobuf" "torch" "accelerate" "safetensors"

# ==============================================================================
# 1. AUTHENTICATION (REQUIRED FOR GATED MODELS)
# ==============================================================================
echo "----------------------------------------------------------------"
echo "⚠️  MedGemma is a RESTRICTED (Gated) model."
echo "You must have accepted the license on Hugging Face."
echo "----------------------------------------------------------------"

# Check for CLI executable (huggingface-cli or hf)
if [ ! -f "$VENV_HF_CLI" ]; then
    VENV_HF_CLI="$VENV_DIR/bin/hf"
    if [ ! -f "$VENV_HF_CLI" ]; then
         echo "❌ Error: Could not find huggingface-cli or hf in venv."
         exit 1
    fi
fi

# Check if logged in, otherwise prompt
if ! "$VENV_HF_CLI" whoami &> /dev/null; then
    echo ">>> Please login to Hugging Face with your Access Token (Read):"
    "$VENV_HF_CLI" login
fi

# ==============================================================================
# 2. DOWNLOAD MODEL WEIGHTS
# ==============================================================================
echo ">>> Downloading $MODEL_REPO..."

if [ -f "$MODEL_DIR/config.json" ]; then
    echo "✅ Model files appear to exist in $MODEL_DIR. Skipping download."
else
    # We exclude safetensors if bin exists, or just download everything needed.
    # MedGemma usually has safetensors.
    "$VENV_HF_CLI" download "$MODEL_REPO" \
        --local-dir "$MODEL_DIR" \
        --local-dir-use-symlinks False \
        --exclude "*.git*" "README.md"

    if [ $? -ne 0 ]; then
        echo "❌ Download failed. Did you accept the terms on Hugging Face?"
        exit 1
    fi
fi

# ==============================================================================
# 3. BUILD LLAMA.CPP (CONVERSION TOOL)
# ==============================================================================
if [ ! -d "$LLAMACPP_DIR" ]; then
    echo ">>> Cloning llama.cpp..."
    git clone https://github.com/ggerganov/llama.cpp "$LLAMACPP_DIR"
fi

echo ">>> Building llama.cpp tools..."
cd "$LLAMACPP_DIR"
make clean
make -j$(nproc) llama-quantize llama-gguf
# Dependencies managed by top-level uv venv

# ==============================================================================
# 4. CONVERT TO GGUF
# ==============================================================================
echo ">>> Converting HF weights to GGUF (FP16)..."
# MedGemma is based on PaliGemma/Gemma architecture, which modern llama.cpp handles.
# We convert to FP16 first, then quantize.
FP16_OUTPUT="$WORK_DIR/${MODEL_NAME}-fp16.gguf"

if [ ! -f "$FP16_OUTPUT" ]; then
    "$VENV_PYTHON" convert_hf_to_gguf.py "$MODEL_DIR" \
        --outfile "$FP16_OUTPUT" \
        --outtype f16
    
    if [ $? -ne 0 ]; then
        echo "❌ Error: Conversion to GGUF failed."
        exit 1
    fi
else
    echo ">>> FP16 GGUF already exists, skipping conversion."
fi

# ==============================================================================
# 5. QUANTIZE MODEL
# ==============================================================================
FINAL_MODEL_PATH="$WORK_DIR/${MODEL_NAME}-${QUANT_METHOD}.gguf"

if [ ! -f "$FINAL_MODEL_PATH" ]; then
    echo ">>> Quantizing to $QUANT_METHOD..."
    ./llama-quantize "$FP16_OUTPUT" "$FINAL_MODEL_PATH" "$QUANT_METHOD"
else
    echo ">>> Quantized model already exists."
fi

# ==============================================================================
# 6. IMPORT TO OLLAMA
# ==============================================================================
echo ">>> Creating Modelfile..."
cat <<EOF > "$WORK_DIR/Modelfile"
FROM ${FINAL_MODEL_PATH}

# Standard Gemma Chat template
TEMPLATE """<start_of_turn>user
{{ .Prompt }}<end_of_turn>
<start_of_turn>model
{{ .Response }}<end_of_turn>
"""

# System Prompt for Medical Context
SYSTEM """You are MedGemma, a specialized medical AI assistant. 
Answer queries with clinical precision. 
If analyzing an image (skin, x-ray), provide objective observations first."""

PARAMETER temperature 0.2
PARAMETER num_ctx 8192
EOF

echo ">>> Importing to Ollama as '$OLLAMA_MODEL_NAME'..."
ollama create "$OLLAMA_MODEL_NAME" -f "$WORK_DIR/Modelfile"

# ==============================================================================
# 7. CLEANUP & TEST
# ==============================================================================
echo ">>> Cleaning up heavy FP16 files (keeping the Q4 model)..."
rm "$FP16_OUTPUT"
# Optional: Remove the raw HF download to save space
# rm -rf "$MODEL_DIR"

echo "✅ SUCCESS! MedGemma is installed."
echo "Run it with: ollama run $OLLAMA_MODEL_NAME"