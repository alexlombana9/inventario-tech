@echo off
chcp 65001 > nul 2>&1
setlocal enabledelayedexpansion
cd /d "%~dp0"
title TechStock - Instalador Automatico

REM Generar caracter ESC para colores ANSI
for /f %%a in ('echo prompt $E ^| cmd') do set "ESC=%%a"

set "GREEN=%ESC%[32m"
set "RED=%ESC%[31m"
set "YELLOW=%ESC%[33m"
set "CYAN=%ESC%[36m"
set "BOLD=%ESC%[1m"
set "RESET=%ESC%[0m"

echo.
echo   %BOLD%=========================================================%RESET%
echo   %BOLD%       TechStock v2.0 - Instalador Automatico           %RESET%
echo   %BOLD%      Sistema de Inventario con PostgreSQL               %RESET%
echo   %BOLD%=========================================================%RESET%
echo.

REM =========================================================
REM  PASO 1: Verificar Python
REM =========================================================
echo %BOLD%[1/7] Verificando Python...%RESET%
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo   %RED%[ERROR]%RESET% Python no encontrado.
    echo.
    echo   Instale Python 3.10+ desde: https://python.org/downloads
    echo   IMPORTANTE: Marque la opcion "Add Python to PATH" durante la instalacion.
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo   %GREEN%[OK]%RESET% Python %PYVER% encontrado.

REM =========================================================
REM  PASO 2: Verificar / Instalar PostgreSQL
REM =========================================================
echo.
echo %BOLD%[2/7] Verificando PostgreSQL...%RESET%

set "PSQL_CMD="
set "PG_BIN="

REM Buscar psql en PATH
where psql > nul 2>&1
if %errorlevel% equ 0 (
    set "PSQL_CMD=psql"
    goto :pg_found
)

REM Buscar en rutas comunes de instalacion
for %%V in (17 16 15 14 13) do (
    if exist "C:\Program Files\PostgreSQL\%%V\bin\psql.exe" (
        set "PG_BIN=C:\Program Files\PostgreSQL\%%V\bin"
        set "PSQL_CMD=!PG_BIN!\psql.exe"
        goto :pg_found
    )
)

REM PostgreSQL no encontrado
echo   %YELLOW%[AVISO]%RESET% PostgreSQL no encontrado en el sistema.
echo.
echo   Se intentara instalar automaticamente con winget...
echo.

winget --version > nul 2>&1
if %errorlevel% equ 0 (
    echo   %CYAN%[INFO]%RESET% Instalando PostgreSQL 16 via winget...
    echo   Esto abrira el instalador de PostgreSQL.
    echo   %YELLOW%IMPORTANTE: Recuerde la contrasena que establezca para el usuario 'postgres'.%RESET%
    echo.
    choice /c SN /m "  Desea continuar con la instalacion automatica? (S/N)"
    if !errorlevel! equ 1 (
        winget install -e --id PostgreSQL.PostgreSQL.16
        if !errorlevel! equ 0 (
            echo   %GREEN%[OK]%RESET% PostgreSQL instalado.
            for %%V in (17 16 15 14) do (
                if exist "C:\Program Files\PostgreSQL\%%V\bin\psql.exe" (
                    set "PG_BIN=C:\Program Files\PostgreSQL\%%V\bin"
                    set "PSQL_CMD=!PG_BIN!\psql.exe"
                    goto :pg_found
                )
            )
        )
    )
)

echo.
echo   %RED%[ERROR]%RESET% No se pudo instalar PostgreSQL automaticamente.
echo.
echo   Instale PostgreSQL manualmente:
echo.
echo   1. Descargue desde: https://www.postgresql.org/download/windows/
echo   2. Ejecute el instalador (postgresql-16-windows-x64.exe)
echo   3. Recuerde la contrasena del usuario 'postgres'
echo   4. Deje el puerto por defecto (5432)
echo   5. Vuelva a ejecutar este script despues de instalar.
echo.
choice /c SN /m "  Desea abrir la pagina de descarga en el navegador? (S/N)"
if !errorlevel! equ 1 (
    start https://www.postgresql.org/download/windows/
)
echo.
pause
exit /b 1

