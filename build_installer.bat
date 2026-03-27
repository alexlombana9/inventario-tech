@echo off
:: ============================================================
:: TechStock — Atajo para construir el instalador
:: Equivale a: python quickstart.py --build
:: ============================================================

title TechStock — Build Installer

:: Detectar Python (venv o sistema)
set PYTHON=python
if exist "venv\Scripts\python.exe" set PYTHON=venv\Scripts\python.exe

%PYTHON% quickstart.py --build
if errorlevel 1 (
    echo.
    echo [ERROR] El build fallo. Revise los errores arriba.
)

pause
