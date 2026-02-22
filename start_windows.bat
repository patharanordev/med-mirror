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
docker compose -f docker-compose.win.yml down -v

echo 2.1 Cleaning up dangling images...
for /f "tokens=*" %%i in ('docker images -q -f "dangling=true"') do docker rmi -f %%i

echo 2.2 Starting Ollama Service (Required for Import)...
docker compose -f docker-compose.win.yml up -d ollama
echo Waiting for Ollama to initialize...
timeout /t 10 /nobreak >nul

echo 2.5 Checking/Downloading Models...
call download_models.bat

echo 3. Building and Starting Remaining Services...
docker compose -f docker-compose.win.yml up -d --build

echo 4. Waiting for Local LLM (Ollama) to start...
timeout /t 10 /nobreak >nul

echo 5. Using local MedGemma model...
echo    (Ensure you ran download_models.bat to import medgemma-1.5:4b)
rem docker exec -it med_mirror_ollama ollama list

echo ========================================================
echo   Setup Complete!
echo   - Frontend: http://localhost:3000
echo   - Segmentation: http://localhost:8000
echo   - Agent: http://localhost:8001
echo ========================================================
pause
