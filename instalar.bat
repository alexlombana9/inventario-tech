@echo off
chcp 65001 > nul 2>&1
setlocal enabledelayedexpansion
cd /d "%~dp0"
title TechStock v2.0 - Instalador Completo

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
echo  %M%║%N%   %B%%C%████████╗███████╗ ██████╗██╗  ██╗%N%                    %M%║%N%
echo  %M%║%N%   %B%%C%╚══██╔══╝██╔════╝██╔════╝██║  ██║%N%                    %M%║%N%
echo  %M%║%N%   %B%%C%   ██║   █████╗  ██║     ███████║%N%                    %M%║%N%
echo  %M%║%N%   %B%%C%   ██║   ██╔══╝  ██║     ██╔══██║%N%                    %M%║%N%
echo  %M%║%N%   %B%%C%   ██║   ███████╗╚██████╗██║  ██║%N%                    %M%║%N%
echo  %M%║%N%   %B%%C%   ╚═╝   ╚══════╝ ╚═════╝╚═╝  ╚═╝  %M%Stock v2.0%N%     %M%║%N%
echo  %M%║%N%                                                           %M%║%N%
echo  %M%║%N%   %D%Instalador Completo - Sistema de Inventario%N%            %M%║%N%
echo  %M%║%N%                                                           %M%║%N%
echo  %M%╚═══════════════════════════════════════════════════════════╝%N%
echo.
echo  %D%Este instalador configurara automaticamente:%N%
echo    %C%1.%N% Python 3.12      %D%(lenguaje del sistema)%N%
echo    %C%2.%N% PostgreSQL 16    %D%(base de datos)%N%
echo    %C%3.%N% Conexion DB      %D%(configuracion PostgreSQL)%N%
echo    %C%4.%N% Entorno virtual  %D%(dependencias aisladas)%N%
echo    %C%5.%N% Dependencias     %D%(FastAPI, SQLAlchemy, etc.)%N%
echo    %C%6.%N% Usuario ROOT     %D%(credenciales del administrador)%N%
echo    %C%7.%N% Base de datos    %D%(tablas + datos iniciales)%N%
echo    %C%8.%N% Ejecutable       %D%(TechStock.exe + acceso directo)%N%
echo.

set "ERRORS=0"
set "PYTHON_INSTALLED=0"
set "PG_INSTALLED=0"

REM ══════════════════════════════════════════════════════════
REM  Verificar permisos de administrador
REM ══════════════════════════════════════════════════════════
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  %Y%[AVISO]%N% Se recomienda ejecutar como Administrador para instalar
    echo          Python y PostgreSQL automaticamente.
    echo.
    echo  %D%Clic derecho sobre instalar.bat ^> "Ejecutar como administrador"%N%
    echo.
    set "RESP="
    set /p "RESP=  Continuar de todas formas? (S/N): "
    if /i "!RESP!"=="N" (
        pause
        exit /b 0
    )
    echo.
)

REM ══════════════════════════════════════════════════════════
REM  PASO 1/8: Python
REM ══════════════════════════════════════════════════════════
echo  %B%══════════════════════════════════════════════════════════%N%
echo  %B%%C%[1/8]%N% %B%Verificando Python...%N%
echo  %B%══════════════════════════════════════════════════════════%N%

python --version > nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do set "PYVER=%%v"
    echo    %G%✓%N% Python !PYVER! encontrado.
    set "PYTHON_INSTALLED=1"
) else (
    echo    %Y%⚠%N% Python no encontrado. Intentando instalar...
    echo.

    REM Intentar con winget
    winget --version > nul 2>&1
    if !errorlevel! equ 0 (
        echo    %C%↓%N% Descargando Python 3.12 via winget...
        echo    %D%  Esto puede tardar unos minutos...%N%
        winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements --silent 2>nul
        if !errorlevel! equ 0 (
            echo    %G%✓%N% Python instalado correctamente.
            echo    %Y%⚠%N% Es necesario reiniciar esta ventana para que Python sea visible.
            echo.
            echo    %B%Por favor cierre esta ventana y vuelva a ejecutar instalar.bat%N%
            pause
            exit /b 0
        ) else (
            echo    %R%✗%N% No se pudo instalar Python automaticamente.
        )
    )

    REM Intentar descarga directa
    if !PYTHON_INSTALLED! equ 0 (
        echo    %C%↓%N% Descargando Python 3.12.7 directamente...
        set "PY_URL=https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe"
        set "PY_EXE=%TEMP%\python_installer.exe"
        powershell -Command "Invoke-WebRequest -Uri '!PY_URL!' -OutFile '!PY_EXE!'" 2>nul
        if exist "!PY_EXE!" (
            echo    %C%⧖%N% Ejecutando instalador de Python ^(modo silencioso^)...
            "!PY_EXE!" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_tcltk=1
            if !errorlevel! equ 0 (
                echo    %G%✓%N% Python instalado. Reinicie esta ventana y ejecute de nuevo.
                del "!PY_EXE!" 2>nul
                pause
                exit /b 0
            )
            del "!PY_EXE!" 2>nul
        )
        echo    %R%✗%N% No se pudo instalar Python automaticamente.
        echo.
        echo    %B%Instale Python manualmente:%N%
        echo      1. Vaya a %C%https://python.org/downloads%N%
        echo      2. Descargue Python 3.12+
        echo      3. %Y%IMPORTANTE: Marque "Add Python to PATH"%N%
        echo      4. Vuelva a ejecutar este instalador.
        echo.
        set /a ERRORS+=1
        pause
        exit /b 1
    )
)

