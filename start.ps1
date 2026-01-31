# MedMirror Windows Launcher
# Use this script to run the application on Windows with NVIDIA GPU support.

Write-Host "Starting MedMirror for Windows (RTX 4080 Optimized)..." -ForegroundColor Cyan

# Check if Docker is running
if (-not (Get-Process "Docker Desktop" -ErrorAction SilentlyContinue)) {
    Write-Host "Warning: Docker Desktop might not be running. Please ensure it is started." -ForegroundColor Yellow
}

# Run Docker Compose with the Windows configuration
docker-compose -f docker-compose.win.yml up -d --build

if ($LASTEXITCODE -eq 0) {
    Write-Host "MedMirror started successfully!" -ForegroundColor Green
    Write-Host "Frontend: http://localhost:3000"
    Write-Host "Agent API: http://localhost:8001"
} else {
    Write-Host "Failed to start MedMirror. Please check the logs." -ForegroundColor Red
}
