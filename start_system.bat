@echo off
TITLE Horizon Bank System - Startup Script
echo =======================================================
echo          STARTING HORIZON BANK SYSTEM SERVICES
echo =======================================================
echo.

:: Automatically determine the directory where this script is located
SET "BASE_DIR=%~dp0"
echo System root detected at: %BASE_DIR%
echo.

:: 1. Start Backend API
echo [1/3] Starting Backend API on Port 8002...
start "Backend API" cmd /c "cd /d ""%BASE_DIR%bank-app\backend"" && echo Starting Backend... && call .venv\Scripts\activate && python main.py || pause"

:: 2. Start KYC Microservice
echo [2/3] Starting KYC Microservice on Port 8001...
start "KYC Microservice" cmd /c "cd /d ""%BASE_DIR%kycsyst"" && echo Starting KYC Service... && call .venv\Scripts\activate && python api.py || pause"

:: 3. Start Frontend
echo [3/3] Starting Frontend Development Server...
start "Frontend UI" cmd /c "cd /d ""%BASE_DIR%bank-app\frontend"" && echo Starting Frontend... && npm run dev || pause"

echo.
echo =======================================================
echo All services have been launched in separate windows!
echo Keep those windows open while using the system.
echo Frontend should be available at: http://localhost:5174
echo =======================================================
pause