REM Refrescar PATH por si se instalo recien
set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"

REM ══════════════════════════════════════════════════════════
REM  PASO 2/8: PostgreSQL
REM ══════════════════════════════════════════════════════════
echo.
echo  %B%══════════════════════════════════════════════════════════%N%
echo  %B%%C%[2/8]%N% %B%Verificando PostgreSQL...%N%
echo  %B%══════════════════════════════════════════════════════════%N%

set "PSQL_CMD="

REM Buscar psql en PATH
where psql > nul 2>&1
if %errorlevel% equ 0 (
    set "PSQL_CMD=psql"
    goto :pg_ok
)

REM Buscar en rutas comunes
for %%V in (17 16 15 14) do (
    if exist "C:\Program Files\PostgreSQL\%%V\bin\psql.exe" (
        set "PSQL_CMD=C:\Program Files\PostgreSQL\%%V\bin\psql.exe"
        set "PATH=C:\Program Files\PostgreSQL\%%V\bin;!PATH!"
        goto :pg_ok
    )
)

REM No encontrado — instalar
echo    %Y%⚠%N% PostgreSQL no encontrado. Intentando instalar...
echo.

winget --version > nul 2>&1
if %errorlevel% equ 0 (
    echo    %C%↓%N% Instalando PostgreSQL 16 via winget...
    echo    %D%  El instalador interactivo se abrira para que configure la contrasena.%N%
    echo    %Y%  IMPORTANTE: Use la contrasena "postgres" para simplificar la configuracion.%N%
    echo    %Y%  Deje el puerto por defecto ^(5432^).%N%
    echo.
    winget install -e --id PostgreSQL.PostgreSQL.16 --accept-package-agreements --accept-source-agreements 2>nul
    if !errorlevel! equ 0 (
        REM Buscar de nuevo
        for %%V in (17 16 15 14) do (
            if exist "C:\Program Files\PostgreSQL\%%V\bin\psql.exe" (
                set "PSQL_CMD=C:\Program Files\PostgreSQL\%%V\bin\psql.exe"
                set "PATH=C:\Program Files\PostgreSQL\%%V\bin;!PATH!"
                goto :pg_ok
            )
        )
    )
)

echo    %R%✗%N% No se pudo instalar PostgreSQL automaticamente.
echo.
echo    %B%Instale PostgreSQL manualmente:%N%
echo      1. Vaya a %C%https://www.postgresql.org/download/windows/%N%
echo      2. Descargue PostgreSQL 16
echo      3. Use contrasena: %Y%postgres%N%
echo      4. Deje el puerto: %Y%5432%N%
echo      5. Vuelva a ejecutar este instalador.
echo.
set "RESP="
set /p "RESP=  Abrir pagina de descarga? (S/N): "
if /i "!RESP!"=="S" start https://www.postgresql.org/download/windows/
set /a ERRORS+=1
pause
exit /b 1

:pg_ok
for /f "tokens=3" %%v in ('"!PSQL_CMD!" --version 2^>^&1') do set "PGVER=%%v"
echo    %G%✓%N% PostgreSQL !PGVER! encontrado.

REM ══════════════════════════════════════════════════════════
REM  PASO 3/8: Configurar conexion PostgreSQL
REM ══════════════════════════════════════════════════════════
echo.
echo  %B%══════════════════════════════════════════════════════════%N%
echo  %B%%C%[3/8]%N% %B%Configurando conexion a PostgreSQL...%N%
echo  %B%══════════════════════════════════════════════════════════%N%

set "PG_HOST=localhost"
set "PG_PORT=5432"
set "PG_USER=postgres"
set "PG_PASS=postgres"
set "PG_DBNAME=inventario"

