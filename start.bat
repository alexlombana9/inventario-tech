@echo off
chcp 65001 > nul 2>&1
cd /d "%~dp0"
title TechStock v2.0

REM Activar entorno virtual
if not exist "venv\Scripts\activate.bat" (
    echo [AVISO] Entorno virtual no encontrado.
    echo Ejecute setup.bat primero para configurar el sistema.
    pause
    exit /b 1
)
call venv\Scripts\activate.bat

REM Verificar conexion a PostgreSQL
python _check_db.py || goto :no_db

echo.
echo Iniciando TechStock...
echo Abra http://localhost:8000 en su navegador.
echo.
python main.py
goto :end

:no_db
echo Verifique que el servicio de PostgreSQL esta corriendo.
echo Intente iniciar PostgreSQL desde Servicios de Windows (services.msc)
pause
exit /b 1

:end
