# PowerShell script to import MedGemma model into Ollama
# Based on scripts/import_medgemma_model.sh

# ==============================================================================
# CONFIGURATION
# ==============================================================================
# The official Google MedGemma 4B Instruction Tuned model
$ModelRepo = "google/medgemma-1.5-4b-it"
$ModelName = "medgemma-1.5-4b"
$OllamaModelName = "medgemma-1.5:4b"

# Directories (using Environment Variable for HOME/USERPROFILE)
$WorkDir = Join-Path $env:USERPROFILE "medgemma_work"
$ModelDir = Join-Path $WorkDir "hf_model"
$LlamaCppDir = Join-Path $WorkDir "llama.cpp"
$VenvDir = Join-Path $WorkDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$VenvHfCli = Join-Path $VenvDir "Scripts\huggingface-cli.exe"

# Ollama stores models internally, usually in %USERPROFILE%\.ollama on Windows

# Quantization Level
$QuantMethod = "Q4_K_M"

# ==============================================================================
# 0. PRE-FLIGHT CHECKS & CLEANUP
# ==============================================================================
Write-Host ">>> Checking if model '$OllamaModelName' already exists in Ollama..."
try {
    $ollamaList = ollama list | Select-String -Pattern $OllamaModelName
    if ($ollamaList) {
        Write-Host "✅ Model '$OllamaModelName' already exists! Skipping installation." -ForegroundColor Green
        exit 0
    }
}
catch {
    Write-Host "⚠️  Could not run 'ollama list'. Is Ollama installed and running?" -ForegroundColor Yellow
    # Continue anyway
}

Write-Host ">>> Creating workspace at $WorkDir..."
if (-not (Test-Path $WorkDir)) { New-Item -ItemType Directory -Path $WorkDir -Force | Out-Null }
if (-not (Test-Path $ModelDir)) { New-Item -ItemType Directory -Path $ModelDir -Force | Out-Null }

# Check for uv
if (-not (Get-Command "uv" -ErrorAction SilentlyContinue)) {
    Write-Host ">>> 'uv' not found. Installing via pip..."
    pip install uv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to install uv. Please install it manually." -ForegroundColor Red
        exit 1
    }
}

# Create/Update Venv
Write-Host ">>> Setting up virtual environment with uv..."
uv venv "$VenvDir"
if ($LASTEXITCODE -ne 0) { exit 1 }

# Install Dependencies
Write-Host ">>> Installing dependencies into venv..."
# numpy<2 is critical for legacy llama.cpp conversion scripts
# HfFolder was removed in huggingface_hub v0.25.0, so we pin below that for compatibility with existing transformers/scripts
# Pinning transformers to a stable version as well
uv pip install -p "$VenvDir" "huggingface_hub[cli]<0.25.0" "numpy<2" "transformers<4.40" "sentencepiece" "gguf" "protobuf" "torch" "accelerate" "safetensors"
if ($LASTEXITCODE -ne 0) { exit 1 }


# ==============================================================================
# 1. AUTHENTICATION (REQUIRED FOR GATED MODELS)
# ==============================================================================
Write-Host "----------------------------------------------------------------"
Write-Host "⚠️  MedGemma is a RESTRICTED (Gated) model." -ForegroundColor Yellow
Write-Host "You must have accepted the license on Hugging Face."
Write-Host "----------------------------------------------------------------"

# Check if logged in
try {
    # If using 'huggingface_hub[cli]', the exe might be 'huggingface-cli.exe'
    if (-not (Test-Path $VenvHfCli)) {
        # Fallback check, sometimes it installs as 'hf.exe' or just strictly inside Scripts
        Write-Host "⚠️  Warning: $VenvHfCli not found. Checking for 'hf.exe'..."
        $VenvHfCli = Join-Path $VenvDir "Scripts\hf.exe"
        if (-not (Test-Path $VenvHfCli)) {
            Write-Host "❌ Error: Could not find huggingface-cli.exe or hf.exe in venv." -ForegroundColor Red
            exit 1
        }
    }

    & $VenvHfCli whoami 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Not logged in" }
}
catch {
    Write-Host ">>> Please login to Hugging Face with your Access Token (Read):"
    & $VenvHfCli login
}

# ==============================================================================
# 2. DOWNLOAD MODEL WEIGHTS
# ==============================================================================
Write-Host ">>> Downloading $ModelRepo..."

if (Test-Path (Join-Path $ModelDir "config.json")) {
    Write-Host "✅ Model files appear to exist in $ModelDir. Skipping download."
}
else {
    $downloadArgs = @(
        "download", "$ModelRepo",
        "--local-dir", "$ModelDir",
        "--local-dir-use-symlinks", "False",
        "--exclude", "*.git*", "README.md"
    )

    # Run the command
    & $VenvHfCli $downloadArgs

    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Download failed. Did you accept the terms on Hugging Face?" -ForegroundColor Red
        exit 1
    }
}