if exist ".env" (
    echo    %C%ℹ%N% Archivo .env existente encontrado.
    for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
        if "%%a"=="DATABASE_URL" echo    %D%  %%b%N%
    )
    echo.
    set "RESP="
    set /p "RESP=  Mantener configuracion existente? (S/N): "
    if /i "!RESP!"=="S" goto :skip_config
    echo.
)

echo.
echo    %D%Ingrese los datos de conexion (ENTER = valor por defecto):%N%
echo.
set /p "PG_HOST=    Host [%PG_HOST%]: " || set "PG_HOST=localhost"
set /p "PG_PORT=    Puerto [%PG_PORT%]: " || set "PG_PORT=5432"
set /p "PG_USER=    Usuario [%PG_USER%]: " || set "PG_USER=postgres"
set /p "PG_PASS=    Contrasena [%PG_PASS%]: " || set "PG_PASS=postgres"
set /p "PG_DBNAME=    Base de datos [%PG_DBNAME%]: " || set "PG_DBNAME=inventario"

echo DATABASE_URL=postgresql://!PG_USER!:!PG_PASS!@!PG_HOST!:!PG_PORT!/!PG_DBNAME!> .env
echo    %G%✓%N% Archivo .env creado.

:skip_config
REM Leer DATABASE_URL del .env
for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
    if "%%a"=="DATABASE_URL" set "DATABASE_URL=%%b"
)

