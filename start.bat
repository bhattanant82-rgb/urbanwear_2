@echo off
title UrbanWear Launcher
color 0A
echo ==========================================
echo       URBANWEAR - Starting Project
echo ==========================================
IF NOT EXIST "backend\venv\" (
    echo [1/3] Creating virtual environment...
    cd backend && python -m venv venv && cd ..
)
echo [2/3] Installing dependencies...
cd backend && call venv\Scripts\activate && pip install -r requirements.txt -q && cd ..
echo [3/3] Starting servers...
echo.
echo Backend  --> http://127.0.0.1:5000
echo Frontend --> http://localhost:8080
echo.
start "UrbanWear Backend" cmd /k "cd backend && venv\Scripts\activate && uvicorn main:app --reload --port 5000"
timeout /t 3 /nobreak > nul
start "UrbanWear Frontend" cmd /k "cd frontend && python -m http.server 8080"
timeout /t 2 /nobreak > nul
start http://localhost:8080
echo Both started! Browser khul jayega.
pause
