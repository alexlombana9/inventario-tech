@echo off
chcp 65001 > nul
cd /d "%~dp0"

if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo [AVISO] Entorno virtual no encontrado. Usando Python global.
)

python main.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] El sistema no pudo iniciarse.
    echo Asegurate de haber ejecutado install.bat primero.
    echo.
    pause
)
