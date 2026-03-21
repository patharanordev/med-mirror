@echo off
echo 1. Checking for Docker...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not installed or not in PATH.
    pause
    exit /b
)

echo 2. Stopping old services...
docker compose -f docker-compose.eval.yml down -v --remove-orphans

echo 2.1 Cleaning up dangling images...
for /f "tokens=*" %%i in ('docker images -q -f "dangling=true"') do docker rmi -f %%i

@REM echo 2.2 Starting Ollama Service (Required for Import)...
@REM docker compose -f docker-compose.eval.yml up -d ollama
@REM echo Waiting for Ollama to initialize...
@REM timeout /t 10 /nobreak >nul

echo 3. Running Evaluation...
docker compose -f docker-compose.eval.yml up --build --abort-on-container-exit --exit-code-from eval-agent

echo.
echo Evaluation finished. All services stopped.
pause
