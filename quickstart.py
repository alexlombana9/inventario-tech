"""TechStock — Punto de entrada unico.

USO:
  python quickstart.py                  Configurar entorno e iniciar servidor
  python quickstart.py --dev            Igual + herramientas de desarrollo (pytest)
  python quickstart.py --docker         Levantar todo con Docker Compose
  python quickstart.py --build          Construir instalador .exe para distribuir
  python quickstart.py --reset          Limpiar entorno (borra venv y .env)

QUE ES CADA COSA:
  quickstart.py         Este script — configura, ejecuta o construye
  build_installer.bat   Atajo rapido para: python quickstart.py --build
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

VERSION = "2.0"

# ── Colores para terminal ──
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


def show_help():
    banner()
    print(f"  {CYAN}Punto de entrada unico v{VERSION}{RESET}\n")
    print(f"  {BOLD}MODOS DE USO:{RESET}\n")
    print(f"    {GREEN}python quickstart.py{RESET}           Configurar + iniciar servidor")
    print(f"    {GREEN}python quickstart.py --dev{RESET}     Igual + pytest, httpx, coverage")
    print(f"    {GREEN}python quickstart.py --docker{RESET}  Levantar con Docker Compose")
    print(f"    {GREEN}python quickstart.py --build{RESET}   Construir instalador .exe")
    print(f"    {GREEN}python quickstart.py --reset{RESET}   Limpiar entorno completo")
    print()
    print(f"  {BOLD}RESULTADO DE --build:{RESET}\n")
    print(f"    dist/installer/TechStock_Setup_v{VERSION}.exe")
    print(f"    {DIM}Ese .exe es el instalador final. Al ejecutarlo en otro PC:{RESET}")
    print(f"    {DIM}  - Primera vez: instala todo (app + PostgreSQL){RESET}")
    print(f"    {DIM}  - Ya instalado: ofrece Reparar o Desinstalar{RESET}")
    print()


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


# ════════════════════════════════════════════════════════════
#  MODO: DESARROLLO (default / --dev)
# ════════════════════════════════════════════════════════════

def setup_venv(dev=False):
    header("1/4  Entorno virtual")

    if os.path.exists(VENV_PYTHON):
        log("venv ya existe", "ok")
    else:
        log("Creando entorno virtual...")
        run([sys.executable, "-m", "venv", VENV_DIR])
        log("venv creado", "ok")

    reqs_file = "requirements-dev.txt" if dev else "requirements.txt"
    log(f"Instalando dependencias ({reqs_file})...")
    result = run([VENV_PIP, "install", "-r", reqs_file, "-q"], check=False, capture=True)
    if result and result.returncode == 0:
        log("Dependencias instaladas", "ok")
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
    pg_dir = os.path.join(BASE_DIR, "pgsql", "bin")
    has_portable = os.path.exists(os.path.join(pg_dir, "pg_ctl.exe" if IS_WIN else "pg_ctl"))

    if port_in_use(configured_port):
        log(f"PostgreSQL activo en puerto {configured_port}", "ok")
        return True

    for port in [5432, PG_PORT]:
        if port != configured_port and port_in_use(port):
            log(f"PostgreSQL detectado en puerto {port}, pero .env apunta a {configured_port}", "warn")
            log(f"Ajusta DATABASE_URL en .env para usar puerto {port}", "info")
            return False

    if has_portable:
        log("PostgreSQL portable encontrado, usa el Launcher para iniciarlo:", "warn")
        log("  python launcher.py", "info")
        return False

    log(f"PostgreSQL no detectado en puerto {configured_port}", "warn")
    log("Opciones:", "info")
    print(f"      a) Instalar PostgreSQL 16: https://www.postgresql.org/download/")
    print(f"      b) Usar Docker:  python quickstart.py --docker")
    print(f"      c) PG portable:  python launcher.py")
    return False


def try_connect_db():
    try:
        result = run(
            [VENV_PYTHON, "-c", "from database import engine; engine.connect().close(); print('OK')"],
            capture=True, check=False
        )
        if result and "OK" in (result.stdout or ""):
            log("Conexion a base de datos exitosa", "ok")
            return True
        log("No se pudo conectar a la base de datos", "warn")
        return False
    except Exception:
        return False


def start_server():
    header("4/4  Iniciando TechStock")

    if port_in_use(WEB_PORT):
        log(f"Puerto {WEB_PORT} ya en uso — el servidor puede estar corriendo", "warn")
        log(f"Abre http://localhost:{WEB_PORT}", "info")
        return

    log(f"Iniciando servidor en http://localhost:{WEB_PORT} ...")
    log("Presiona Ctrl+C para detener\n", "info")

    try:
        proc = subprocess.Popen([VENV_PYTHON, "main.py"], cwd=BASE_DIR)
        for _ in range(30):
            time.sleep(1)
            if port_in_use(WEB_PORT):
                log(f"Servidor listo en http://localhost:{WEB_PORT}", "ok")
                log("Admin: admin / admin123 (cambia la clave al entrar)", "info")
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
        log(f"Python {v.major}.{v.minor} detectado — se requiere 3.10+", "err")
        sys.exit(1)
    log(f"Python {v.major}.{v.minor}.{v.micro}", "ok")

    setup_venv(dev=dev)
    setup_env()
    pg_ok = check_postgres()

    if pg_ok:
        if try_connect_db():
            start_server()
        else:
            log("Verifica la configuracion de DATABASE_URL en .env", "warn")
    else:
        log("\nInicia PostgreSQL y luego ejecuta:", "info")
        print(f"      python quickstart.py\n")


# ════════════════════════════════════════════════════════════
#  MODO: DOCKER
# ════════════════════════════════════════════════════════════

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


# ════════════════════════════════════════════════════════════
#  MODO: BUILD (construir instalador .exe)
# ════════════════════════════════════════════════════════════

PG_VERSION = "16.8-1"
PG_ZIP = f"postgresql-{PG_VERSION}-windows-x64-binaries.zip"
PG_URL = f"https://get.enterprisedb.com/postgresql/{PG_ZIP}"

# Herramientas PG que NO se necesitan en produccion
PG_UNNECESSARY_BINS = [
    "pgbench", "pg_basebackup", "pg_dump", "pg_dumpall",
    "pg_receivewal", "pg_recvlogical", "pg_restore",
    "pg_test_fsync", "pg_test_timing", "pg_upgrade",
    "pg_verifybackup", "pg_waldump", "pg_rewind",
    "pg_amcheck", "pg_checksums", "pg_archivecleanup",
    "vacuumdb", "reindexdb", "clusterdb", "dropuser", "ecpg",
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


# ════════════════════════════════════════════════════════════
#  MODO: RESET
# ════════════════════════════════════════════════════════════

def run_reset():
    header("Reset del entorno")

    if os.path.exists(VENV_DIR):
        log("Eliminando venv...")
        shutil.rmtree(VENV_DIR)
        log("venv eliminado", "ok")
    else:
        log("No hay venv que eliminar", "info")

    env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path):
        log("Eliminando .env...")
        os.remove(env_path)
        log(".env eliminado", "ok")
    else:
        log("No hay .env que eliminar", "info")

    log("Reset completo. Ejecuta de nuevo: python quickstart.py", "ok")


# ════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════

def main():
    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        show_help()
        return

    banner()

    if "--reset" in args:
        print(f"  {CYAN}Modo: Reset{RESET}\n")
        run_reset()
        return

    if "--docker" in args:
        print(f"  {CYAN}Modo: Docker Compose{RESET}\n")
        run_docker()
        return

    if "--build" in args:
        print(f"  {CYAN}Modo: Construir instalador .exe{RESET}\n")
        run_build()
        return

    dev = "--dev" in args
    mode = "Desarrollo (con herramientas de testing)" if dev else "Servidor de desarrollo"
    print(f"  {CYAN}Modo: {mode}{RESET}\n")
    run_dev(dev=dev)


if __name__ == "__main__":
    main()