:pg_found
REM Mostrar version de PostgreSQL
if defined PG_BIN (
    for /f "tokens=3" %%v in ('"!PSQL_CMD!" --version 2^>^&1') do set PGVER=%%v
    echo   %GREEN%[OK]%RESET% PostgreSQL !PGVER! encontrado en: !PG_BIN!
    set "PATH=!PG_BIN!;!PATH!"
) else (
    for /f "tokens=3" %%v in ('psql --version 2^>^&1') do set PGVER=%%v
    echo   %GREEN%[OK]%RESET% PostgreSQL !PGVER! encontrado en PATH.
)

REM =========================================================
REM  PASO 3: Configurar conexion a PostgreSQL
REM =========================================================
echo.
echo %BOLD%[3/7] Configurando conexion a PostgreSQL...%RESET%

set "PG_HOST=localhost"
set "PG_PORT=5432"
set "PG_USER=postgres"
set "PG_PASS=postgres"
set "PG_DBNAME=inventario"

REM Verificar si ya hay un .env con configuracion
if exist ".env" (
    echo   %CYAN%[INFO]%RESET% Archivo .env existente encontrado.
    for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
        if "%%a"=="DATABASE_URL" (
            echo   URL actual: %%b
        )
    )
    echo.
    choice /c SN /m "  Desea mantener la configuracion existente? (S/N)"
    if !errorlevel! equ 1 goto :skip_pg_config
)

echo.
echo   Ingrese los datos de conexion a PostgreSQL.
echo   Presione ENTER para usar el valor por defecto [entre corchetes].
echo.

set /p "PG_HOST=  Host [%PG_HOST%]: " || set "PG_HOST=localhost"
set /p "PG_PORT=  Puerto [%PG_PORT%]: " || set "PG_PORT=5432"
set /p "PG_USER=  Usuario [%PG_USER%]: " || set "PG_USER=postgres"
set /p "PG_PASS=  Contrasena [%PG_PASS%]: " || set "PG_PASS=postgres"
set /p "PG_DBNAME=  Base de datos [%PG_DBNAME%]: " || set "PG_DBNAME=inventario"

REM Escribir .env
echo DATABASE_URL=postgresql://!PG_USER!:!PG_PASS!@!PG_HOST!:!PG_PORT!/!PG_DBNAME!> .env
echo   %GREEN%[OK]%RESET% Archivo .env creado.

:skip_pg_config
REM Leer DATABASE_URL del .env
for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
    if "%%a"=="DATABASE_URL" set "DATABASE_URL=%%b"
)

REM =========================================================
REM  PASO 4: Crear base de datos PostgreSQL
REM =========================================================
echo.
echo %BOLD%[4/7] Creando base de datos PostgreSQL...%RESET%

REM Verificar conexion al servidor
set "PGPASSWORD=!PG_PASS!"
"!PSQL_CMD!" -h !PG_HOST! -p !PG_PORT! -U !PG_USER! -c "SELECT 1" > nul 2>&1
if %errorlevel% neq 0 (
    echo   %YELLOW%[AVISO]%RESET% No se pudo conectar a PostgreSQL.
    echo   Verifique que el servicio esta corriendo y que la contrasena es correcta.
    echo.
    echo   Para iniciar el servicio:
    echo     - Abra 'Servicios' de Windows (services.msc)
    echo     - Busque 'postgresql-x64-XX'
    echo     - Haga clic derecho y 'Iniciar'
    echo.
    choice /c SN /m "  Desea intentar iniciar el servicio automaticamente? (S/N)"
    if !errorlevel! equ 1 (
        net start postgresql-x64-16 2>nul || net start postgresql-x64-15 2>nul || net start postgresql-x64-14 2>nul
    )
    REM Reintentar
    "!PSQL_CMD!" -h !PG_HOST! -p !PG_PORT! -U !PG_USER! -c "SELECT 1" > nul 2>&1
    if !errorlevel! neq 0 (
        echo   %RED%[ERROR]%RESET% No se pudo conectar a PostgreSQL. Verifique la configuracion y vuelva a intentar.
        pause
        exit /b 1
    )
)
echo   %GREEN%[OK]%RESET% Conexion a PostgreSQL verificada.

