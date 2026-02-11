import os
import argparse
from huggingface_hub import snapshot_download

# Define model mapping
MODELS = {
    "segmentation": {
        "repo_id": "mattmdjaga/segformer_b2_clothes",
        "local_dir": "models/segmentation"
    },
    # MedGemma is a gated model. You must accept terms on HF and provide a token.
    # We use "google/medgemma-1.5-4b-it"
    # MedGemma is now handled by a separate script (import_medgemma_model)
    # because it requires specific compilation/quantization steps on the host.
}

def download_model(model_key, token=None):
    if model_key not in MODELS:
        print(f"Unknown model: {model_key}")
        return

    config = MODELS[model_key]
    print(f"⬇️  Downloading {model_key} ({config['repo_id']}) to {config['local_dir']}...")
    
    # Check if directory exists and is not empty
    if os.path.exists(config['local_dir']) and any(os.scandir(config['local_dir'])):
        print(f"✅ {model_key} already exists in {config['local_dir']}. Skipping download.")
        return
    
    try:
        snapshot_download(
            repo_id=config["repo_id"],
            local_dir=config["local_dir"],
            local_dir_use_symlinks=False, # Important for Docker mounting
            token=token,
            ignore_patterns=["*.msgpack", "*.h5", "*.ot"] # Skip non-torch weights if preferred
        )
        print(f"✅ {model_key} downloaded successfully.")
    except Exception as e:
        print(f"❌ Failed to download {model_key}: {e}")
        if "401" in str(e):
            print("   (Hint: This might be a gated model. Provide a valid HF_TOKEN.)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download models for MedMirror")
    parser.add_argument("--model", type=str, default="all", help="Model to download: 'segmentation', 'medgemma', or 'all'")
    parser.add_argument("--token", type=str, help="Hugging Face User Access Token (for gated models)")
    
    args = parser.parse_args()
    
    # Ensure directories exist
    os.makedirs("models", exist_ok=True)
    
    token = args.token or os.environ.get("HF_TOKEN")

    if args.model == "all":
        for key in MODELS:
            download_model(key, token)
    else:
        download_model(args.model, token)
