@echo off
chcp 65001 > nul 2>&1
setlocal enabledelayedexpansion
cd /d "%~dp0"
title TechStock v2.0

REM Cargar variables de entorno desde .env
if exist ".env" (
    for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
        set "%%a=%%b"
    )
)

REM Activar entorno virtual
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo [AVISO] Entorno virtual no encontrado.
    echo Ejecute setup.bat primero para configurar el sistema.
    pause
    exit /b 1
)

REM Verificar conexion a PostgreSQL
python -c "from database import engine; conn = engine.connect(); conn.close(); print('[OK] Conexion a PostgreSQL verificada.')" 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] No se pudo conectar a PostgreSQL.
    echo Verifique que el servicio de PostgreSQL esta corriendo.
    echo Intente iniciar PostgreSQL desde Servicios de Windows (services.msc)
    pause
    exit /b 1
)

python main.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] El sistema no pudo iniciarse.
    echo Ejecute setup.bat si es la primera vez.
    echo.
    pause
)
endlocal
