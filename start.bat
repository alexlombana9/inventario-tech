@echo off
chcp 65001 > nul 2>&1
setlocal enabledelayedexpansion
cd /d "%~dp0"
title TechStock v2.0

REM ── Colores ANSI ──
for /f %%a in ('echo prompt $E ^| cmd') do set "ESC=%%a"
set "G=%ESC%[92m"
set "R=%ESC%[91m"
set "Y=%ESC%[93m"
set "C=%ESC%[96m"
set "B=%ESC%[1m"
set "D=%ESC%[2m"
set "N=%ESC%[0m"

REM ── Verificar entorno virtual ──
if not exist "venv\Scripts\activate.bat" (
    echo  %R%[ERROR]%N% Entorno virtual no encontrado.
    echo  Ejecute %C%instalar.bat%N% primero para configurar el sistema.
    pause
    exit /b 1
)
call venv\Scripts\activate.bat

REM ── Verificar dependencias y auto-instalar si faltan ──
venv\Scripts\python.exe -c "import fastapi; import sqlalchemy; import uvicorn" >nul 2>&1
if !errorlevel! neq 0 (
    echo  %Y%[AVISO]%N% Dependencias faltantes detectadas. Instalando...
    echo.
    venv\Scripts\python.exe -m pip install -r requirements.txt --no-cache-dir -q 2>nul
    if !errorlevel! neq 0 (
        echo  %Y%⚠%N% Instalacion rapida fallo. Intentando paquete por paquete...
        for /f "usebackq tokens=1 delims=>= " %%p in ("requirements.txt") do (
            set "PKG=%%p"
            if not "!PKG!"=="" if not "!PKG:~0,1!"=="#" (
                venv\Scripts\python.exe -m pip install "%%p" --no-cache-dir -q 2>nul
            )
        )
    )
    echo  %G%✓%N% Dependencias verificadas.
    echo.
)

REM ── Verificar conexion a PostgreSQL ──
venv\Scripts\python.exe -c "from database import engine; c=engine.connect(); c.close()" >nul 2>&1
if !errorlevel! neq 0 (
    echo  %R%[ERROR]%N% No se pudo conectar a PostgreSQL.
    echo  Verifique que el servicio de PostgreSQL esta corriendo.
    echo  %D%Servicios de Windows ^(services.msc^) ^> postgresql-x64-16 ^> Iniciar%N%
    pause
    exit /b 1
)
echo  %G%✓%N% Conexion a PostgreSQL verificada.

echo.
echo  Iniciando TechStock...
echo  Abra %C%http://localhost:8000%N% en su navegador.
echo.
venv\Scripts\python.exe main.py
endlocal
