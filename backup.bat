@echo off
chcp 65001 > nul 2>&1
setlocal enabledelayedexpansion
cd /d "%~dp0"
title TechStock - Copias de Seguridad

REM Generar caracter ESC para colores ANSI
for /f %%a in ('echo prompt $E ^| cmd') do set "ESC=%%a"

set "GREEN=%ESC%[32m"
set "RED=%ESC%[31m"
set "YELLOW=%ESC%[33m"
set "CYAN=%ESC%[36m"
set "BOLD=%ESC%[1m"
set "RESET=%ESC%[0m"

set "BACKUP_DIR=%~dp0backups"
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

REM Cargar .env
set "DATABASE_URL="
set "PG_HOST=localhost"
set "PG_PORT=5432"
set "PG_USER=postgres"
set "PG_PASS=postgres"
set "PG_DBNAME=inventario"

if exist ".env" (
    for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
        if "%%a"=="DATABASE_URL" set "DATABASE_URL=%%b"
    )
)

REM Parsear DATABASE_URL si existe
if defined DATABASE_URL (
    REM Extraer componentes con Python
    if exist "venv\Scripts\python.exe" (
        for /f "tokens=1,2,3,4,5 delims=|" %%a in ('venv\Scripts\python -c "from urllib.parse import urlparse; p=urlparse(r'!DATABASE_URL!'); print(f'{p.hostname}|{p.port or 5432}|{p.username or \"postgres\"}|{p.password or \"postgres\"}|{(p.path or \"/inventario\").lstrip(\"/\")}')" 2^>nul') do (
            set "PG_HOST=%%a"
            set "PG_PORT=%%b"
            set "PG_USER=%%c"
            set "PG_PASS=%%d"
            set "PG_DBNAME=%%e"
        )
    )
) else (
    echo   %YELLOW%[AVISO]%RESET% No se encontro archivo .env. Usando valores por defecto.
    echo   Ejecute setup.bat para configurar la conexion.
    echo.
)

REM Buscar psql y pg_dump
set "PSQL_CMD="
set "PGDUMP_CMD="

where psql > nul 2>&1
if %errorlevel% equ 0 (
    set "PSQL_CMD=psql"
    set "PGDUMP_CMD=pg_dump"
) else (
    for %%V in (17 16 15 14 13) do (
        if exist "C:\Program Files\PostgreSQL\%%V\bin\psql.exe" (
            set "PSQL_CMD=C:\Program Files\PostgreSQL\%%V\bin\psql.exe"
            set "PGDUMP_CMD=C:\Program Files\PostgreSQL\%%V\bin\pg_dump.exe"
            goto :tools_found
        )
    )
)
:tools_found

set "PGPASSWORD=!PG_PASS!"

:menu
cls
echo.
echo   %BOLD%=========================================================%RESET%
echo   %BOLD%     TechStock - Copias de Seguridad (Backups)           %RESET%
echo   %BOLD%=========================================================%RESET%
echo.
echo   Base de datos: %CYAN%!PG_DBNAME!%RESET% en %CYAN%!PG_HOST!:!PG_PORT!%RESET%
echo   Directorio:    %CYAN%!BACKUP_DIR!%RESET%
echo.
echo   %BOLD%Opciones:%RESET%
echo.
echo   1. Crear copia de seguridad completa
echo   2. Crear copia de seguridad (solo datos)
echo   3. Restaurar desde copia de seguridad
echo   4. Ver copias de seguridad existentes
echo   5. Eliminar copias antiguas
echo   6. Programar backup automatico
echo   7. Salir
echo.
set /p "opcion=  Seleccione una opcion [1-7]: "

if "!opcion!"=="1" goto :backup_completo
if "!opcion!"=="2" goto :backup_datos
if "!opcion!"=="3" goto :restaurar
if "!opcion!"=="4" goto :listar
if "!opcion!"=="5" goto :limpiar
if "!opcion!"=="6" goto :programar
if "!opcion!"=="7" goto :salir

echo   %RED%[ERROR]%RESET% Opcion no valida.
timeout /t 2 > nul
goto :menu

REM =========================================================
REM  1. BACKUP COMPLETO (estructura + datos)
REM =========================================================
:backup_completo
echo.
echo   %BOLD%Creando copia de seguridad completa...%RESET%
echo.

if not defined PGDUMP_CMD (
    echo   %RED%[ERROR]%RESET% pg_dump no encontrado. Instale PostgreSQL o agregue su ruta al PATH.
    goto :pause_menu
)

for /f "delims=" %%T in ('venv\Scripts\python -c "from datetime import datetime; print(datetime.now().strftime('%%Y%%m%%d_%%H%%M%%S'))" 2^>nul') do set "TIMESTAMP=%%T"
if not defined TIMESTAMP set "TIMESTAMP=backup"
set "FILENAME=techstock_full_!TIMESTAMP!.sql"
set "FILEPATH=!BACKUP_DIR!\!FILENAME!"

echo   Exportando base de datos...

"!PGDUMP_CMD!" -h !PG_HOST! -p !PG_PORT! -U !PG_USER! -d !PG_DBNAME! --no-owner --no-acl -f "!FILEPATH!" 2>&1

if %errorlevel% neq 0 (
    echo   %RED%[ERROR]%RESET% Error al crear el backup.
    echo   Verifique que PostgreSQL esta corriendo y las credenciales son correctas.
    goto :pause_menu
)

for %%A in ("!FILEPATH!") do set "FSIZE=%%~zA"
set /a "FSIZE_KB=!FSIZE!/1024"

echo.
echo   %GREEN%[OK]%RESET% Backup creado exitosamente.
echo   Archivo:  !FILENAME!
echo   Tamano:   !FSIZE_KB! KB
echo   Ruta:     !FILEPATH!
goto :pause_menu

REM =========================================================
REM  2. BACKUP SOLO DATOS
REM =========================================================
:backup_datos
echo.
echo   %BOLD%Creando copia de seguridad (solo datos)...%RESET%
echo.

if not defined PGDUMP_CMD (
    echo   %RED%[ERROR]%RESET% pg_dump no encontrado.
    goto :pause_menu
)

for /f "delims=" %%T in ('venv\Scripts\python -c "from datetime import datetime; print(datetime.now().strftime('%%Y%%m%%d_%%H%%M%%S'))" 2^>nul') do set "TIMESTAMP=%%T"
if not defined TIMESTAMP set "TIMESTAMP=backup"
set "FILENAME=techstock_data_!TIMESTAMP!.sql"
set "FILEPATH=!BACKUP_DIR!\!FILENAME!"

echo   Exportando datos...

"!PGDUMP_CMD!" -h !PG_HOST! -p !PG_PORT! -U !PG_USER! -d !PG_DBNAME! --data-only --no-owner --no-acl --column-inserts -f "!FILEPATH!" 2>&1

if %errorlevel% neq 0 (
    echo   %RED%[ERROR]%RESET% Error al crear el backup.
    goto :pause_menu
)

for %%A in ("!FILEPATH!") do set "FSIZE=%%~zA"
set /a "FSIZE_KB=!FSIZE!/1024"

echo.
echo   %GREEN%[OK]%RESET% Backup de datos creado.
echo   Archivo:  !FILENAME!
echo   Tamano:   !FSIZE_KB! KB
goto :pause_menu

REM =========================================================
REM  3. RESTAURAR BACKUP
REM =========================================================
:restaurar
echo.
echo   %BOLD%Restaurar copia de seguridad%RESET%
echo.

set "COUNT=0"
echo   Backups disponibles:
echo   -------------------------------------------------
for /f "delims=" %%F in ('dir /b /o-d "%BACKUP_DIR%\*.sql" 2^>nul') do (
    set /a "COUNT+=1"
    set "BK_!COUNT!=%%F"
    for %%A in ("%BACKUP_DIR%\%%F") do set "SIZE=%%~zA"
    set /a "SIZE_KB=!SIZE!/1024"
    echo   !COUNT!. %%F  (!SIZE_KB! KB^)
)

if !COUNT! equ 0 (
    echo   %YELLOW%[AVISO]%RESET% No hay backups disponibles.
    goto :pause_menu
)

echo.
set /p "NUM=  Seleccione el numero del backup a restaurar (0=cancelar): "

if "!NUM!"=="0" goto :menu
if !NUM! gtr !COUNT! (
    echo   %RED%[ERROR]%RESET% Numero invalido.
    goto :pause_menu
)

set "SELECTED=!BK_%NUM%!"
echo.
echo   %YELLOW%ATENCION: Esto reemplazara TODOS los datos actuales de la base de datos.%RESET%
echo   Archivo: !SELECTED!
echo.
choice /c SN /m "  Esta seguro de continuar? (S/N)"
if !errorlevel! neq 1 goto :menu

echo.
echo   Restaurando base de datos...

REM Cerrar conexiones activas
"!PSQL_CMD!" -h !PG_HOST! -p !PG_PORT! -U !PG_USER! -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='!PG_DBNAME!' AND pid <> pg_backend_pid();" > nul 2>&1

REM Eliminar y recrear la base de datos
"!PSQL_CMD!" -h !PG_HOST! -p !PG_PORT! -U !PG_USER! -c "DROP DATABASE IF EXISTS !PG_DBNAME!;" > nul 2>&1
"!PSQL_CMD!" -h !PG_HOST! -p !PG_PORT! -U !PG_USER! -c "CREATE DATABASE !PG_DBNAME! ENCODING 'UTF8';" > nul 2>&1

if %errorlevel% neq 0 (
    echo   %RED%[ERROR]%RESET% Error al recrear la base de datos.
    goto :pause_menu
)

REM Restaurar el dump SQL
"!PSQL_CMD!" -h !PG_HOST! -p !PG_PORT! -U !PG_USER! -d !PG_DBNAME! -f "!BACKUP_DIR!\!SELECTED!" > nul 2>&1

if %errorlevel% neq 0 (
    echo   %YELLOW%[AVISO]%RESET% La restauracion termino con advertencias (puede ser normal).
) else (
    echo   %GREEN%[OK]%RESET% Base de datos restaurada exitosamente desde: !SELECTED!
)
goto :pause_menu

REM =========================================================
REM  4. LISTAR BACKUPS
REM =========================================================
:listar
echo.
echo   %BOLD%Copias de seguridad existentes%RESET%
echo   Directorio: !BACKUP_DIR!
echo   ---------------------------------------------------------

set "COUNT=0"
set "TOTAL_SIZE=0"

for /f "delims=" %%F in ('dir /b /o-d "%BACKUP_DIR%\*.sql" 2^>nul') do (
    set /a "COUNT+=1"
    for %%A in ("%BACKUP_DIR%\%%F") do (
        set "SIZE=%%~zA"
        set "FDATE=%%~tA"
    )
    set /a "SIZE_KB=!SIZE!/1024"
    set /a "TOTAL_SIZE+=!SIZE!"

    if !COUNT! lss 10 (set "PAD= ") else (set "PAD=")
    echo   !PAD!!COUNT!. %%F    !SIZE_KB! KB    !FDATE!
)

if !COUNT! equ 0 (
    echo.
    echo   (No hay backups)
) else (
    set /a "TOTAL_KB=!TOTAL_SIZE!/1024"
    set /a "TOTAL_MB=!TOTAL_SIZE!/1048576"
    echo   ---------------------------------------------------------
    echo   Total: !COUNT! archivo(s), ~!TOTAL_MB! MB
)
goto :pause_menu

REM =========================================================
REM  5. LIMPIAR BACKUPS ANTIGUOS
REM =========================================================
:limpiar
echo.
echo   %BOLD%Eliminar copias de seguridad antiguas%RESET%
echo.
echo   Esta opcion mantiene las ultimas N copias y elimina el resto.
echo.
set /p "KEEP=  Cuantas copias desea conservar? [5]: " || set "KEEP=5"

set "COUNT=0"
set "DELETED=0"
for /f "delims=" %%F in ('dir /b /o-d "%BACKUP_DIR%\*.sql" 2^>nul') do (
    set /a "COUNT+=1"
    if !COUNT! gtr !KEEP! (
        del "%BACKUP_DIR%\%%F"
        set /a "DELETED+=1"
        echo   Eliminado: %%F
    )
)

if !DELETED! equ 0 (
    echo   No hay backups antiguos para eliminar.
) else (
    echo.
    echo   %GREEN%[OK]%RESET% !DELETED! backup(s) eliminado(s). Se conservaron las ultimas !KEEP! copias.
)
goto :pause_menu

REM =========================================================
REM  6. PROGRAMAR BACKUP AUTOMATICO
REM =========================================================
:programar
echo.
echo   %BOLD%Programar backup automatico (Programador de tareas de Windows)%RESET%
echo.
echo   Opciones de frecuencia:
echo.
echo   1. Cada dia (a las 2:00 AM)
echo   2. Cada semana (lunes a las 2:00 AM)
echo   3. Cada mes (dia 1 a las 2:00 AM)
echo   4. Eliminar tarea programada existente
echo   5. Cancelar
echo.
set /p "FREQ=  Seleccione [1-5]: "

if "!FREQ!"=="5" goto :menu
if "!FREQ!"=="4" goto :eliminar_tarea

set "TASK_SCRIPT=%~dp0backup_auto.bat"
set "TASK_NAME=TechStock_Backup_Auto"

REM Crear script automatico que usa Python para timestamps
(
echo @echo off
echo chcp 65001 ^> nul 2^>^&1
echo setlocal enabledelayedexpansion
echo cd /d "%%~dp0"
echo if exist ".env" for /f "usebackq tokens=1,* delims==" %%%%a in ^(".env"^) do set "%%%%a=%%%%b"
echo set "PGDUMP_CMD="
echo where pg_dump ^> nul 2^>^&1
echo if %%errorlevel%% equ 0 ^(set "PGDUMP_CMD=pg_dump"^) else ^(
echo     for %%%%V in ^(17 16 15 14^) do if exist "C:\Program Files\PostgreSQL\%%%%V\bin\pg_dump.exe" set "PGDUMP_CMD=C:\Program Files\PostgreSQL\%%%%V\bin\pg_dump.exe"
echo ^)
echo if not defined PGDUMP_CMD exit /b 1
echo for /f "delims=" %%%%T in ^('venv\Scripts\python -c "from datetime import datetime; print^(datetime.now^(^).strftime^('%%%%%%%%Y%%%%%%%%m%%%%%%%%d_%%%%%%%%H%%%%%%%%M%%%%%%%%S'^)^)" 2^^^>nul'^) do set "TS=%%%%T"
echo if not defined TS set "TS=auto"
echo if exist "venv\Scripts\python.exe" ^(
echo     for /f "tokens=1,2,3,4,5 delims=|" %%%%a in ^('venv\Scripts\python -c "from urllib.parse import urlparse; p=urlparse^(r'%%DATABASE_URL%%'^); print^(f'{p.hostname}^|{p.port or 5432}^|{p.username or \"postgres\"}^|{p.password or \"postgres\"}^|{^(p.path or \"/inventario\"^).lstrip^(\"/\"^)}'^)" 2^^^>nul'^) do ^(
echo         set "PGPASSWORD=%%%%d"
echo         "%%PGDUMP_CMD%%" -h %%%%a -p %%%%b -U %%%%c -d %%%%e --no-owner --no-acl -f "backups\techstock_auto_%%TS%%.sql" 2^^^>nul
echo     ^)
echo ^)
echo set "N=0"
echo for /f "delims=" %%%%F in ^('dir /b /o-d "backups\techstock_auto_*.sql" 2^^^>nul'^) do ^(
echo     set /a "N+=1"
echo     if %%N%% gtr 30 del "backups\%%%%F"
echo ^)
) > "!TASK_SCRIPT!"

if "!FREQ!"=="1" (
    schtasks /create /tn "!TASK_NAME!" /tr "\"!TASK_SCRIPT!\"" /sc DAILY /st 02:00 /f > nul 2>&1
    set "FREQ_DESC=diario a las 2:00 AM"
)
if "!FREQ!"=="2" (
    schtasks /create /tn "!TASK_NAME!" /tr "\"!TASK_SCRIPT!\"" /sc WEEKLY /d MON /st 02:00 /f > nul 2>&1
    set "FREQ_DESC=semanal (lunes 2:00 AM)"
)
if "!FREQ!"=="3" (
    schtasks /create /tn "!TASK_NAME!" /tr "\"!TASK_SCRIPT!\"" /sc MONTHLY /d 1 /st 02:00 /f > nul 2>&1
    set "FREQ_DESC=mensual (dia 1, 2:00 AM)"
)

if %errorlevel% equ 0 (
    echo.
    echo   %GREEN%[OK]%RESET% Tarea programada creada: !FREQ_DESC!
    echo   Nombre: !TASK_NAME!
    echo   Script: !TASK_SCRIPT!
    echo   Los backups automaticos se guardaran en: backups\
) else (
    echo   %YELLOW%[AVISO]%RESET% No se pudo crear la tarea. Intente ejecutar este script como Administrador.
)
goto :pause_menu

:eliminar_tarea
schtasks /delete /tn "TechStock_Backup_Auto" /f > nul 2>&1
if %errorlevel% equ 0 (
    echo   %GREEN%[OK]%RESET% Tarea programada eliminada.
) else (
    echo   %CYAN%[INFO]%RESET% No habia tarea programada.
)
if exist "%~dp0backup_auto.bat" del "%~dp0backup_auto.bat"
goto :pause_menu

REM =========================================================
:pause_menu
echo.
pause
goto :menu

:salir
endlocal
exit /b 0
