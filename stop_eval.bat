@echo off
echo 1. Checking for Docker...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not installed or not in PATH.
    pause
    exit /b
)

echo 2. Stopping old services...
docker compose -f docker-compose.eval.yml down -v

echo 2.1 Cleaning up dangling images...
for /f "tokens=*" %%i in ('docker images -q -f "dangling=true"') do docker rmi -f %%i
