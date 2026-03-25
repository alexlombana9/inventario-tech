@echo off
chcp 65001 > nul 2>&1
setlocal enabledelayedexpansion
cd /d "%~dp0"
title TechStock v2.0 - Desinstalador

REM ══════════════════════════════════════════════════════════
REM  Colores ANSI (Windows 10+)
REM ══════════════════════════════════════════════════════════
for /f %%a in ('echo prompt $E ^| cmd') do set "ESC=%%a"
set "G=%ESC%[92m"
set "R=%ESC%[91m"
set "Y=%ESC%[93m"
set "C=%ESC%[96m"
set "M=%ESC%[95m"
set "B=%ESC%[1m"
set "D=%ESC%[2m"
set "N=%ESC%[0m"

cls
echo.
echo  %M%╔═══════════════════════════════════════════════════════════╗%N%
echo  %M%║%N%                                                           %M%║%N%
echo  %M%║%N%   %B%%R%████████╗███████╗ ██████╗██╗  ██╗%N%                    %M%║%N%
echo  %M%║%N%   %B%%R%╚══██╔══╝██╔════╝██╔════╝██║  ██║%N%                    %M%║%N%
echo  %M%║%N%   %B%%R%   ██║   █████╗  ██║     ███████║%N%                    %M%║%N%
echo  %M%║%N%   %B%%R%   ██║   ██╔══╝  ██║     ██╔══██║%N%                    %M%║%N%
echo  %M%║%N%   %B%%R%   ██║   ███████╗╚██████╗██║  ██║%N%                    %M%║%N%
echo  %M%║%N%   %B%%R%   ╚═╝   ╚══════╝ ╚═════╝╚═╝  ╚═╝  %M%Stock v2.0%N%     %M%║%N%
echo  %M%║%N%                                                           %M%║%N%
echo  %M%║%N%   %D%Desinstalador — Sistema de Inventario%N%                  %M%║%N%
echo  %M%║%N%                                                           %M%║%N%
echo  %M%╚═══════════════════════════════════════════════════════════╝%N%
echo.
echo  %Y%ATENCION:%N% Este proceso eliminara la instalacion de TechStock.
echo  %D%El codigo fuente NO se elimina, solo los archivos generados.%N%
echo  %D%Puede volver a instalar ejecutando instalar.bat%N%
echo.
echo  %B%Se eliminara:%N%
echo    %C%1.%N% Entorno virtual      %D%(venv/)%N%
echo    %C%2.%N% Configuracion        %D%(.env, .secret_key)%N%
echo    %C%3.%N% Ejecutable           %D%(TechStock.exe)%N%
echo    %C%4.%N% Acceso directo       %D%(Escritorio)%N%
echo    %C%5.%N% Tarea programada     %D%(backup automatico)%N%
echo    %C%6.%N% Cache                %D%(__pycache__, .pytest_cache, etc.)%N%
echo.

set "RESP="
set /p "RESP=  Desea continuar con la desinstalacion? (S/N): "
if /i not "!RESP!"=="S" (
    echo.
    echo  %C%Desinstalacion cancelada.%N%
    pause
    exit /b 0
)

echo.

REM ══════════════════════════════════════════════════════════
REM  Preguntar sobre la base de datos
REM ══════════════════════════════════════════════════════════
set "DROP_DB=0"
echo  %Y%Desea ELIMINAR la base de datos PostgreSQL?%N%
echo  %D%  Si elige SI, se perderan TODOS los datos (productos, ventas, etc.)%N%
echo  %D%  Si elige NO, los datos se conservan para una futura reinstalacion.%N%
echo.
set "RESP="
set /p "RESP=  Eliminar base de datos? (S/N): "
if /i "!RESP!"=="S" set "DROP_DB=1"
echo.

REM ══════════════════════════════════════════════════════════
REM  Preguntar sobre los backups
REM ══════════════════════════════════════════════════════════
set "DROP_BACKUPS=0"
if exist "backups" (
    set "BK_COUNT=0"
    for %%F in (backups\*.sql) do set /a "BK_COUNT+=1"
    if !BK_COUNT! gtr 0 (
        echo  %Y%Se encontraron !BK_COUNT! copias de seguridad.%N%
        echo  %D%  Carpeta: backups/%N%
        echo.
        set "RESP="
        set /p "RESP=  Eliminar copias de seguridad? (S/N): "
        if /i "!RESP!"=="S" set "DROP_BACKUPS=1"
        echo.
    )
)

