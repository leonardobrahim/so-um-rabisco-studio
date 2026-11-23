@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ==================================================
echo   So um Rabisco Studio - Iniciando Servidores
echo ==================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERRO] Ambiente virtual .venv nao encontrado na raiz do repositorio.
    pause
    exit /b 1
)

if not exist "frontend\node_modules" (
    echo [INFO] Instalando dependencias do frontend na primeira execucao...
    pushd frontend
    call npm install
    popd
)

echo [1/2] Subindo Backend FastAPI (http://localhost:8000)...
start "So um Rabisco - Backend (FastAPI)" cmd /k "cd /d "%~dp0" && .venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000"

echo [2/2] Subindo Frontend Vite (http://localhost:5173)...
start "So um Rabisco - Frontend (Vite)" cmd /k "cd /d "%~dp0frontend" && npm run dev -- --port 5173"

timeout /t 3 /nobreak >nul
start "" "http://localhost:5173"

echo.
echo Tudo iniciado!
echo - Frontend: http://localhost:5173
echo - Backend API: http://localhost:8000/docs
echo.
