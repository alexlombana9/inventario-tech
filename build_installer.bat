@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

:: ============================================================
:: TechStock v2.0 — Build Installer Script
:: Genera el instalador .exe completo
:: PyInstaller + PostgreSQL portable + Inno Setup
:: ============================================================

title TechStock — Build Installer

echo.
echo  ======================================================
echo     TechStock v2.0 — Build Installer
echo     PyInstaller + PostgreSQL Portable + Inno Setup
echo  ======================================================
echo.

:: ── Verificar directorio correcto ────────────────────────
if not exist "main.py" (
    echo [ERROR] No se encuentra main.py. Ejecute desde la raiz del proyecto.
    pause
    exit /b 1
)

:: ── Verificar Python ─────────────────────────────────────
set PYTHON=python
if exist "venv\Scripts\python.exe" set PYTHON=venv\Scripts\python.exe

echo [1/6] Verificando Python...
%PYTHON% --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado. Instale Python 3.10+.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('%PYTHON% --version') do echo        %%i

:: ── Verificar/Instalar PyInstaller ───────────────────────
echo.
echo [2/6] Verificando PyInstaller...
%PYTHON% -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo        Instalando PyInstaller...
    %PYTHON% -m pip install pyinstaller --quiet
    if errorlevel 1 (
        echo [ERROR] No se pudo instalar PyInstaller.
        pause
        exit /b 1
    )
)
for /f "tokens=*" %%i in ('%PYTHON% -m PyInstaller --version') do echo        PyInstaller %%i

:: ── Instalar dependencias ────────────────────────────────
echo.
echo [3/6] Verificando dependencias...
%PYTHON% -m pip install -r requirements.txt --quiet 2>nul

:: ── Descargar PostgreSQL portable ────────────────────────
echo.
echo [4/6] Preparando PostgreSQL portable...

set PG_VERSION=16.8-1
set PG_ZIP=postgresql-%PG_VERSION%-windows-x64-binaries.zip
set PG_URL=https://get.enterprisedb.com/postgresql/%PG_ZIP%

if not exist "pgsql\bin\pg_ctl.exe" (
    if not exist "%PG_ZIP%" (
        echo        Descargando PostgreSQL %PG_VERSION% portable...
        echo        URL: %PG_URL%
        echo        Esto puede tomar varios minutos...
        curl -L -o "%PG_ZIP%" "%PG_URL%"
        if errorlevel 1 (
            echo [ERROR] No se pudo descargar PostgreSQL.
            echo        Descargue manualmente desde:
            echo        https://www.enterprisedb.com/download-postgresql-binaries
            echo        y extraiga la carpeta 'pgsql' en la raiz del proyecto.
            pause
            exit /b 1
        )
    )
    echo        Extrayendo PostgreSQL...
    tar -xf "%PG_ZIP%" pgsql 2>nul
    if not exist "pgsql\bin\pg_ctl.exe" (
        powershell -Command "Expand-Archive -Path '%PG_ZIP%' -DestinationPath '.' -Force" 2>nul
    )
    if not exist "pgsql\bin\pg_ctl.exe" (
        echo [ERROR] No se pudo extraer PostgreSQL.
        pause
        exit /b 1
    )
    echo        PostgreSQL %PG_VERSION% portable listo.
) else (
    echo        PostgreSQL portable ya existe.
)

:: ── Ejecutar PyInstaller ─────────────────────────────────
echo.
echo [5/6] Construyendo distribucion con PyInstaller...
echo        Esto puede tomar varios minutos...
echo.

if exist "dist\TechStock" rmdir /s /q "dist\TechStock"
if exist "build\TechStock" rmdir /s /q "build\TechStock"

%PYTHON% -m PyInstaller techstock.spec --noconfirm --clean
if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller fallo. Revise los errores arriba.
    pause
    exit /b 1
)

if not exist "dist\TechStock\TechStock.exe" (
    echo [ERROR] No se genero dist\TechStock\TechStock.exe
    pause
    exit /b 1
)

echo.
echo        Build PyInstaller completado.

:: ── Copiar archivos adicionales ──────────────────────────
echo        Copiando archivos adicionales...

:: Templates y static (por si PyInstaller no los incluyo bien)
if not exist "dist\TechStock\templates" (
    xcopy "templates" "dist\TechStock\templates\" /E /I /Q /Y >nul
)
if not exist "dist\TechStock\static" (
    xcopy "static" "dist\TechStock\static\" /E /I /Q /Y >nul
)

:: PostgreSQL portable
echo        Copiando PostgreSQL portable...
if not exist "dist\TechStock\pgsql" (
    xcopy "pgsql" "dist\TechStock\pgsql\" /E /I /Q /Y >nul
)

:: Directorio de uploads
if not exist "dist\TechStock\static\uploads\avatars" (
    mkdir "dist\TechStock\static\uploads\avatars" 2>nul
)

:: .env por defecto para PostgreSQL portable
if not exist "dist\TechStock\.env" (
    echo DATABASE_URL=postgresql://techstock:techstock@localhost:5433/techstock> "dist\TechStock\.env"
)

:: ── Ejecutar Inno Setup ──────────────────────────────────
echo.
echo [6/6] Generando instalador con Inno Setup...

set ISCC=
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
)

if not exist "dist\installer" mkdir "dist\installer"

if defined ISCC (
    echo        Usando: !ISCC!
    "!ISCC!" installer\techstock.iss
    if errorlevel 1 (
        echo.
        echo [ERROR] Inno Setup fallo.
        pause
        exit /b 1
    )
    echo.
    echo  ======================================================
    echo     BUILD COMPLETADO EXITOSAMENTE
    echo  ======================================================
    echo.
    echo  Instalador: dist\installer\TechStock_Setup_v2.0.exe
    echo  Portable:   dist\TechStock\TechStock.exe
    echo.
) else (
    echo.
    echo [INFO] Inno Setup no encontrado.
    echo        Para generar el instalador, instale Inno Setup 6:
    echo        https://jrsoftware.org/isdl.php
    echo.
    echo        La version portable esta lista en:
    echo        dist\TechStock\TechStock.exe
    echo.
)

pause