REM ══════════════════════════════════════════════════════════
REM  Leer credenciales de .env ANTES de eliminar nada
REM ══════════════════════════════════════════════════════════
set "PG_HOST=localhost"
set "PG_PORT=5432"
set "PG_USER=postgres"
set "PG_PASS=postgres"
set "PG_DBNAME=inventario"

if exist ".env" (
    for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
        if "%%a"=="DATABASE_URL" set "DATABASE_URL=%%b"
    )
    if defined DATABASE_URL (
        REM Parsear postgresql://user:pass@host:port/dbname sin Python
        set "TMPURL=!DATABASE_URL:postgresql://=!"
        for /f "tokens=1,2 delims=@" %%a in ("!TMPURL!") do (
            set "USERPASS=%%a"
            set "HOSTREST=%%b"
        )
        for /f "tokens=1,* delims=:" %%a in ("!USERPASS!") do (
            set "PG_USER=%%a"
            set "PG_PASS=%%b"
        )
        for /f "tokens=1,2 delims=/" %%a in ("!HOSTREST!") do (
            set "HOSTPORT=%%a"
            set "PG_DBNAME=%%b"
        )
        for /f "tokens=1,2 delims=:" %%a in ("!HOSTPORT!") do (
            set "PG_HOST=%%a"
            if not "%%b"=="" set "PG_PORT=%%b"
        )
    )
)

echo  %B%══════════════════════════════════════════════════════════%N%
echo  %B%Desinstalando TechStock...%N%
echo  %B%══════════════════════════════════════════════════════════%N%
echo.

REM ══════════════════════════════════════════════════════════
REM  1. Eliminar tarea programada de Windows
REM ══════════════════════════════════════════════════════════
echo  %C%[1/7]%N% Eliminando tarea programada...
schtasks /delete /tn "TechStock_Backup_Auto" /f > nul 2>&1
if %errorlevel% equ 0 (
    echo    %G%✓%N% Tarea programada eliminada.
) else (
    echo    %D%  No habia tarea programada.%N%
)

REM ══════════════════════════════════════════════════════════
REM  2. Eliminar acceso directo del Escritorio
REM ══════════════════════════════════════════════════════════
echo  %C%[2/7]%N% Eliminando acceso directo...
set "DESKTOP=%USERPROFILE%\Desktop"
if exist "%DESKTOP%\TechStock.lnk" (
    del "%DESKTOP%\TechStock.lnk" 2>nul
    echo    %G%✓%N% Acceso directo eliminado.
) else (
    echo    %D%  No habia acceso directo.%N%
)

REM ══════════════════════════════════════════════════════════
REM  3. Eliminar ejecutable y archivos de build
REM ══════════════════════════════════════════════════════════
echo  %C%[3/7]%N% Eliminando ejecutable y archivos de build...
if exist "TechStock.exe" del "TechStock.exe" 2>nul
if exist "TechStock.spec" del "TechStock.spec" 2>nul
if exist "backup_auto.bat" del "backup_auto.bat" 2>nul
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
echo    %G%✓%N% Archivos de build eliminados.

REM ══════════════════════════════════════════════════════════
REM  4. Eliminar entorno virtual
REM ══════════════════════════════════════════════════════════
echo  %C%[4/7]%N% Eliminando entorno virtual...
if exist "venv" (
    rmdir /s /q venv 2>nul
    if not exist "venv" (
        echo    %G%✓%N% Entorno virtual eliminado.
    ) else (
        echo    %Y%⚠%N% No se pudo eliminar completamente. Intente cerrar otros programas.
    )
) else (
    echo    %D%  No habia entorno virtual.%N%
)

REM ══════════════════════════════════════════════════════════
REM  5. Eliminar archivos de configuracion
REM ══════════════════════════════════════════════════════════
echo  %C%[5/7]%N% Eliminando archivos de configuracion...

if exist ".env" (
    del ".env" 2>nul
    echo    %G%✓%N% .env eliminado.
) else (
    echo    %D%  No habia .env%N%
)

if exist ".secret_key" (
    del ".secret_key" 2>nul
    echo    %G%✓%N% .secret_key eliminado.
)
if exist ".coverage" (
    del ".coverage" 2>nul
)

