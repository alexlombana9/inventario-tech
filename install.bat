@echo off
chcp 65001 > nul
echo.
echo ================================================
echo   TechStock - Instalacion de dependencias
echo ================================================
echo.

python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no encontrado. Instala Python desde https://python.org
    pause
    exit /b 1
)

echo [1/3] Creando entorno virtual...
python -m venv venv
if %errorlevel% neq 0 (
    echo [ERROR] No se pudo crear el entorno virtual
    pause
    exit /b 1
)

echo [2/3] Activando entorno virtual...
call venv\Scripts\activate.bat

echo [3/3] Instalando dependencias...
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo [ERROR] Fallo la instalacion de dependencias
    pause
    exit /b 1
)

echo.
echo ================================================
echo   Instalacion completada correctamente!
echo   Ejecuta start.bat para iniciar el sistema.
echo ================================================
echo.
pause