REM Verificar si la base de datos ya existe
"!PSQL_CMD!" -h !PG_HOST! -p !PG_PORT! -U !PG_USER! -d !PG_DBNAME! -c "SELECT 1" > nul 2>&1
if %errorlevel% equ 0 (
    echo   %CYAN%[INFO]%RESET% La base de datos '!PG_DBNAME!' ya existe.
) else (
    echo   Creando base de datos '!PG_DBNAME!'...
    "!PSQL_CMD!" -h !PG_HOST! -p !PG_PORT! -U !PG_USER! -c "CREATE DATABASE !PG_DBNAME! ENCODING 'UTF8'" > nul 2>&1
    if !errorlevel! neq 0 (
        echo   %RED%[ERROR]%RESET% No se pudo crear la base de datos.
        pause
        exit /b 1
    )
    echo   %GREEN%[OK]%RESET% Base de datos '!PG_DBNAME!' creada.
)

REM =========================================================
REM  PASO 5: Crear entorno virtual Python
REM =========================================================
echo.
echo %BOLD%[5/7] Configurando entorno virtual Python...%RESET%

if exist "venv\Scripts\activate.bat" (
    echo   %CYAN%[INFO]%RESET% Entorno virtual ya existe.
) else (
    echo   Creando entorno virtual...
    python -m venv venv
    if !errorlevel! neq 0 (
        echo   %RED%[ERROR]%RESET% No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
    echo   %GREEN%[OK]%RESET% Entorno virtual creado.
)

REM =========================================================
REM  PASO 6: Instalar dependencias Python
REM =========================================================
echo.
echo %BOLD%[6/7] Instalando dependencias Python...%RESET%

call venv\Scripts\activate.bat
pip install --upgrade pip > nul 2>&1
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo   %RED%[ERROR]%RESET% Fallo la instalacion de dependencias.
    pause
    exit /b 1
)
echo   %GREEN%[OK]%RESET% Dependencias instaladas.

REM =========================================================
REM  PASO 7: Inicializar tablas y datos
REM =========================================================
echo.
echo %BOLD%[7/7] Inicializando base de datos (tablas + datos iniciales)...%RESET%

python _init_db.py
if %errorlevel% neq 0 (
    echo   %RED%[ERROR]%RESET% Error al inicializar la base de datos.
    echo   Verifique que PostgreSQL esta corriendo y que la URL es correcta.
    pause
    exit /b 1
)
echo   %GREEN%[OK]%RESET% Base de datos inicializada correctamente.

REM Crear directorios necesarios
if not exist "backups" mkdir backups
if not exist "static\uploads" mkdir static\uploads

REM =========================================================
REM  RESUMEN FINAL
REM =========================================================
echo.
echo   %GREEN%=========================================================%RESET%
echo   %GREEN%        Instalacion completada exitosamente!             %RESET%
echo   %GREEN%=========================================================%RESET%
echo.
echo   %BOLD%Para iniciar TechStock:%RESET%
echo     start.bat
echo.
echo   %BOLD%Para crear copias de seguridad:%RESET%
echo     backup.bat
echo.
echo   %BOLD%Datos de acceso:%RESET%
echo     URL:       http://localhost:8000
echo     Usuario:   admin
echo     Clave:     admin123
echo.
if defined DATABASE_URL (
    echo   %BOLD%Base de datos:%RESET%
    echo     !DATABASE_URL!
) else (
    echo   %BOLD%Base de datos:%RESET% configurada en .env
)
echo.
pause
endlocal