REM ══════════════════════════════════════════════════════════
REM  6. Eliminar cache y archivos temporales
REM ══════════════════════════════════════════════════════════
echo  %C%[6/7]%N% Eliminando cache y archivos temporales...
for /d /r %%d in (__pycache__) do (
    if exist "%%d" rmdir /s /q "%%d" 2>nul
)
rmdir /s /q .pytest_cache 2>nul
rmdir /s /q htmlcov 2>nul

if !DROP_BACKUPS! equ 1 (
    rmdir /s /q backups 2>nul
    echo    %G%✓%N% Copias de seguridad eliminadas.
) else (
    echo    %D%  Copias de seguridad conservadas en backups/%N%
)

echo    %G%✓%N% Cache limpiado.

REM ══════════════════════════════════════════════════════════
REM  7. Eliminar base de datos (opcional)
REM ══════════════════════════════════════════════════════════
echo  %C%[7/7]%N% Base de datos...
if !DROP_DB! equ 1 (
    REM Buscar psql
    set "PSQL_CMD="
    where psql > nul 2>&1
    if !errorlevel! equ 0 (
        set "PSQL_CMD=psql"
    ) else (
        for %%V in (17 16 15 14) do (
            if exist "C:\Program Files\PostgreSQL\%%V\bin\psql.exe" (
                set "PSQL_CMD=C:\Program Files\PostgreSQL\%%V\bin\psql.exe"
            )
        )
    )

    if defined PSQL_CMD (
        echo    %Y%⧖%N% Eliminando base de datos '!PG_DBNAME!'...
        set "PGPASSWORD=!PG_PASS!"

        REM Cerrar conexiones activas
        "!PSQL_CMD!" -h !PG_HOST! -p !PG_PORT! -U !PG_USER! -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='!PG_DBNAME!' AND pid <> pg_backend_pid();" > nul 2>&1

        REM Eliminar base de datos
        "!PSQL_CMD!" -h !PG_HOST! -p !PG_PORT! -U !PG_USER! -c "DROP DATABASE IF EXISTS !PG_DBNAME!;" > nul 2>&1
        if !errorlevel! equ 0 (
            echo    %G%✓%N% Base de datos '!PG_DBNAME!' eliminada.
        ) else (
            echo    %Y%⚠%N% No se pudo eliminar la base de datos.
            echo    %D%  Puede eliminarla manualmente con: DROP DATABASE !PG_DBNAME!;%N%
        )
    ) else (
        echo    %Y%⚠%N% psql no encontrado. No se pudo eliminar la base de datos.
        echo    %D%  Eliminela manualmente desde pgAdmin o psql.%N%
    )
) else (
    echo    %D%  Base de datos conservada ^(puede reutilizarse al reinstalar^).%N%
)

REM ══════════════════════════════════════════════════════════
REM  RESUMEN
REM ══════════════════════════════════════════════════════════
echo.
echo.
echo  %G%╔═══════════════════════════════════════════════════════════╗%N%
echo  %G%║%N%                                                           %G%║%N%
echo  %G%║%N%   %G%✓  DESINSTALACION COMPLETADA%N%                           %G%║%N%
echo  %G%║%N%                                                           %G%║%N%
echo  %G%╚═══════════════════════════════════════════════════════════╝%N%
echo.
echo  %B%Elementos eliminados:%N%
echo    %G%✓%N% Entorno virtual (venv)
echo    %G%✓%N% Configuracion (.env, .secret_key)
echo    %G%✓%N% Ejecutable (TechStock.exe)
echo    %G%✓%N% Acceso directo (Escritorio)
echo    %G%✓%N% Tarea programada (backup)
echo    %G%✓%N% Cache y archivos temporales
if !DROP_DB! equ 1 (
    echo    %G%✓%N% Base de datos PostgreSQL
) else (
    echo    %C%~%N% Base de datos conservada
)
if !DROP_BACKUPS! equ 1 (
    echo    %G%✓%N% Copias de seguridad
) else (
    echo    %C%~%N% Copias de seguridad conservadas
)
echo.
echo  %B%Elementos conservados:%N%
echo    %C%~%N% Codigo fuente del proyecto
echo    %C%~%N% Python (instalacion del sistema)
echo    %C%~%N% PostgreSQL (instalacion del sistema)
echo.
echo  %B%Para reinstalar:%N%
echo    Ejecute %C%instalar.bat%N%
echo.
pause
endlocal
exit /b 0
