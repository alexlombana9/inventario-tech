"""TechStock — Centro de Control Unificado v4.0

USO INTERACTIVO:
  python quickstart.py              Menu interactivo con todas las opciones

USO POR LINEA DE COMANDOS:
  python quickstart.py --dev        Iniciar servidor de desarrollo
  python quickstart.py --install    Solo instalar dependencias
  python quickstart.py --pg         Gestionar PostgreSQL (submenu)
  python quickstart.py --build      Construir instalador .exe
  python quickstart.py --docker     Desplegar con Docker Compose
  python quickstart.py --check      Verificar requisitos del sistema
  python quickstart.py --update     Actualizar aplicacion (git pull + deps)
  python quickstart.py --status     Estado del sistema
  python quickstart.py --clean      Limpiar entorno (venv, cache, .env)
  python quickstart.py --reset      Reset completo (todo + dist + build + pgsql)
  python quickstart.py --help       Mostrar ayuda

QUE ES CADA COSA:
  quickstart.py         Este script — centro de control unificado
  launcher.py           GUI del Launcher (lo que abre el .exe instalado)
  TechStock_Setup.exe   El instalador final (instala/repara/desinstala)
"""
import os
import sys
import subprocess
import shutil
import time
import socket

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

VENV_DIR = os.path.join(BASE_DIR, "venv")
IS_WIN = sys.platform == "win32"
VENV_PYTHON = os.path.join(VENV_DIR, "Scripts", "python.exe") if IS_WIN else os.path.join(VENV_DIR, "bin", "python")
VENV_PIP = os.path.join(VENV_DIR, "Scripts", "pip.exe") if IS_WIN else os.path.join(VENV_DIR, "bin", "pip")

PG_PORT = 5433
PG_USER = "techstock"
PG_DB = "techstock"
PG_PASSWORD = "techstock"
WEB_PORT = 8000

VERSION = "4.0"

# -- Colores para terminal --
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def log(msg, level="info"):
    icons = {
        "ok": f"{GREEN}[OK]{RESET}",
        "info": f"{CYAN}[..]{RESET}",
        "warn": f"{YELLOW}[!!]{RESET}",
        "err": f"{RED}[XX]{RESET}",
        "step": f"{CYAN}[>>]{RESET}",
    }
    print(f"  {icons.get(level, icons['info'])} {msg}")


def header(msg):
    print(f"\n{BOLD}{CYAN}{'=' * 54}")
    print(f"  {msg}")
    print(f"{'=' * 54}{RESET}\n")


def banner():
    print(f"\n{BOLD}{GREEN}")
    print("  _____ _____ ____ _   _ ____ _____ ___   ____ _  __")
    print("  |_   _| ____/ ___| | | / ___|_   _/ _ \\ / ___| |/ /")
    print("    | | |  _|| |   | |_| \\___ \\ | || | | | |   | ' / ")
    print("    | | | |__| |___|  _  |___) || || |_| | |___| . \\ ")
    print("    |_| |_____\\____|_| |_|____/ |_| \\___/ \\____|_|\\_\\")
    print(f"{RESET}")


def run(cmd, check=True, capture=False, **kwargs):
    """Ejecuta un comando y retorna el resultado."""
    if capture:
        result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
        if check and result.returncode != 0:
            log(f"Comando fallo: {' '.join(cmd) if isinstance(cmd, list) else cmd}", "err")
            if result.stderr:
                for line in result.stderr.strip().split("\n")[:5]:
                    print(f"      {line}")
            return None
        return result
    return subprocess.run(cmd, check=check, **kwargs)


def port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


# ================================================================
#  MODO: DESARROLLO (default / --dev)
# ================================================================

def _deps_up_to_date(reqs_file):
    """Verifica si las dependencias estan al dia comparando mtime del requirements con un marker."""
    marker = os.path.join(VENV_DIR, ".deps_installed")
    if not os.path.exists(marker):
        return False
    try:
        marker_mtime = os.path.getmtime(marker)
        reqs_mtime = os.path.getmtime(os.path.join(BASE_DIR, reqs_file))
        # Tambien verificar requirements.txt base si es dev
        if reqs_file == "requirements-dev.txt":
            base_mtime = os.path.getmtime(os.path.join(BASE_DIR, "requirements.txt"))
            reqs_mtime = max(reqs_mtime, base_mtime)
        return marker_mtime > reqs_mtime
    except OSError:
        return False


def _mark_deps_installed():
    """Crea marker indicando que las dependencias estan al dia."""
    marker = os.path.join(VENV_DIR, ".deps_installed")
    try:
        with open(marker, "w") as f:
            f.write("")
    except OSError:
        pass


def setup_venv(dev=False):
    header("1/4  Entorno virtual")

    if os.path.exists(VENV_PYTHON):
        log("venv ya existe", "ok")
    else:
        log("Creando entorno virtual...")
        run([sys.executable, "-m", "venv", VENV_DIR])
        log("venv creado", "ok")

    reqs_file = "requirements-dev.txt" if dev else "requirements.txt"

    # Saltar pip install si no cambio el archivo de requirements
    if _deps_up_to_date(reqs_file):
        log(f"Dependencias al dia ({reqs_file})", "ok")
        return

    log(f"Instalando dependencias ({reqs_file})...")
    result = run([VENV_PIP, "install", "-r", reqs_file, "-q"], check=False, capture=True)
    if result and result.returncode == 0:
        log("Dependencias instaladas", "ok")
        _mark_deps_installed()
    else:
        log("Fallo al instalar dependencias", "err")
        if result and result.stderr:
            print(f"      {result.stderr.strip()}")
        sys.exit(1)


def setup_env():
    header("2/4  Configuracion (.env)")

    env_path = os.path.join(BASE_DIR, ".env")
    example_path = os.path.join(BASE_DIR, ".env.example")

    if os.path.exists(env_path):
        log(".env ya existe", "ok")
    elif os.path.exists(example_path):
        shutil.copy2(example_path, env_path)
        log(".env creado desde .env.example", "ok")
    else:
        with open(env_path, "w") as f:
            f.write(f"DATABASE_URL=postgresql://{PG_USER}:{PG_PASSWORD}@localhost:{PG_PORT}/{PG_DB}\n")
        log(".env creado con valores por defecto", "ok")

    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("DATABASE_URL=") and not line.startswith("#"):
                db_url = line.split("=", 1)[1]
                display = db_url.replace(PG_PASSWORD, "****") if PG_PASSWORD in db_url else db_url
                log(f"DB: {display}", "info")
                break


def _get_db_port_from_env():
    env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("DATABASE_URL=") and not line.startswith("#"):
                    url = line.split("=", 1)[1]
                    if ":" in url.split("@")[-1]:
                        port_part = url.split("@")[-1].split(":")[1].split("/")[0]
                        try:
                            return int(port_part)
                        except ValueError:
                            pass
    return PG_PORT


def check_postgres():
    header("3/4  PostgreSQL")

    configured_port = _get_db_port_from_env()

    if port_in_use(configured_port):
        log(f"PostgreSQL activo en puerto {configured_port}", "ok")
        return True

    # Verificar otros puertos conocidos
    for port in [5432, PG_PORT]:
        if port != configured_port and port_in_use(port):
            log(f"PostgreSQL detectado en puerto {port}, pero .env apunta a {configured_port}", "warn")
            log(f"Ajusta DATABASE_URL en .env para usar puerto {port}", "info")
            return False

    # Intentar auto-iniciar PG portable si esta disponible
    pg_ctl = _pg_ctl()
    if pg_ctl and os.path.exists(os.path.join(PG_DATA_DIR, "PG_VERSION")):
        log("PostgreSQL portable detectado. Iniciando automaticamente...", "info")
        os.makedirs(os.path.dirname(PG_LOG_FILE), exist_ok=True)
        run([pg_ctl, "start", "-w", "-D", PG_DATA_DIR, "-l", PG_LOG_FILE,
             "-o", f"-p {PG_PORT}"], check=False, capture=True)
        if port_in_use(PG_PORT):
            log(f"PostgreSQL iniciado en puerto {PG_PORT}", "ok")
            # Asegurar que la BD existe
            createdb = _pg_bin("createdb")
            if createdb:
                run([createdb, "-U", PG_USER, "-p", str(PG_PORT), PG_DB],
                    check=False, capture=True)
            return True
        else:
            log("No se pudo iniciar automaticamente", "warn")

    # PG portable existe pero sin datos inicializados
    if pg_ctl:
        log("PostgreSQL portable encontrado pero sin datos", "warn")
        log("Usa: python quickstart.py --pg → [3] Inicializar → [4] Iniciar", "info")
        return False

    log(f"PostgreSQL no detectado en puerto {configured_port}", "warn")
    log("Opciones:", "info")
    print(f"      a) python quickstart.py --pg    Gestionar PostgreSQL")
    print(f"      b) python quickstart.py --docker   Usar Docker")
    print(f"      c) https://www.postgresql.org/download/")
    return False


