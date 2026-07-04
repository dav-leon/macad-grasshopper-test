@echo off
cd /d "%~dp0"

echo Starting MACAD GH-Quiz...
echo.

start "Quiz Backend" cmd /k "cd /d %~dp0backend && pip install -r requirements.txt -q && python app.py"
start "Quiz Frontend" cmd /k "cd /d %~dp0frontend && (if not exist node_modules npm install) && npm run dev"

echo Backend:  http://localhost:5002
echo Frontend: http://localhost:5173
echo.
echo Servers are starting in separate windows.
echo Opening browser in a few seconds...

timeout /t 3 /nobreak >nul
start http://localhost:5173