# ==============================================================================
# 3. GET LLAMA.CPP (SOURCE + BINARIES)
# ==============================================================================
if (-not (Test-Path $LlamaCppDir)) {
    Write-Host ">>> Cloning llama.cpp (for conversion scripts)..."
    git clone https://github.com/ggerganov/llama.cpp "$LlamaCppDir"
}

# Dependencies are already installed in top-level venv. Skipping pip install here.


# Download Pre-built Binaries for Windows
# Note: 'avx2' builds are often default but naming changes. 
# Looking for standard cpu build or cuda if user wants (sticking to cpu for safety)
$LlamaQuantizeExe = Join-Path "$LlamaCppDir" "llama-quantize.exe"

if (-not (Test-Path $LlamaQuantizeExe)) {
    Write-Host ">>> Downloading pre-built llama.cpp binaries for Windows..."
    
    # Get the latest release URL from GitHub API
    $LatestReleaseUrl = "https://api.github.com/repos/ggerganov/llama.cpp/releases/latest"
    try {
        $ReleaseInfo = Invoke-RestMethod -Uri $LatestReleaseUrl
        # Look for the asset ending with bin-win-cpu-x64.zip (AVX2 is usually implied in modern builds or separate)
        # Based on recent releases: llama-bXXXX-bin-win-cpu-x64.zip
        $Asset = $ReleaseInfo.assets | Where-Object { $_.name -like "*bin-win-cpu-x64.zip" } | Select-Object -First 1
        
        if ($Asset) {
            $DownloadUrl = $Asset.browser_download_url
            $ZipPath = Join-Path "$LlamaCppDir" "llama-bin.zip"
            
            Write-Host "Downloading $($Asset.name)..."
            Invoke-WebRequest -Uri $DownloadUrl -OutFile $ZipPath
            
            Write-Host "Extracting binaries..."
            Expand-Archive -Path $ZipPath -DestinationPath "$LlamaCppDir" -Force
            Remove-Item $ZipPath
        }
        else {
            Write-Error "Could not find a compatible binary asset in the latest release."
            exit 1
        }
    }
    catch {
        Write-Error "Failed to fetch latest release info from GitHub. $_"
        exit 1
    }
}

# Check again
if (-not (Test-Path $LlamaQuantizeExe)) {
    Write-Host "❌ Error: llama-quantize.exe not found after download attempt." -ForegroundColor Red
    exit 1
}

# ==============================================================================
# 4. CONVERT TO GGUF
# ==============================================================================
Write-Host ">>> Converting HF weights to GGUF (FP16)..."
$Fp16Output = Join-Path "$WorkDir" "${ModelName}-fp16.gguf"

if (-not (Test-Path $Fp16Output)) {
    # Check if convert script exists
    $ConvertScript = Join-Path "$LlamaCppDir" "convert_hf_to_gguf.py"
    if (-not (Test-Path $ConvertScript)) {
        Write-Host "❌ Error: $ConvertScript not found." -ForegroundColor Red
        exit 1
    }

    & $VenvPython "$ConvertScript" "$ModelDir" --outfile "$Fp16Output" --outtype f16
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Error: Conversion to GGUF failed." -ForegroundColor Red
        exit 1
    }
}
else {
    Write-Host ">>> FP16 GGUF already exists, skipping conversion."
}

# ==============================================================================
# 5. QUANTIZE MODEL
# ==============================================================================
$FinalModelPath = Join-Path "$WorkDir" "${ModelName}-${QuantMethod}.gguf"

if (-not (Test-Path $FinalModelPath)) {
    Write-Host ">>> Quantizing to $QuantMethod..."
    # The quantize tool needs to be called
    $QuantizeCmd = Join-Path "$LlamaCppDir" "llama-quantize.exe"
    & $QuantizeCmd "$Fp16Output" "$FinalModelPath" "$QuantMethod"
}
else {
    Write-Host ">>> Quantized model already exists."
}

# ==============================================================================
# 6. IMPORT TO OLLAMA
# ==============================================================================
Write-Host ">>> Creating Modelfile..."
$ModelfilePath = Join-Path "$WorkDir" "Modelfile"

$ModelfileContent = @"
FROM ${FinalModelPath}

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
"@

# Write Modelfile with UTF8 encoding (no BOM is safer for cross-platform tools, but usually PS default UTF16 is bad)
Set-Content -Path $ModelfilePath -Value $ModelfileContent -Encoding UTF8

Write-Host ">>> Importing to Ollama as '$OllamaModelName'..."
ollama create "$OllamaModelName" -f "$ModelfilePath"

# ==============================================================================
# 7. CLEANUP & TEST
# ==============================================================================
Write-Host ">>> Cleaning up heavy FP16 files (keeping the Q4 model)..."
if (Test-Path $Fp16Output) { Remove-Item $Fp16Output }

# Optional: Remove the raw HF download to save space
# Remove-Item -Recurse -Force $ModelDir

Write-Host "✅ SUCCESS! MedGemma is installed." -ForegroundColor Green
Write-Host "Run it with: ollama run $OllamaModelName"