REM Parsear credenciales de DATABASE_URL
if defined DATABASE_URL (
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

REM Verificar conexion al servidor PostgreSQL
set "PGPASSWORD=!PG_PASS!"
"!PSQL_CMD!" -h !PG_HOST! -p !PG_PORT! -U !PG_USER! -c "SELECT 1" > nul 2>&1
if %errorlevel% neq 0 (
    echo    %Y%⚠%N% No se pudo conectar a PostgreSQL.
    echo    %D%  Intentando iniciar el servicio...%N%
    net start postgresql-x64-16 > nul 2>&1 || net start postgresql-x64-15 > nul 2>&1 || net start postgresql-x64-17 > nul 2>&1
    timeout /t 3 /nobreak > nul
    "!PSQL_CMD!" -h !PG_HOST! -p !PG_PORT! -U !PG_USER! -c "SELECT 1" > nul 2>&1
    if !errorlevel! neq 0 (
        echo    %R%✗%N% No se pudo conectar a PostgreSQL.
        echo      Verifique que el servicio esta corriendo y la contrasena es correcta.
        echo      Servicios de Windows ^> postgresql-x64-16 ^> Iniciar
        set /a ERRORS+=1
        pause
        exit /b 1
    )
)
echo    %G%✓%N% Conexion a PostgreSQL verificada.

REM Crear base de datos si no existe
"!PSQL_CMD!" -h !PG_HOST! -p !PG_PORT! -U !PG_USER! -d !PG_DBNAME! -c "SELECT 1" > nul 2>&1
if %errorlevel% equ 0 (
    echo    %C%ℹ%N% Base de datos '!PG_DBNAME!' ya existe.
) else (
    echo    %C%⧖%N% Creando base de datos '!PG_DBNAME!'...
    "!PSQL_CMD!" -h !PG_HOST! -p !PG_PORT! -U !PG_USER! -c "CREATE DATABASE !PG_DBNAME! ENCODING 'UTF8'" > nul 2>&1
    if !errorlevel! neq 0 (
        echo    %R%✗%N% Error al crear la base de datos.
        set /a ERRORS+=1
        pause
        exit /b 1
    )
    echo    %G%✓%N% Base de datos '!PG_DBNAME!' creada.
)

REM ══════════════════════════════════════════════════════════
REM  PASO 4/8: Entorno virtual Python
REM ══════════════════════════════════════════════════════════
echo.
echo  %B%══════════════════════════════════════════════════════════%N%
echo  %B%%C%[4/8]%N% %B%Creando entorno virtual Python...%N%
echo  %B%══════════════════════════════════════════════════════════%N%

if exist "venv\Scripts\activate.bat" (
    echo    %C%ℹ%N% Entorno virtual ya existe.
) else (
    echo    %C%⧖%N% Creando entorno virtual...
    python -m venv venv
    if !errorlevel! neq 0 (
        echo    %R%✗%N% Error al crear el entorno virtual.
        set /a ERRORS+=1
        pause
        exit /b 1
    )
    echo    %G%✓%N% Entorno virtual creado.
)

call venv\Scripts\activate.bat

REM ══════════════════════════════════════════════════════════
REM  PASO 5/8: Dependencias
REM ══════════════════════════════════════════════════════════
echo.
echo  %B%══════════════════════════════════════════════════════════%N%
echo  %B%%C%[5/8]%N% %B%Instalando dependencias Python...%N%
echo  %B%══════════════════════════════════════════════════════════%N%

echo    %C%⧖%N% Actualizando pip...
python -m pip install --upgrade pip --no-cache-dir -q 2>nul
if !errorlevel! neq 0 (
    echo    %Y%⚠%N% No se pudo actualizar pip, continuando con la version actual...
)

echo    %C%⧖%N% Instalando paquetes ^(FastAPI, SQLAlchemy, etc.^)...
pip install -r requirements.txt --no-cache-dir -q
if !errorlevel! neq 0 (
    echo    %Y%⚠%N% Primer intento fallo. Reintentando sin cache y con permisos de usuario...
    pip install -r requirements.txt --no-cache-dir --user -q 2>nul
    if !errorlevel! neq 0 (
        echo    %Y%⚠%N% Segundo intento fallo. Desactivando antivirus temporalmente...
        echo    %D%  Si tiene Windows Defender u otro antivirus, agregue esta carpeta%N%
        echo    %D%  a las exclusiones: %cd%%N%
        echo.
        echo    %C%⧖%N% Ultimo intento con pip verbose...
        pip install -r requirements.txt --no-cache-dir --no-warn-script-location 2>&1
        if !errorlevel! neq 0 (
            echo.
            echo    %R%✗%N% Error al instalar dependencias.
            echo.
            echo    %B%Posibles soluciones:%N%
            echo      %C%1.%N% Ejecute instalar.bat como %Y%Administrador%N%
            echo         ^(Clic derecho ^> Ejecutar como administrador^)
            echo      %C%2.%N% Desactive el antivirus temporalmente
            echo      %C%3.%N% Agregue esta carpeta como exclusion en Windows Defender:
            echo         %D%%cd%%N%
            echo      %C%4.%N% Ejecute manualmente:
            echo         %D%cd %cd%%N%
            echo         %D%venv\Scripts\activate%N%
            echo         %D%pip install -r requirements.txt --no-cache-dir%N%
            echo.
            set /a ERRORS+=1
            pause
            exit /b 1
        )
    )
)
echo    %G%✓%N% Dependencias instaladas.

REM Instalar PyInstaller para generar .exe
echo    %C%⧖%N% Instalando PyInstaller...
pip install pyinstaller --no-cache-dir -q 2>nul
echo    %G%✓%N% PyInstaller listo.

REM ══════════════════════════════════════════════════════════
REM  PASO 6/8: Credenciales del usuario administrador
REM ══════════════════════════════════════════════════════════
echo.
echo  %B%══════════════════════════════════════════════════════════%N%
echo  %B%%C%[6/8]%N% %B%Configurando usuario administrador (ROOT)...%N%
echo  %B%══════════════════════════════════════════════════════════%N%
echo.
echo    %D%Configure las credenciales del usuario principal.%N%
echo    %D%Presione ENTER para usar el valor por defecto [entre corchetes].%N%
echo.
set "ADMIN_USERNAME=admin"
set "ADMIN_PASSWORD="
set "ADMIN_NAME=Administrador"
set /p "ADMIN_USERNAME=    Usuario administrador [admin]: " || set "ADMIN_USERNAME=admin"
set /p "ADMIN_PASSWORD=    Contrasena del administrador: "
if "!ADMIN_PASSWORD!"=="" (
    set "ADMIN_PASSWORD=admin123"
    echo    %Y%⚠%N% Se usara la contrasena por defecto: admin123
    echo    %Y%  Cambiela despues del primer inicio de sesion.%N%
)
set /p "ADMIN_NAME=    Nombre completo [Administrador]: " || set "ADMIN_NAME=Administrador"
echo.
echo    %G%✓%N% Usuario: !ADMIN_USERNAME!
echo    %G%✓%N% Nombre:  !ADMIN_NAME!

REM ══════════════════════════════════════════════════════════
REM  PASO 7/8: Inicializar base de datos
REM ══════════════════════════════════════════════════════════
echo.
echo  %B%══════════════════════════════════════════════════════════%N%
echo  %B%%C%[7/8]%N% %B%Inicializando base de datos...%N%
echo  %B%══════════════════════════════════════════════════════════%N%

echo    %C%⧖%N% Creando tablas...
python -c "from database import engine, Base, SessionLocal; from models import *; from migrations import run_migrations; from seed import run_seed; Base.metadata.create_all(bind=engine); run_migrations(engine); db=SessionLocal(); run_seed(db); db.close(); print('OK')" 2>nul
if %errorlevel% neq 0 (
    echo    %R%✗%N% Error al inicializar la base de datos.
    echo    %D%  Verifique que PostgreSQL esta corriendo.%N%
    set /a ERRORS+=1
    pause
    exit /b 1
)
echo    %G%✓%N% Tablas creadas.
echo    %G%✓%N% Migraciones aplicadas.
echo    %G%✓%N% Usuario '!ADMIN_USERNAME!' creado.

REM Crear directorios
if not exist "backups" mkdir backups
if not exist "static\uploads" mkdir static\uploads

REM ══════════════════════════════════════════════════════════
REM  PASO 8/8: Generar ejecutable y acceso directo
REM ══════════════════════════════════════════════════════════
echo.
echo  %B%══════════════════════════════════════════════════════════%N%
echo  %B%%C%[8/8]%N% %B%Generando ejecutable TechStock.exe...%N%
echo  %B%══════════════════════════════════════════════════════════%N%

echo    %C%⧖%N% Compilando launcher con PyInstaller...
pyinstaller launcher.py --onefile --name TechStock --noconsole --clean -y > nul 2>&1
if %errorlevel% neq 0 (
    echo    %Y%⚠%N% No se pudo generar el ejecutable.
    echo    %D%  Puede usar 'start.bat' o 'python launcher.py' para iniciar.%N%
    goto :skip_exe
)

REM Mover .exe a la raiz del proyecto
if exist "dist\TechStock.exe" (
    move /y "dist\TechStock.exe" "TechStock.exe" > nul 2>&1
    echo    %G%✓%N% TechStock.exe generado en la carpeta del proyecto.
)

REM Limpiar archivos de build
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del /q TechStock.spec 2>nul

REM Crear acceso directo en el Escritorio
echo    %C%⧖%N% Creando acceso directo en el Escritorio...
set "DESKTOP=%USERPROFILE%\Desktop"
set "EXE_PATH=%cd%\TechStock.exe"

powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%DESKTOP%\TechStock.lnk'); $s.TargetPath = '%EXE_PATH%'; $s.WorkingDirectory = '%cd%'; $s.Description = 'TechStock v2.0 - Sistema de Inventario'; $s.Save()" 2>nul

if exist "%DESKTOP%\TechStock.lnk" (
    echo    %G%✓%N% Acceso directo creado en el Escritorio.
) else (
    echo    %Y%⚠%N% No se pudo crear el acceso directo.
)

:skip_exe

REM ══════════════════════════════════════════════════════════
REM  RESUMEN FINAL
REM ══════════════════════════════════════════════════════════
echo.
echo.
if %ERRORS% equ 0 (
    echo  %G%╔═══════════════════════════════════════════════════════════╗%N%
    echo  %G%║%N%                                                           %G%║%N%
    echo  %G%║%N%   %G%✓  INSTALACION COMPLETADA EXITOSAMENTE%N%                 %G%║%N%
    echo  %G%║%N%                                                           %G%║%N%
    echo  %G%╚═══════════════════════════════════════════════════════════╝%N%
) else (
    echo  %Y%╔═══════════════════════════════════════════════════════════╗%N%
    echo  %Y%║%N%                                                           %Y%║%N%
    echo  %Y%║%N%   %Y%⚠  INSTALACION COMPLETADA CON ADVERTENCIAS%N%             %Y%║%N%
    echo  %Y%║%N%                                                           %Y%║%N%
    echo  %Y%╚═══════════════════════════════════════════════════════════╝%N%
)
echo.
echo  %B%Como iniciar TechStock:%N%
echo.
echo    %C%Opcion 1:%N%  Doble clic en %B%TechStock.exe%N% %D%(o acceso directo del Escritorio)%N%
echo    %C%Opcion 2:%N%  Ejecutar %B%start.bat%N%
echo.
echo  %B%Datos de acceso:%N%
echo.
echo    %C%URL:%N%       http://localhost:8000
echo    %C%Usuario:%N%   !ADMIN_USERNAME!
echo    %C%Nombre:%N%    !ADMIN_NAME!
echo.
echo  %D%──────────────────────────────────────────────────────────%N%
echo.

set "RESP="
set /p "RESP=  Desea iniciar TechStock ahora? (S/N): "
if /i "!RESP!"=="S" (
    if exist "TechStock.exe" (
        start "" "TechStock.exe"
    ) else (
        start "" python launcher.py
    )
)

endlocal
exit /b 0