def try_connect_db():
    """Verifica conexion a PG con socket directo (rapido, sin subproceso)."""
    configured_port = _get_db_port_from_env()
    if port_in_use(configured_port):
        log("Conexion a base de datos verificada", "ok")
        return True
    log("No se pudo conectar a la base de datos", "warn")
    return False


def start_server():
    header("4/4  Iniciando TechStock")

    if port_in_use(WEB_PORT):
        log(f"Puerto {WEB_PORT} ya en uso -- el servidor puede estar corriendo", "warn")
        log(f"Abre http://localhost:{WEB_PORT}", "info")
        return

    log(f"Iniciando servidor en http://localhost:{WEB_PORT} ...")
    log("Presiona Ctrl+C para detener\n", "info")

    try:
        proc = subprocess.Popen([VENV_PYTHON, "main.py"], cwd=BASE_DIR)
        # Polling rapido: 0.3s x 50 = 15s max
        for _ in range(50):
            time.sleep(0.3)
            if port_in_use(WEB_PORT):
                log(f"Servidor listo en http://localhost:{WEB_PORT}", "ok")
                break
        else:
            log("El servidor tardo demasiado en arrancar", "warn")

        import webbrowser
        webbrowser.open(f"http://localhost:{WEB_PORT}")
        proc.wait()
    except KeyboardInterrupt:
        log("\nDeteniendo servidor...", "info")
        proc.terminate()
        proc.wait(timeout=5)
        log("Servidor detenido", "ok")


def run_dev(dev=False):
    """Modo desarrollo: venv + .env + PG + servidor."""
    v = sys.version_info
    if v < (3, 10):
        log(f"Python {v.major}.{v.minor} detectado -- se requiere 3.10+", "err")
        sys.exit(1)
    log(f"Python {v.major}.{v.minor}.{v.micro}", "ok")

    # Paso 1: venv + deps (se salta si ya esta al dia)
    setup_venv(dev=dev)

    # Paso 2: .env (se salta si ya existe)
    setup_env()

    # Paso 3: PostgreSQL (auto-inicia si es portable)
    pg_ok = check_postgres()

    # Paso 4: Servidor
    if pg_ok and try_connect_db():
        start_server()
    elif pg_ok:
        log("Verifica la configuracion de DATABASE_URL en .env", "warn")
    else:
        log("\nInicia PostgreSQL y luego ejecuta:", "info")
        print(f"      python quickstart.py --pg\n")


# ================================================================
#  MODO: DOCKER
# ================================================================

def run_docker():
    header("Docker Compose")

    docker = shutil.which("docker")
    if not docker:
        log("Docker no encontrado en PATH", "err")
        log("Instala Docker Desktop: https://www.docker.com/products/docker-desktop/", "info")
        sys.exit(1)

    compose_cmd = ["docker-compose"] if shutil.which("docker-compose") else ["docker", "compose"]

    log("Levantando contenedores...")
    run([*compose_cmd, "up", "-d", "--build"])
    log("Contenedores iniciados", "ok")

    for _ in range(30):
        time.sleep(1)
        if port_in_use(WEB_PORT):
            break

    if port_in_use(WEB_PORT):
        log(f"TechStock listo en http://localhost:{WEB_PORT}", "ok")
        import webbrowser
        webbrowser.open(f"http://localhost:{WEB_PORT}")
    else:
        log("Verifica los logs: docker-compose logs -f web", "warn")


# ================================================================
#  MODO: BUILD (construir instalador .exe)
# ================================================================

PG_VERSION = "16.8-1"
PG_ZIP = f"postgresql-{PG_VERSION}-windows-x64-binaries.zip"
PG_URL = f"https://get.enterprisedb.com/postgresql/{PG_ZIP}"

# Herramientas PG que NO se necesitan en produccion
PG_UNNECESSARY_BINS = [
    "pgbench", "pg_basebackup", "pg_dumpall",
    "pg_receivewal", "pg_recvlogical", "pg_restore",
    "pg_test_fsync", "pg_test_timing", "pg_upgrade",
    "pg_verifybackup", "pg_waldump", "pg_rewind",
    "pg_amcheck", "pg_checksums", "pg_archivecleanup",
    "vacuumdb", "reindexdb", "clusterdb", "dropuser", "ecpg",
    # NOTA: pg_dump y psql se mantienen (usados por backup/restore)
]

# Carpetas PG que NO se necesitan
PG_UNNECESSARY_DIRS = ["doc", "include", "pgAdmin 4", "StackBuilder", "symbols"]


def _find_inno_setup():
    for path in [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
    ]:
        if os.path.exists(path):
            return path
    found = shutil.which("ISCC")
    return found


def build_step_python():
    """Paso 1: Verificar Python y dependencias."""
    header("1/7  Python y dependencias")

    python = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable
    result = run([python, "--version"], capture=True, check=False)
    if not result or result.returncode != 0:
        log("Python no encontrado", "err")
        sys.exit(1)
    log(result.stdout.strip(), "ok")

    # Verificar/instalar PyInstaller
    check = run([python, "-c", "import PyInstaller"], capture=True, check=False)
    if not check or check.returncode != 0:
        log("Instalando PyInstaller...")
        pip = VENV_PIP if os.path.exists(VENV_PIP) else [python, "-m", "pip"]
        pip_cmd = [pip] if isinstance(pip, str) else pip
        run([*pip_cmd, "install", "pyinstaller", "-q"])
    ver = run([python, "-m", "PyInstaller", "--version"], capture=True, check=False)
    if ver and ver.stdout:
        log(f"PyInstaller {ver.stdout.strip()}", "ok")

    # Instalar dependencias de produccion
    log("Verificando dependencias de produccion...")
    pip = VENV_PIP if os.path.exists(VENV_PIP) else [python, "-m", "pip"]
    pip_cmd = [pip] if isinstance(pip, str) else pip
    run([*pip_cmd, "install", "-r", "requirements.txt", "-q"], check=False, capture=True)
    log("Dependencias OK", "ok")

    return python


def build_step_postgres():
    """Paso 2: Descargar y preparar PostgreSQL portable."""
    header("2/7  PostgreSQL portable")

    pg_ctl = os.path.join("pgsql", "bin", "pg_ctl.exe")

    if os.path.exists(pg_ctl):
        log("PostgreSQL portable ya existe", "ok")
        return

    if not os.path.exists(PG_ZIP):
        log(f"Descargando PostgreSQL {PG_VERSION} portable...")
        log(f"URL: {PG_URL}", "info")
        log("Esto puede tomar varios minutos...", "info")
        curl = shutil.which("curl")
        if curl:
            result = run(["curl", "-L", "-o", PG_ZIP, PG_URL], check=False)
        else:
            # Fallback con Python
            log("curl no encontrado, usando Python para descargar...", "info")
            import urllib.request
            urllib.request.urlretrieve(PG_URL, PG_ZIP)
        if not os.path.exists(PG_ZIP):
            log("No se pudo descargar PostgreSQL", "err")
            log("Descargue manualmente desde:", "info")
            print(f"      https://www.enterprisedb.com/download-postgresql-binaries")
            print(f"      Extraiga la carpeta 'pgsql' en la raiz del proyecto.")
            sys.exit(1)

    log("Extrayendo PostgreSQL...")
    result = run(["tar", "-xf", PG_ZIP, "pgsql"], check=False, capture=True)
    if not os.path.exists(pg_ctl):
        # Fallback con PowerShell
        run(["powershell", "-Command",
             f"Expand-Archive -Path '{PG_ZIP}' -DestinationPath '.' -Force"],
            check=False, capture=True)

    if not os.path.exists(pg_ctl):
        log("No se pudo extraer PostgreSQL", "err")
        sys.exit(1)

    log(f"PostgreSQL {PG_VERSION} portable listo", "ok")


def build_step_optimize_pg():
    """Paso 3: Optimizar PG portable (eliminar ~250MB innecesarios)."""
    header("3/7  Optimizar PostgreSQL")

    removed = 0
    for dirname in PG_UNNECESSARY_DIRS:
        path = os.path.join("pgsql", dirname)
        if os.path.exists(path):
            shutil.rmtree(path, ignore_errors=True)
            removed += 1

    for binname in PG_UNNECESSARY_BINS:
        path = os.path.join("pgsql", "bin", f"{binname}.exe")
        if os.path.exists(path):
            os.remove(path)
            removed += 1

    log(f"Eliminados {removed} componentes innecesarios", "ok")


