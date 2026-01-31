@echo off
echo ========================================================
echo   MedMirror Edge - Model Downloader (Windows)
echo ========================================================
echo.
echo Running temporary downloader container...
echo (Check med-mirror/models folder to see progress)
echo.

docker run --rm -v "%cd%":/app -w /app -e HF_TOKEN python:3.11-slim sh -c "pip install huggingface_hub && python scripts/download_models.py --model segmentation"

if %errorlevel% neq 0 (
    echo [ERROR] Model download failed.
    pause
    exit /b
)

echo.
echo [SUCCESS] Models downloaded successfully!
echo You can now run start_windows.bat to launch the system.
echo.
pause
