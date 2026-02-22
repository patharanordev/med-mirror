@echo off
echo ========================================================
echo   MedMirror Edge - Model Downloader (Windows)
echo ========================================================
echo.
echo Running temporary downloader container...
echo (Check med-mirror/models folder to see progress)
echo.

echo Checking for existing segmentation model...
if exist "models\segmentation" (
    echo [SKIP] Segmentation model already exists in models\segmentation.
) else (
    docker run --rm -v "%cd%":/app -w /app -e HF_TOKEN python:3.11-slim sh -c "pip install huggingface_hub && python scripts/download_models.py --model segmentation"

    if errorlevel 1 (
        echo [ERROR] Model download failed.
        pause
        exit /b
    )
)

echo.
echo ========================================================
echo   Starting MedGemma Setup (Host)
echo ========================================================
echo.
echo Checking if model medgemma-1.5:4b already exists...
ollama list | findstr "medgemma-1.5:4b" >nul
if %errorlevel% equ 0 (
    echo [SKIP] Model medgemma-1.5:4b already exists.
) else (
    powershell -ExecutionPolicy Bypass -File scripts/import_medgemma_model.ps1
    if errorlevel 1 (
        echo [ERROR] MedGemma import failed.
        pause
        exit /b
    )
)

echo.
echo [SUCCESS] Models downloaded successfully!
echo You can now run start_windows.bat to launch the system.
echo.