def build_step_pyinstaller(python):
    """Paso 4: Ejecutar PyInstaller."""
    header("4/7  PyInstaller")

    dist_dir = os.path.join("dist", "TechStock")
    build_dir = os.path.join("build", "TechStock")

    if os.path.exists(dist_dir):
        log("Limpiando build anterior...")
        shutil.rmtree(dist_dir)
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)

    log("Construyendo distribucion (esto tarda varios minutos)...")
    result = run([python, "-m", "PyInstaller", "techstock.spec", "--noconfirm", "--clean"],
                 check=False)
    if not result or result.returncode != 0:
        log("PyInstaller fallo", "err")
        sys.exit(1)

    exe_path = os.path.join(dist_dir, "TechStock.exe")
    if not os.path.exists(exe_path):
        log(f"No se genero {exe_path}", "err")
        sys.exit(1)

    log("Build PyInstaller completado", "ok")


def build_step_copy_extras():
    """Paso 5: Copiar archivos adicionales al dist."""
    header("5/7  Archivos adicionales")

    dist_dir = os.path.join("dist", "TechStock")

    # Templates y static (backup por si PyInstaller no los incluyo)
    for folder in ["templates", "static"]:
        dest = os.path.join(dist_dir, folder)
        if not os.path.exists(dest):
            log(f"Copiando {folder}/...")
            shutil.copytree(folder, dest)

    # PostgreSQL portable
    pg_dest = os.path.join(dist_dir, "pgsql")
    if not os.path.exists(pg_dest):
        log("Copiando PostgreSQL portable...")
        shutil.copytree("pgsql", pg_dest)

    # Directorio de uploads
    avatars = os.path.join(dist_dir, "static", "uploads", "avatars")
    os.makedirs(avatars, exist_ok=True)

    # .env por defecto
    env_dist = os.path.join(dist_dir, ".env")
    if not os.path.exists(env_dist):
        with open(env_dist, "w") as f:
            f.write(f"DATABASE_URL=postgresql://{PG_USER}:{PG_PASSWORD}@localhost:{PG_PORT}/{PG_DB}\n")

    # Calcular tamano
    total = 0
    for dirpath, _, filenames in os.walk(dist_dir):
        for f in filenames:
            total += os.path.getsize(os.path.join(dirpath, f))
    log(f"Tamano del build: {total // (1024*1024)} MB", "ok")


def build_step_inno_setup():
    """Paso 6: Generar instalador con Inno Setup."""
    header("6/7  Inno Setup (instalador)")

    iscc = _find_inno_setup()

    os.makedirs(os.path.join("dist", "installer"), exist_ok=True)

    if not iscc:
        log("Inno Setup no encontrado", "warn")
        log("La version portable esta lista en: dist/TechStock/TechStock.exe", "info")
        log("Para generar el instalador .exe, instala Inno Setup 6:", "info")
        print(f"      https://jrsoftware.org/isdl.php")
        return False

    log(f"Usando: {iscc}")
    result = run([iscc, os.path.join("installer", "techstock.iss")], check=False)
    if not result or result.returncode != 0:
        log("Inno Setup fallo", "err")
        return False

    log("Instalador generado", "ok")
    return True


def build_step_summary(has_installer):
    """Paso 7: Resumen final."""
    header("7/7  Resultado")

    installer_path = os.path.join("dist", "installer", f"TechStock_Setup_v{VERSION}.exe")
    portable_path = os.path.join("dist", "TechStock", "TechStock.exe")

    if has_installer and os.path.exists(installer_path):
        size_mb = os.path.getsize(installer_path) // (1024 * 1024)
        print(f"  {GREEN}{BOLD}INSTALADOR LISTO{RESET}")
        print(f"  {installer_path}  ({size_mb} MB)\n")
        print(f"  {DIM}Ese archivo es todo lo que necesitas.{RESET}")
        print(f"  {DIM}Copialo a cualquier PC con Windows 10+ y ejecutalo.{RESET}")
        print(f"  {DIM}  - Primera vez:   instala app + PostgreSQL{RESET}")
        print(f"  {DIM}  - Ya instalado:  ofrece Reparar o Desinstalar{RESET}")
    else:
        print(f"  {YELLOW}{BOLD}VERSION PORTABLE LISTA{RESET}")
        print(f"  {portable_path}\n")
        print(f"  {DIM}Copia la carpeta dist/TechStock/ completa al PC destino.{RESET}")
        print(f"  {DIM}Ejecuta TechStock.exe para iniciar.{RESET}")

    print()


def run_build():
    """Modo build: construir instalador .exe completo."""
    if not IS_WIN:
        log("El build del instalador solo funciona en Windows", "err")
        sys.exit(1)

    if not os.path.exists("main.py"):
        log("Ejecuta este script desde la raiz del proyecto", "err")
        sys.exit(1)

    python = build_step_python()
    build_step_postgres()
    build_step_optimize_pg()
    build_step_pyinstaller(python)
    build_step_copy_extras()
    has_installer = build_step_inno_setup()
    build_step_summary(has_installer)


# ================================================================
#  POSTGRESQL
# ================================================================

# Directorio de datos de PG (mismo que launcher.py)
_APPDATA = os.environ.get("APPDATA", os.path.expanduser("~"))
PG_DATA_DIR = os.path.join(_APPDATA, "TechStock", "pgdata")
PG_LOG_FILE = os.path.join(_APPDATA, "TechStock", "pg.log")


def _pg_ctl():
    """Retorna la ruta a pg_ctl o None."""
    local = os.path.join(BASE_DIR, "pgsql", "bin", "pg_ctl.exe" if IS_WIN else "pg_ctl")
    if os.path.exists(local):
        return local
    return shutil.which("pg_ctl")


def _pg_bin(name):
    """Retorna ruta a un binario PG (psql, initdb, etc.)."""
    local = os.path.join(BASE_DIR, "pgsql", "bin", f"{name}.exe" if IS_WIN else name)
    if os.path.exists(local):
        return local
    return shutil.which(name)


def _pg_status():
    """Retorna (running, portable_exists, data_exists, port_active)."""
    pg_ctl = _pg_ctl()
    portable = os.path.exists(os.path.join(BASE_DIR, "pgsql", "bin"))
    data_exists = os.path.exists(PG_DATA_DIR)
    configured_port = _get_db_port_from_env()
    port_active = port_in_use(configured_port)
    port_5432 = port_in_use(5432) if configured_port != 5432 else False
    return {
        "pg_ctl": pg_ctl,
        "portable": portable,
        "data_exists": data_exists,
        "port": configured_port,
        "running": port_active,
        "running_5432": port_5432,
    }


def pg_show_status():
    """Muestra el estado actual de PostgreSQL."""
    s = _pg_status()
    print(f"\n  {BOLD}Estado de PostgreSQL:{RESET}\n")

    # Instalacion
    if s["portable"]:
        pg_ctl = _pg_ctl()
        ver = None
        if pg_ctl:
            r = subprocess.run([pg_ctl, "--version"], capture_output=True, text=True)
            if r.returncode == 0:
                ver = r.stdout.strip().split()[-1]
        log(f"Instalacion: PostgreSQL portable {ver or ''} (pgsql/)", "ok")
    elif shutil.which("pg_ctl"):
        log("Instalacion: PostgreSQL del sistema (en PATH)", "ok")
    else:
        log("Instalacion: NO encontrado", "err")
        log(f"  Descarga: https://www.postgresql.org/download/", "info")
        log(f"  O usa la opcion [2] para descargar la version portable", "info")

    # Datos
    if s["data_exists"]:
        log(f"Datos: {PG_DATA_DIR}", "ok")
    else:
        log(f"Datos: no inicializado", "info")
        log(f"  Ruta esperada: {PG_DATA_DIR}", "info")

    # Servicio
    if s["running"]:
        log(f"Servicio: ACTIVO en puerto {s['port']}", "ok")
    elif s["running_5432"]:
        log(f"Servicio: ACTIVO en puerto 5432 (configurado: {s['port']})", "warn")
        log(f"  Ajusta DATABASE_URL en .env o inicia PG en puerto {s['port']}", "info")
    else:
        log(f"Servicio: DETENIDO (puerto {s['port']} libre)", "warn")

    # Conexion a BD
    env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.strip().startswith("DATABASE_URL=") and not line.strip().startswith("#"):
                    raw = line.strip().split("=", 1)[1]
                    if "@" in raw and ":" in raw.split("@")[0]:
                        masked = raw.split("@")[0].rsplit(":", 1)[0] + ":****@" + raw.split("@", 1)[1]
                    else:
                        masked = raw
                    log(f"DATABASE_URL: {masked}", "info")
                    break
    print()


