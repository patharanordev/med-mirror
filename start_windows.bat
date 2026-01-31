@echo off
echo ========================================================
echo   MedMirror Edge - First Time Setup (Windows)
echo ========================================================

echo 1. Checking for Docker...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not installed or not in PATH.
    pause
    exit /b
)

echo 2. Stopping old services...
docker-compose down

echo 2.1 Cleaning up dangling images...
for /f "tokens=*" %%i in ('docker images -q -f "dangling=true"') do docker rmi -f %%i

echo 2.5 Skipping Model Download...
echo     (If first time, run download_models.bat first)

echo 3. Building and Starting Services...
docker-compose up -d --build

echo 4. Waiting for Local LLM (Ollama) to start...
timeout /t 10 /nobreak >nul

echo 5. Pulling MedGemma/Gemma model to Ollama...
echo    (This may take a while depending on internet speed)
docker exec -it med_mirror_ollama ollama pull gemma:2b

echo ========================================================
echo   Setup Complete!
echo   - Frontend: http://localhost:3000
echo   - Segmentation: http://localhost:8000
echo   - Agent: http://localhost:8001
echo ========================================================
pause
