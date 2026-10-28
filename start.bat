@echo off
echo ===================================================
echo        Starting OmniGeneDB Platform
echo ===================================================
echo.

:: Start Backend
echo [1/2] Starting FastAPI Backend on port 8002...
start "OmniGeneDB Backend" cmd /k "cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8002"

:: Start Frontend
echo [2/2] Starting React Frontend on port 3001...
start "OmniGeneDB Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo Both servers have been launched in separate windows!
echo Backend API: http://localhost:8002
echo Frontend UI: http://localhost:3001
echo.
pause