def pg_download():
    """Descarga PostgreSQL portable (reutiliza build_step_postgres)."""
    header("Descargar PostgreSQL Portable")

    pg_ctl = os.path.join("pgsql", "bin", "pg_ctl.exe" if IS_WIN else "pg_ctl")
    if os.path.exists(pg_ctl):
        log("PostgreSQL portable ya esta descargado en pgsql/", "ok")
        return True

    log(f"Se descargara PostgreSQL {PG_VERSION} portable (~330 MB)", "info")
    log(f"URL: {PG_URL}", "info")
    print()

    try:
        resp = input("  Continuar? [S/n]: ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        return False
    if resp in ("n", "no"):
        return False

    build_step_postgres()
    build_step_optimize_pg()
    log("PostgreSQL portable listo en pgsql/", "ok")
    return True


def pg_init():
    """Inicializa el directorio de datos de PostgreSQL."""
    header("Inicializar Base de Datos")

    pg_ctl = _pg_ctl()
    if not pg_ctl:
        log("pg_ctl no encontrado. Descarga PostgreSQL primero (opcion 2)", "err")
        return False

    if os.path.exists(os.path.join(PG_DATA_DIR, "PG_VERSION")):
        log(f"Datos ya inicializados en {PG_DATA_DIR}", "ok")
        return True

    initdb = _pg_bin("initdb")
    if not initdb:
        log("initdb no encontrado", "err")
        return False

    os.makedirs(PG_DATA_DIR, exist_ok=True)
    log(f"Inicializando datos en {PG_DATA_DIR}...")
    result = run([initdb, "-D", PG_DATA_DIR, "-U", PG_USER, "-E", "UTF8", "--locale=C"],
                 check=False, capture=True)
    if result and result.returncode == 0:
        log("Base de datos inicializada", "ok")
        return True
    else:
        log("Error al inicializar. Revisa los permisos de la carpeta", "err")
        if result and result.stderr:
            for line in result.stderr.strip().split("\n")[:3]:
                print(f"      {line}")
        return False


def pg_start():
    """Inicia el servicio de PostgreSQL."""
    header("Iniciar PostgreSQL")

    s = _pg_status()
    if s["running"]:
        log(f"PostgreSQL ya esta corriendo en puerto {s['port']}", "ok")
        return True

    pg_ctl = _pg_ctl()
    if not pg_ctl:
        log("pg_ctl no encontrado. Descarga PostgreSQL primero", "err")
        return False

    if not os.path.exists(os.path.join(PG_DATA_DIR, "PG_VERSION")):
        log("Datos no inicializados. Ejecuta primero 'Inicializar base de datos'", "warn")
        return False

    os.makedirs(os.path.dirname(PG_LOG_FILE), exist_ok=True)
    log(f"Iniciando PostgreSQL en puerto {PG_PORT}...")
    # -w: pg_ctl espera a que PG este listo (sin polling manual)
    result = run([pg_ctl, "start", "-w", "-D", PG_DATA_DIR, "-l", PG_LOG_FILE,
                  "-o", f"-p {PG_PORT}"],
                 check=False, capture=True)

    if port_in_use(PG_PORT):
        log(f"PostgreSQL activo en puerto {PG_PORT}", "ok")

        # Crear usuario y BD si no existen
        createuser = _pg_bin("createuser")
        createdb = _pg_bin("createdb")
        psql = _pg_bin("psql")

        if createuser:
            run([createuser, "-U", PG_USER, "-p", str(PG_PORT), PG_USER],
                check=False, capture=True)
        if createdb:
            run([createdb, "-U", PG_USER, "-p", str(PG_PORT), PG_DB],
                check=False, capture=True)

        log(f"Base de datos '{PG_DB}' lista", "ok")
        return True
    else:
        log("PostgreSQL no arranco. Revisa el log:", "err")
        log(f"  {PG_LOG_FILE}", "info")
        if os.path.exists(PG_LOG_FILE):
            try:
                with open(PG_LOG_FILE, encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                    for line in lines[-5:]:
                        print(f"      {line.rstrip()}")
            except Exception:
                pass
        return False


def pg_stop():
    """Detiene el servicio de PostgreSQL."""
    header("Detener PostgreSQL")

    s = _pg_status()
    if not s["running"] and not s["running_5432"]:
        log("PostgreSQL no esta corriendo", "info")
        return True

    pg_ctl = _pg_ctl()
    if not pg_ctl:
        log("pg_ctl no encontrado. Detiene PostgreSQL manualmente", "err")
        return False

    log("Deteniendo PostgreSQL...")
    # -w: pg_ctl espera a que PG se detenga completamente
    result = run([pg_ctl, "stop", "-w", "-D", PG_DATA_DIR, "-m", "fast"],
                 check=False, capture=True)

    if not port_in_use(s["port"]):
        log("PostgreSQL detenido", "ok")
        return True
    else:
        log("No se pudo detener. Intenta manualmente", "warn")
        return False


def pg_restart():
    """Reinicia PostgreSQL."""
    header("Reiniciar PostgreSQL")
    pg_ctl = _pg_ctl()
    if not pg_ctl:
        log("pg_ctl no encontrado", "err")
        return
    log("Reiniciando PostgreSQL...")
    result = run([pg_ctl, "restart", "-w", "-D", PG_DATA_DIR, "-l", PG_LOG_FILE,
                  "-o", f"-p {PG_PORT}", "-m", "fast"],
                 check=False, capture=True)
    if port_in_use(PG_PORT):
        log(f"PostgreSQL reiniciado en puerto {PG_PORT}", "ok")
    else:
        log("Error al reiniciar. Revisa el log", "err")


def run_postgres():
    """Submenu de gestion de PostgreSQL."""
    while True:
        s = _pg_status()

        # Indicador de estado
        if s["running"]:
            estado = f"{GREEN}ACTIVO{RESET} (puerto {s['port']})"
        elif s["running_5432"]:
            estado = f"{YELLOW}ACTIVO en 5432{RESET} (configurado: {s['port']})"
        else:
            estado = f"{RED}DETENIDO{RESET}"

        print(f"\n{BOLD}{CYAN}{'=' * 54}")
        print(f"  PostgreSQL -- Gestion de Base de Datos")
        print(f"{'=' * 54}{RESET}")
        print(f"\n  Estado: {estado}")

        if s["portable"]:
            print(f"  Tipo:   PostgreSQL portable (pgsql/)")
        elif shutil.which("pg_ctl"):
            print(f"  Tipo:   PostgreSQL del sistema")
        else:
            print(f"  Tipo:   {RED}No instalado{RESET}")

        if s["data_exists"]:
            print(f"  Datos:  {PG_DATA_DIR}")
        else:
            print(f"  Datos:  {YELLOW}No inicializado{RESET}")

        print()
        print(f"    {GREEN}[1]{RESET}  Ver estado detallado")

        if not s["portable"] and not shutil.which("pg_ctl"):
            print(f"    {GREEN}[2]{RESET}  Descargar PostgreSQL portable")
        elif s["portable"] and not shutil.which("pg_ctl"):
            print(f"    {DIM}[2]  PostgreSQL portable ya descargado{RESET}")

        if not s["data_exists"] and (s["portable"] or shutil.which("pg_ctl")):
            print(f"    {GREEN}[3]{RESET}  Inicializar base de datos")
        elif s["data_exists"]:
            print(f"    {DIM}[3]  Datos ya inicializados{RESET}")

        if not s["running"] and s["data_exists"]:
            print(f"    {GREEN}[4]{RESET}  Iniciar PostgreSQL")
        elif s["running"]:
            print(f"    {DIM}[4]  PostgreSQL ya esta corriendo{RESET}")

        if s["running"]:
            print(f"    {GREEN}[5]{RESET}  Detener PostgreSQL")
            print(f"    {GREEN}[6]{RESET}  Reiniciar PostgreSQL")

        print(f"    {GREEN}[7]{RESET}  Configurar conexion (.env)")
        print()

        if not s["portable"] and not shutil.which("pg_ctl"):
            print(f"  {DIM}INICIO RAPIDO: [2] Descargar → [3] Inicializar → [4] Iniciar{RESET}")
        elif not s["data_exists"]:
            print(f"  {DIM}INICIO RAPIDO: [3] Inicializar → [4] Iniciar{RESET}")
        elif not s["running"]:
            print(f"  {DIM}INICIO RAPIDO: [4] Iniciar{RESET}")

        print()
        print(f"    {DIM}[0]  Volver al menu principal{RESET}")
        print()

        try:
            choice = input(f"  Seleccione una opcion: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print()
            break

        if choice == "0" or choice in ("q", "quit", "back", "volver"):
            break
        elif choice == "1":
            pg_show_status()
        elif choice == "2":
            if not s["portable"] and not shutil.which("pg_ctl"):
                pg_download()
            else:
                log("PostgreSQL ya esta disponible", "ok")
        elif choice == "3":
            if not s["data_exists"]:
                if pg_init():
                    log("Ahora puedes iniciar PostgreSQL con la opcion [4]", "info")
            else:
                log("Datos ya inicializados", "ok")
        elif choice == "4":
            if not s["running"]:
                pg_start()
            else:
                log("PostgreSQL ya esta corriendo", "ok")
        elif choice == "5":
            if s["running"]:
                pg_stop()
            else:
                log("PostgreSQL no esta corriendo", "info")
        elif choice == "6":
            if s["running"]:
                pg_restart()
            else:
                log("PostgreSQL no esta corriendo. Usa [4] para iniciar", "info")
        elif choice == "7":
            pg_configure_env()
        elif choice == "":
            continue
        else:
            log(f"Opcion no valida: {choice}", "warn")
            continue

        if choice not in ("0", "q", ""):
            print()
            try:
                input(f"  Presione Enter para continuar...")
            except (KeyboardInterrupt, EOFError):
                print()
                break


def pg_configure_env():
    """Configurar la conexion a PostgreSQL en .env."""
    header("Configurar Conexion (.env)")

    env_path = os.path.join(BASE_DIR, ".env")

    print(f"  {BOLD}Configuracion actual:{RESET}")
    current_url = None
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.strip().startswith("DATABASE_URL=") and not line.strip().startswith("#"):
                    current_url = line.strip().split("=", 1)[1]
                    break

    if current_url:
        log(f"DATABASE_URL={current_url}", "info")
    else:
        log("DATABASE_URL no configurada", "warn")

    print(f"\n  {BOLD}Opciones:{RESET}")
    print(f"    {GREEN}[1]{RESET}  PG portable local (puerto {PG_PORT})")
    print(f"        postgresql://{PG_USER}:{PG_PASSWORD}@localhost:{PG_PORT}/{PG_DB}")
    print(f"    {GREEN}[2]{RESET}  PG sistema (puerto 5432)")
    print(f"        postgresql://{PG_USER}:{PG_PASSWORD}@localhost:5432/{PG_DB}")
    print(f"    {GREEN}[3]{RESET}  Personalizada (ingresar URL manualmente)")
    print(f"    {GREEN}[0]{RESET}  Cancelar")
    print()

    try:
        opt = input("  Seleccione: ").strip()
    except (KeyboardInterrupt, EOFError):
        return

    new_url = None
    if opt == "1":
        new_url = f"postgresql://{PG_USER}:{PG_PASSWORD}@localhost:{PG_PORT}/{PG_DB}"
    elif opt == "2":
        new_url = f"postgresql://{PG_USER}:{PG_PASSWORD}@localhost:5432/{PG_DB}"
    elif opt == "3":
        try:
            new_url = input("  DATABASE_URL: ").strip()
        except (KeyboardInterrupt, EOFError):
            return
        if not new_url:
            log("URL vacia, cancelado", "warn")
            return
    elif opt == "0":
        return
    else:
        log("Opcion no valida", "warn")
        return

    # Actualizar .env
    if os.path.exists(env_path):
        with open(env_path) as f:
            content = f.read()

        import re
        if re.search(r'^DATABASE_URL=', content, re.MULTILINE):
            content = re.sub(r'^DATABASE_URL=.*$', f'DATABASE_URL={new_url}', content, flags=re.MULTILINE)
        else:
            content = f"DATABASE_URL={new_url}\n" + content

        with open(env_path, "w") as f:
            f.write(content)
    else:
        with open(env_path, "w") as f:
            f.write(f"DATABASE_URL={new_url}\n")

    log(f"DATABASE_URL actualizada en .env", "ok")
    log(f"  {new_url}", "info")


# ================================================================
#  NUEVAS FUNCIONES
# ================================================================

def run_install():
    """Opcion 2: Solo instalar dependencias."""
    header("Instalar / Actualizar Dependencias")

    v = sys.version_info
    if v < (3, 10):
        log(f"Python {v.major}.{v.minor} detectado -- se requiere 3.10+", "err")
        return
    log(f"Python {v.major}.{v.minor}.{v.micro}", "ok")

    # Crear venv si no existe
    if os.path.exists(VENV_PYTHON):
        log("venv ya existe", "ok")
    else:
        log("Creando entorno virtual...")
        run([sys.executable, "-m", "venv", VENV_DIR])
        log("venv creado", "ok")

    # Preguntar tipo de dependencias
    print()
    print(f"  {BOLD}Tipo de dependencias:{RESET}")
    print(f"    [1] Produccion (requirements.txt)")
    print(f"    [2] Desarrollo (requirements-dev.txt) — incluye pytest, httpx, coverage")
    print()
    choice = input(f"  Seleccione [1/2] (default: 1): ").strip()

    if choice == "2":
        reqs_file = "requirements-dev.txt"
    else:
        reqs_file = "requirements.txt"

    if not os.path.exists(reqs_file):
        log(f"Archivo {reqs_file} no encontrado", "err")
        return

    log(f"Instalando dependencias ({reqs_file})...")
    result = run([VENV_PIP, "install", "-r", reqs_file, "-q"], check=False, capture=True)
    if result and result.returncode == 0:
        log("Dependencias instaladas correctamente", "ok")
    else:
        log("Fallo al instalar dependencias", "err")
        if result and result.stderr:
            for line in result.stderr.strip().split("\n")[:5]:
                print(f"      {line}")

    # Mostrar paquetes instalados
    result = run([VENV_PIP, "list", "--format=columns"], check=False, capture=True)
    if result and result.stdout:
        lines = result.stdout.strip().split("\n")
        log(f"{len(lines) - 2} paquetes instalados en el entorno", "ok")


def _check_tool(name, check_fn, version_fn=None):
    """Verifica si una herramienta esta disponible.

    Args:
        name: Nombre de la herramienta
        check_fn: Funcion que retorna True/False si esta disponible
        version_fn: Funcion que retorna la version como string, o None

    Returns:
        (disponible: bool, version: str o None)
    """
    try:
        available = check_fn()
    except Exception:
        available = False

    version = None
    if available and version_fn:
        try:
            version = version_fn()
        except Exception:
            version = "detectado"

    return available, version


def run_check():
    """Opcion 5: Verificar requisitos del sistema."""
    header("Requisitos del Sistema")

    results = []

    # --- REQUERIDO ---
    results.append(("section", "REQUERIDO"))

    # Python
    v = sys.version_info
    py_ok = v >= (3, 10)
    py_ver = f"{v.major}.{v.minor}.{v.micro}"
    results.append(("tool", "Python 3.10+", py_ok, py_ver if py_ok else f"{py_ver} (se requiere 3.10+)",
                     "https://www.python.org/downloads/"))

    # pip
    pip_path = shutil.which("pip") or shutil.which("pip3")
    pip_ver = None
    if pip_path:
        r = subprocess.run([pip_path, "--version"], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout:
            # "pip 24.0 from ..."
            parts = r.stdout.strip().split()
            if len(parts) >= 2:
                pip_ver = parts[1]
    results.append(("tool", "pip", pip_path is not None, pip_ver,
                     "Incluido con Python"))

    # --- PARA DESARROLLO ---
    results.append(("section", "PARA DESARROLLO"))

    # PostgreSQL
    pg_available = False
    pg_ver = None
    pg_detail = ""

    # Verificar pg_ctl en PATH
    pg_ctl_path = shutil.which("pg_ctl")
    # Verificar PG portable local
    pg_ctl_local = os.path.join(BASE_DIR, "pgsql", "bin", "pg_ctl.exe" if IS_WIN else "pg_ctl")
    pg_ctl_any = pg_ctl_path or (pg_ctl_local if os.path.exists(pg_ctl_local) else None)

    if pg_ctl_any:
        r = subprocess.run([pg_ctl_any, "--version"], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout:
            # "pg_ctl (PostgreSQL) 16.x"
            pg_ver = r.stdout.strip().split()[-1] if r.stdout.strip() else None
            pg_available = True

    # Verificar si hay alguna instancia corriendo
    configured_port = _get_db_port_from_env()
    pg_running = port_in_use(configured_port)
    pg_running_5432 = port_in_use(5432) if configured_port != 5432 else False

    if pg_running:
        pg_detail = f"activo en puerto {configured_port}"
        pg_available = True
    elif pg_running_5432:
        pg_detail = f"activo en puerto 5432"
        pg_available = True
    elif pg_available:
        pg_detail = f"instalado (no activo)"

    pg_display = pg_ver if pg_ver else pg_detail if pg_detail else None
    if pg_ver and pg_detail:
        pg_display = f"{pg_ver} ({pg_detail})"

    results.append(("tool", "PostgreSQL", pg_available, pg_display,
                     "https://www.postgresql.org/download/"))

    # --- PARA BUILD DEL INSTALADOR ---
    results.append(("section", "PARA BUILD DEL INSTALADOR"))

    # PyInstaller
    pi_ok = False
    pi_ver = None
    python_exe = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable
    r = subprocess.run([python_exe, "-c", "import PyInstaller; print(PyInstaller.__version__)"],
                       capture_output=True, text=True)
    if r.returncode == 0 and r.stdout:
        pi_ok = True
        pi_ver = r.stdout.strip()
    results.append(("tool", "PyInstaller", pi_ok, pi_ver,
                     "pip install pyinstaller"))

    # Inno Setup
    iscc = _find_inno_setup()
    inno_ver = None
    if iscc:
        r = subprocess.run([iscc, "/?"], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout:
            # Primera linea suele tener la version
            first_line = r.stdout.strip().split("\n")[0]
            if "Inno Setup" in first_line:
                inno_ver = first_line.strip()
            else:
                inno_ver = "detectado"
        else:
            inno_ver = "detectado"
    results.append(("tool", "Inno Setup 6", iscc is not None, inno_ver,
                     "https://jrsoftware.org/isdl.php"))

    # --- PARA DOCKER ---
    results.append(("section", "PARA DOCKER"))

    # Docker
    docker_path = shutil.which("docker")
    docker_ver = None
    if docker_path:
        r = subprocess.run([docker_path, "--version"], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout:
            # "Docker version 24.0.x, ..."
            docker_ver = r.stdout.strip().split(",")[0].replace("Docker version ", "")
    results.append(("tool", "Docker", docker_path is not None, docker_ver,
                     "https://www.docker.com/products/docker-desktop/"))

    # Docker Compose
    dc_ok = False
    dc_ver = None
    if shutil.which("docker-compose"):
        dc_ok = True
        r = subprocess.run(["docker-compose", "--version"], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout:
            dc_ver = r.stdout.strip().split(",")[0].replace("docker-compose version ", "").replace("Docker Compose version ", "")
    elif docker_path:
        r = subprocess.run(["docker", "compose", "version"], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout:
            dc_ok = True
            dc_ver = r.stdout.strip().replace("Docker Compose version ", "")
    results.append(("tool", "Docker Compose", dc_ok, dc_ver,
                     "Incluido con Docker Desktop"))

    # --- OPCIONAL ---
    results.append(("section", "OPCIONAL"))

    # Git
    git_path = shutil.which("git")
    git_ver = None
    if git_path:
        r = subprocess.run([git_path, "--version"], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout:
            git_ver = r.stdout.strip().replace("git version ", "")
    results.append(("tool", "Git", git_path is not None, git_ver,
                     "https://git-scm.com/downloads"))

    # curl
    curl_path = shutil.which("curl")
    curl_ver = None
    if curl_path:
        r = subprocess.run([curl_path, "--version"], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout:
            first_line = r.stdout.strip().split("\n")[0]
            # "curl 8.x.x ..."
            parts = first_line.split()
            if len(parts) >= 2:
                curl_ver = parts[1]
    results.append(("tool", "curl", curl_path is not None, curl_ver,
                     "Incluido con Windows 10+"))

    # --- Mostrar resultados ---
    for item in results:
        if item[0] == "section":
            print(f"\n  {BOLD}{item[1]}:{RESET}")
        else:
            _, name, ok, ver, url = item
            if ok:
                ver_display = f"  {DIM}{ver}{RESET}" if ver else ""
                print(f"  {GREEN}[OK]{RESET} {name}{ver_display}")
            else:
                print(f"  {YELLOW}[!!]{RESET} {name} no detectado          {DIM}{url}{RESET}")

    print()

    # Resumen
    tools = [item for item in results if item[0] == "tool"]
    ok_count = sum(1 for t in tools if t[2])
    total_count = len(tools)
    if ok_count == total_count:
        log(f"Todos los requisitos cumplidos ({ok_count}/{total_count})", "ok")
    else:
        missing = total_count - ok_count
        log(f"{ok_count}/{total_count} requisitos cumplidos, {missing} faltante(s)", "warn")


def run_update():
    """Opcion 6: Actualizar aplicacion desde git."""
    header("Actualizar Aplicacion")

    # Verificar Git
    git_path = shutil.which("git")
    if not git_path:
        log("Git no encontrado en PATH", "err")
        log("Instala Git: https://git-scm.com/downloads", "info")
        return

    # Verificar que es un repositorio git
    if not os.path.exists(os.path.join(BASE_DIR, ".git")):
        log("Este directorio no es un repositorio Git", "err")
        return

    # Verificar cambios locales
    result = run([git_path, "status", "--porcelain"], capture=True, check=False)
    if result and result.stdout and result.stdout.strip():
        log("Hay cambios locales sin commitear:", "warn")
        for line in result.stdout.strip().split("\n")[:10]:
            print(f"      {line}")
        print()
        confirm = input(f"  Continuar de todos modos? [s/N]: ").strip().lower()
        if confirm not in ("s", "si", "y", "yes"):
            log("Actualizacion cancelada", "info")
            return

    # Git pull
    log("Descargando actualizaciones...")
    result = run([git_path, "pull", "origin", "main"], capture=True, check=False)
    if result:
        if result.returncode == 0:
            output = result.stdout.strip() if result.stdout else ""
            if "Already up to date" in output or "Already up-to-date" in output:
                log("Ya esta actualizado, no hay cambios nuevos", "ok")
            else:
                log("Codigo actualizado", "ok")
                if output:
                    for line in output.split("\n")[:15]:
                        print(f"      {line}")
        else:
            log("Fallo al ejecutar git pull", "err")
            if result.stderr:
                for line in result.stderr.strip().split("\n")[:5]:
                    print(f"      {line}")
            return

    # Reinstalar dependencias
    if os.path.exists(VENV_PYTHON):
        log("Actualizando dependencias...")
        reqs = "requirements-dev.txt" if os.path.exists(os.path.join(BASE_DIR, "requirements-dev.txt")) else "requirements.txt"
        r = run([VENV_PIP, "install", "-r", reqs, "-q"], check=False, capture=True)
        if r and r.returncode == 0:
            log("Dependencias actualizadas", "ok")
        else:
            log("Error actualizando dependencias", "warn")
    else:
        log("No hay venv. Ejecuta la opcion 2 para instalar dependencias", "warn")

    # Mostrar resumen
    print()
    result = run([git_path, "log", "--oneline", "-5"], capture=True, check=False)
    if result and result.stdout:
        log("Ultimos commits:", "info")
        for line in result.stdout.strip().split("\n"):
            print(f"      {line}")
    print()


def run_status():
    """Opcion 7: Estado del sistema."""
    header("Estado del Sistema")

    # Python
    v = sys.version_info
    log(f"Python: {v.major}.{v.minor}.{v.micro} ({sys.executable})", "ok")

    # venv
    if os.path.exists(VENV_PYTHON):
        r = subprocess.run([VENV_PYTHON, "--version"], capture_output=True, text=True)
        venv_ver = r.stdout.strip() if r.returncode == 0 else "desconocido"
        log(f"venv: {venv_ver} ({VENV_DIR})", "ok")
    else:
        log("venv: no existe", "warn")

    # .env
    env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path):
        db_url_display = None
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("DATABASE_URL=") and not line.startswith("#"):
                    raw_url = line.split("=", 1)[1]
                    # Enmascarar password
                    if "@" in raw_url:
                        pre_at = raw_url.split("@")[0]
                        post_at = raw_url.split("@", 1)[1]
                        if ":" in pre_at:
                            scheme_user = pre_at.rsplit(":", 1)[0]
                            db_url_display = f"{scheme_user}:****@{post_at}"
                        else:
                            db_url_display = raw_url
                    else:
                        db_url_display = raw_url
                    break
        if db_url_display:
            log(f".env: DATABASE_URL={db_url_display}", "ok")
        else:
            log(".env: existe (sin DATABASE_URL)", "ok")
    else:
        log(".env: no existe", "warn")

    # PostgreSQL
    configured_port = _get_db_port_from_env()
    if port_in_use(configured_port):
        log(f"PostgreSQL: activo en puerto {configured_port}", "ok")
    elif port_in_use(5432):
        log(f"PostgreSQL: activo en puerto 5432 (configurado: {configured_port})", "warn")
    else:
        log(f"PostgreSQL: no detectado en puerto {configured_port}", "warn")

    # Servidor web
    if port_in_use(WEB_PORT):
        log(f"Servidor web: activo en http://localhost:{WEB_PORT}", "ok")
    else:
        log(f"Servidor web: no activo (puerto {WEB_PORT} libre)", "info")

    # PG portable
    pg_ctl_local = os.path.join(BASE_DIR, "pgsql", "bin", "pg_ctl.exe" if IS_WIN else "pg_ctl")
    if os.path.exists(pg_ctl_local):
        log("PostgreSQL portable: presente en pgsql/", "ok")
    else:
        log("PostgreSQL portable: no descargado", "info")

    # dist/
    dist_dir = os.path.join(BASE_DIR, "dist")
    if os.path.exists(dist_dir):
        # Calcular tamano
        total = 0
        file_count = 0
        for dirpath, _, filenames in os.walk(dist_dir):
            for f in filenames:
                total += os.path.getsize(os.path.join(dirpath, f))
                file_count += 1
        log(f"dist/: {file_count} archivos, {total // (1024*1024)} MB", "ok")

        installer_path = os.path.join(dist_dir, "installer", f"TechStock_Setup_v{VERSION}.exe")
        if os.path.exists(installer_path):
            size_mb = os.path.getsize(installer_path) // (1024 * 1024)
            log(f"Instalador: TechStock_Setup_v{VERSION}.exe ({size_mb} MB)", "ok")
    else:
        log("dist/: no existe (no se ha hecho build)", "info")

    # Espacio en disco
    if IS_WIN:
        try:
            import ctypes
            free_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                BASE_DIR, None, None, ctypes.pointer(free_bytes))
            free_gb = free_bytes.value / (1024 ** 3)
            log(f"Espacio libre en disco: {free_gb:.1f} GB", "ok" if free_gb > 5 else "warn")
        except Exception:
            pass
    else:
        try:
            st = os.statvfs(BASE_DIR)
            free_gb = (st.f_bavail * st.f_frsize) / (1024 ** 3)
            log(f"Espacio libre en disco: {free_gb:.1f} GB", "ok" if free_gb > 5 else "warn")
        except Exception:
            pass

    # Archivos clave: ultima modificacion
    print(f"\n  {BOLD}Ultima modificacion de archivos clave:{RESET}")
    key_files = [
        "main.py", "models.py", "auth.py", "middleware.py", "database.py",
        "requirements.txt", "migrations.py", "seed.py"
    ]
    for fname in key_files:
        fpath = os.path.join(BASE_DIR, fname)
        if os.path.exists(fpath):
            mtime = os.path.getmtime(fpath)
            mtime_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime))
            print(f"    {DIM}{mtime_str}{RESET}  {fname}")

    # Git info
    git_path = shutil.which("git")
    if git_path and os.path.exists(os.path.join(BASE_DIR, ".git")):
        print(f"\n  {BOLD}Git:{RESET}")
        r = subprocess.run([git_path, "branch", "--show-current"], capture_output=True, text=True, cwd=BASE_DIR)
        if r.returncode == 0 and r.stdout:
            print(f"    Branch: {r.stdout.strip()}")
        r = subprocess.run([git_path, "log", "--oneline", "-3"], capture_output=True, text=True, cwd=BASE_DIR)
        if r.returncode == 0 and r.stdout:
            for line in r.stdout.strip().split("\n"):
                print(f"    {DIM}{line}{RESET}")

    print()


def run_clean():
    """Opcion 8: Limpiar entorno (venv, cache, .env)."""
    header("Limpiar Entorno")

    # Mostrar que se va a eliminar
    items_to_clean = []
    if os.path.exists(VENV_DIR):
        items_to_clean.append(("venv/", VENV_DIR))
    env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path):
        items_to_clean.append((".env", env_path))

    # Buscar __pycache__
    pycache_count = 0
    for dirpath, dirnames, _ in os.walk(BASE_DIR):
        # No entrar en venv, dist, build, pgsql, .git
        dirnames[:] = [d for d in dirnames if d not in ("venv", "dist", "build", "pgsql", ".git", "node_modules")]
        if "__pycache__" in dirnames:
            pycache_count += 1

    pytest_cache = os.path.join(BASE_DIR, ".pytest_cache")
    htmlcov = os.path.join(BASE_DIR, "htmlcov")
    coverage_file = os.path.join(BASE_DIR, ".coverage")

    if pycache_count > 0:
        items_to_clean.append((f"__pycache__/ ({pycache_count} directorios)", None))
    if os.path.exists(pytest_cache):
        items_to_clean.append((".pytest_cache/", pytest_cache))
    if os.path.exists(htmlcov):
        items_to_clean.append(("htmlcov/", htmlcov))
    if os.path.exists(coverage_file):
        items_to_clean.append((".coverage", coverage_file))

    if not items_to_clean:
        log("No hay nada que limpiar", "ok")
        return

    print(f"  {BOLD}Se eliminara:{RESET}")
    for name, _ in items_to_clean:
        print(f"    {YELLOW}-{RESET} {name}")
    print()

    confirm = input(f"  Confirmar limpieza? [s/N]: ").strip().lower()
    if confirm not in ("s", "si", "y", "yes"):
        log("Limpieza cancelada", "info")
        return

    # Ejecutar limpieza
    if os.path.exists(VENV_DIR):
        log("Eliminando venv...")
        shutil.rmtree(VENV_DIR, ignore_errors=True)
        log("venv eliminado", "ok")

    if os.path.exists(env_path):
        log("Eliminando .env...")
        os.remove(env_path)
        log(".env eliminado", "ok")

    # Eliminar __pycache__ recursivamente
    if pycache_count > 0:
        log("Eliminando __pycache__...")
        removed = 0
        for dirpath, dirnames, _ in os.walk(BASE_DIR):
            dirnames[:] = [d for d in dirnames if d not in ("venv", "dist", "build", "pgsql", ".git", "node_modules")]
            for d in dirnames:
                if d == "__pycache__":
                    full = os.path.join(dirpath, d)
                    shutil.rmtree(full, ignore_errors=True)
                    removed += 1
        log(f"{removed} directorios __pycache__ eliminados", "ok")

    if os.path.exists(pytest_cache):
        log("Eliminando .pytest_cache...")
        shutil.rmtree(pytest_cache, ignore_errors=True)
        log(".pytest_cache eliminado", "ok")

    if os.path.exists(htmlcov):
        log("Eliminando htmlcov...")
        shutil.rmtree(htmlcov, ignore_errors=True)
        log("htmlcov eliminado", "ok")

    if os.path.exists(coverage_file):
        log("Eliminando .coverage...")
        os.remove(coverage_file)
        log(".coverage eliminado", "ok")

    print()
    log("Limpieza completada. Ejecuta la opcion 2 para reinstalar.", "ok")


def run_reset():
    """Opcion 9: Reset completo (todo + dist + build + pgsql)."""
    header("Reset Completo")

    # Mostrar que se va a eliminar
    items = []
    if os.path.exists(VENV_DIR):
        items.append("venv/")
    env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path):
        items.append(".env")

    # Caches
    for dirpath, dirnames, _ in os.walk(BASE_DIR):
        dirnames[:] = [d for d in dirnames if d not in ("venv", "dist", "build", "pgsql", ".git", "node_modules")]
        if "__pycache__" in dirnames:
            items.append("__pycache__/ (multiples)")
            break
    pytest_cache = os.path.join(BASE_DIR, ".pytest_cache")
    htmlcov = os.path.join(BASE_DIR, "htmlcov")
    coverage_file = os.path.join(BASE_DIR, ".coverage")
    if os.path.exists(pytest_cache):
        items.append(".pytest_cache/")
    if os.path.exists(htmlcov):
        items.append("htmlcov/")
    if os.path.exists(coverage_file):
        items.append(".coverage")

    # Build artifacts
    dist_dir = os.path.join(BASE_DIR, "dist")
    build_dir = os.path.join(BASE_DIR, "build")
    pgsql_dir = os.path.join(BASE_DIR, "pgsql")
    if os.path.exists(dist_dir):
        items.append("dist/")
    if os.path.exists(build_dir):
        items.append("build/")
    if os.path.exists(pgsql_dir):
        items.append("pgsql/ (PostgreSQL portable)")

    # Archivos zip de PG
    pg_zips = [f for f in os.listdir(BASE_DIR) if f.startswith("postgresql-") and f.endswith(".zip")]
    for z in pg_zips:
        items.append(z)

    if not items:
        log("No hay nada que resetear", "ok")
        return

    print(f"  {RED}{BOLD}ATENCION: Esta operacion eliminara todo lo siguiente:{RESET}")
    for name in items:
        print(f"    {RED}-{RESET} {name}")
    print()

    confirm1 = input(f"  Confirmar reset completo? [s/N]: ").strip().lower()
    if confirm1 not in ("s", "si", "y", "yes"):
        log("Reset cancelado", "info")
        return

    confirm2 = input(f"  {RED}Esta seguro? Esta accion no se puede deshacer.{RESET} [s/N]: ").strip().lower()
    if confirm2 not in ("s", "si", "y", "yes"):
        log("Reset cancelado", "info")
        return

    # Ejecutar reset

    # venv
    if os.path.exists(VENV_DIR):
        log("Eliminando venv...")
        shutil.rmtree(VENV_DIR, ignore_errors=True)
        log("venv eliminado", "ok")

    # .env
    if os.path.exists(env_path):
        log("Eliminando .env...")
        os.remove(env_path)
        log(".env eliminado", "ok")

    # Caches
    log("Eliminando caches...")
    for dirpath, dirnames, _ in os.walk(BASE_DIR):
        dirnames[:] = [d for d in dirnames if d not in ("venv", "dist", "build", "pgsql", ".git", "node_modules")]
        for d in list(dirnames):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(dirpath, d), ignore_errors=True)
    if os.path.exists(pytest_cache):
        shutil.rmtree(pytest_cache, ignore_errors=True)
    if os.path.exists(htmlcov):
        shutil.rmtree(htmlcov, ignore_errors=True)
    if os.path.exists(coverage_file):
        os.remove(coverage_file)
    log("Caches eliminados", "ok")

    # dist/
    if os.path.exists(dist_dir):
        log("Eliminando dist/...")
        shutil.rmtree(dist_dir, ignore_errors=True)
        log("dist/ eliminado", "ok")

    # build/
    if os.path.exists(build_dir):
        log("Eliminando build/...")
        shutil.rmtree(build_dir, ignore_errors=True)
        log("build/ eliminado", "ok")

    # pgsql/
    if os.path.exists(pgsql_dir):
        log("Eliminando pgsql/ (PostgreSQL portable)...")
        shutil.rmtree(pgsql_dir, ignore_errors=True)
        log("pgsql/ eliminado", "ok")

    # Archivos ZIP de PostgreSQL
    for z in pg_zips:
        zpath = os.path.join(BASE_DIR, z)
        if os.path.exists(zpath):
            log(f"Eliminando {z}...")
            os.remove(zpath)
            log(f"{z} eliminado", "ok")

    print()
    log("Reset completo. Ejecuta de nuevo: python quickstart.py", "ok")


def show_help():
    """Ayuda completa."""
    banner()
    print(f"  {CYAN}Centro de Control Unificado v{VERSION}{RESET}\n")
    print(f"  {BOLD}USO INTERACTIVO:{RESET}\n")
    print(f"    {GREEN}python quickstart.py{RESET}              Menu interactivo\n")
    print(f"  {BOLD}LINEA DE COMANDOS:{RESET}\n")
    print(f"    {GREEN}python quickstart.py --dev{RESET}        Iniciar servidor de desarrollo")
    print(f"    {GREEN}python quickstart.py --install{RESET}    Solo instalar dependencias")
    print(f"    {GREEN}python quickstart.py --pg{RESET}         Gestionar PostgreSQL (submenu)")
    print(f"    {GREEN}python quickstart.py --build{RESET}      Construir instalador .exe")
    print(f"    {GREEN}python quickstart.py --docker{RESET}     Desplegar con Docker Compose")
    print(f"    {GREEN}python quickstart.py --check{RESET}      Verificar requisitos del sistema")
    print(f"    {GREEN}python quickstart.py --update{RESET}     Actualizar aplicacion (git pull)")
    print(f"    {GREEN}python quickstart.py --status{RESET}     Estado del sistema")
    print(f"    {GREEN}python quickstart.py --clean{RESET}      Limpiar entorno (venv, cache)")
    print(f"    {GREEN}python quickstart.py --reset{RESET}      Reset completo")
    print(f"    {GREEN}python quickstart.py --help{RESET}       Esta ayuda")
    print()
    print(f"  {BOLD}RESULTADO DE --build:{RESET}\n")
    print(f"    dist/installer/TechStock_Setup_v{VERSION}.exe")
    print(f"    {DIM}Ese .exe es el instalador final. Al ejecutarlo en otro PC:{RESET}")
    print(f"    {DIM}  - Primera vez: instala todo (app + PostgreSQL){RESET}")
    print(f"    {DIM}  - Ya instalado: ofrece Reparar o Desinstalar{RESET}")
    print()
    print(f"  {BOLD}ARCHIVOS RELACIONADOS:{RESET}\n")
    print(f"    {DIM}quickstart.py{RESET}         Este script -- centro de control unificado")
    print(f"    {DIM}launcher.py{RESET}           GUI del Launcher (lo que abre el .exe instalado)")
    print(f"    {DIM}TechStock_Setup.exe{RESET}   El instalador final (instala/repara/desinstala)")
    print()


def show_menu():
    """Menu interactivo principal."""
    while True:
        print(f"\n{BOLD}{CYAN}{'=' * 54}")
        print(f"  TechStock -- Centro de Control v{VERSION}")
        print(f"{'=' * 54}{RESET}")
        print()
        print(f"  {BOLD}DESARROLLO{RESET}")
        print(f"    {GREEN}[1]{RESET}  Iniciar servidor de desarrollo")
        print(f"    {GREEN}[2]{RESET}  Instalar/actualizar dependencias")
        print(f"    {GREEN}[3]{RESET}  PostgreSQL (descargar, iniciar, detener, config)")
        print()
        print(f"  {BOLD}DESPLIEGUE{RESET}")
        print(f"    {GREEN}[4]{RESET}  Construir instalador (.exe)")
        print(f"    {GREEN}[5]{RESET}  Desplegar con Docker Compose")
        print()
        print(f"  {BOLD}MANTENIMIENTO{RESET}")
        print(f"    {GREEN}[6]{RESET}  Verificar requisitos del sistema")
        print(f"    {GREEN}[7]{RESET}  Actualizar aplicacion (git pull + deps)")
        print(f"    {GREEN}[8]{RESET}  Estado del sistema")
        print()
        print(f"  {BOLD}LIMPIEZA{RESET}")
        print(f"    {GREEN}[9]{RESET}  Limpiar entorno (venv, cache, .env)")
        print(f"    {GREEN}[R]{RESET}  Reset completo (todo + dist + build + pgsql)")
        print()
        print(f"    {DIM}[0]{RESET}  Ayuda")
        print(f"    {DIM}[Q]{RESET}  Salir")
        print()

        try:
            choice = input(f"  Seleccione una opcion: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print()
            log("Saliendo...", "info")
            break

        if choice in ("q", "quit", "exit"):
            log("Hasta luego.", "info")
            break
        elif choice == "0":
            show_help()
        elif choice == "1":
            banner()
            print(f"  {CYAN}Modo: Servidor de desarrollo{RESET}\n")
            run_dev(dev=True)
            # Si el servidor se detuvo (Ctrl+C), volver al menu
        elif choice == "2":
            run_install()
        elif choice == "3":
            run_postgres()
        elif choice == "4":
            banner()
            print(f"  {CYAN}Modo: Construir instalador .exe{RESET}\n")
            run_build()
        elif choice == "5":
            banner()
            print(f"  {CYAN}Modo: Docker Compose{RESET}\n")
            run_docker()
        elif choice == "6":
            run_check()
        elif choice == "7":
            run_update()
        elif choice == "8":
            run_status()
        elif choice == "9":
            run_clean()
        elif choice == "r":
            run_reset()
        elif choice == "":
            continue
        else:
            log(f"Opcion no valida: {choice}", "warn")
            continue

        # Pausa antes de volver al menu (excepto para opciones que salen del loop)
        if choice not in ("q", "quit", "exit", ""):
            print()
            try:
                input(f"  Presione Enter para volver al menu...")
            except (KeyboardInterrupt, EOFError):
                print()
                log("Saliendo...", "info")
                break


# ================================================================
#  MAIN
# ================================================================

def main():
    """Punto de entrada: CLI args o menu interactivo."""
    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        show_help()
        return

    # Modo CLI directo (con argumentos)
    if args:
        banner()

        if "--reset" in args:
            print(f"  {CYAN}Modo: Reset completo{RESET}\n")
            run_reset()
            return

        if "--clean" in args:
            print(f"  {CYAN}Modo: Limpiar entorno{RESET}\n")
            run_clean()
            return

        if "--docker" in args:
            print(f"  {CYAN}Modo: Docker Compose{RESET}\n")
            run_docker()
            return

        if "--build" in args:
            print(f"  {CYAN}Modo: Construir instalador .exe{RESET}\n")
            run_build()
            return

        if "--install" in args:
            print(f"  {CYAN}Modo: Instalar dependencias{RESET}\n")
            run_install()
            return

        if "--pg" in args:
            print(f"  {CYAN}Modo: Gestion PostgreSQL{RESET}\n")
            run_postgres()
            return

        if "--check" in args:
            print(f"  {CYAN}Modo: Verificar requisitos{RESET}\n")
            run_check()
            return

        if "--update" in args:
            print(f"  {CYAN}Modo: Actualizar aplicacion{RESET}\n")
            run_update()
            return

        if "--status" in args:
            print(f"  {CYAN}Modo: Estado del sistema{RESET}\n")
            run_status()
            return

        if "--dev" in args:
            print(f"  {CYAN}Modo: Desarrollo (con herramientas de testing){RESET}\n")
            run_dev(dev=True)
            return

        # Argumento no reconocido
        log(f"Argumento no reconocido: {' '.join(args)}", "err")
        log("Usa --help para ver las opciones disponibles", "info")
        return

    # Sin argumentos: menu interactivo
    banner()
    show_menu()


if __name__ == "__main__":
    main()
