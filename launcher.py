"""TechStock Launcher — Interfaz para gestionar PostgreSQL + servidor web.

En modo frozen (PyInstaller), uvicorn se ejecuta in-process (no subprocess).
En modo desarrollo, se usa subprocess para facilitar recarga.
"""
import os
import sys
import subprocess
import threading
import webbrowser
import time
import logging
import tkinter as tk
from tkinter import messagebox
from datetime import datetime

# ── Deteccion de modo ──
_FROZEN = getattr(sys, "frozen", False)

# ── Ruta base ──
if _FROZEN:
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

# ── Cargar .env ──
_env_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

# ── Python del venv (solo en modo desarrollo) ──
VENV_PYTHON = None
if not _FROZEN:
    _venv_win = os.path.join(BASE_DIR, "venv", "Scripts", "python.exe")
    _venv_unix = os.path.join(BASE_DIR, "venv", "bin", "python")
    if os.path.exists(_venv_win):
        VENV_PYTHON = _venv_win
    elif os.path.exists(_venv_unix):
        VENV_PYTHON = _venv_unix
    else:
        VENV_PYTHON = sys.executable

# ── PostgreSQL portable ──
PG_DIR = os.path.join(BASE_DIR, "pgsql")
PG_BIN = os.path.join(PG_DIR, "bin")
PG_DATA = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "TechStock", "pgdata"
)
PG_LOG = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "TechStock", "pg.log"
)
PG_PORT = "5433"
PG_USER = "techstock"
PG_DB = "techstock"
PG_PASSWORD = "techstock"

# ── Paleta de colores ──
BG_DARK = "#0f0f1a"
BG_CARD = "#1a1a2e"
ACCENT = "#6c63ff"
ACCENT_HOVER = "#857dff"
SUCCESS = "#00c9a7"
DANGER = "#ff6b6b"
WARNING = "#ffc93c"
TEXT_PRIMARY = "#e8e8f0"
TEXT_SECONDARY = "#8888a0"
TEXT_MUTED = "#555570"
BORDER = "#2a2a45"

LOG_BG = "#080812"
LOG_INFO_COLOR = "#6c8cff"
LOG_WARN_COLOR = "#ffc93c"
LOG_ERR_COLOR = "#ff6b6b"
LOG_OK_COLOR = "#00c9a7"
LOG_HTTP_COLOR = "#8888a0"
LOG_MSG_COLOR = "#c0c0d0"
LOG_TIME_COLOR = "#444466"

_SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def _pg_cmd(name):
    """Retorna ruta completa al comando PostgreSQL."""
    ext = ".exe" if sys.platform == "win32" else ""
    return os.path.join(PG_BIN, f"{name}{ext}")


class _TkLogHandler(logging.Handler):
    """Routes Python logging output to the Tkinter log widget."""

    def __init__(self, launcher):
        super().__init__()
        self._launcher = launcher

    def emit(self, record):
        try:
            msg = self.format(record)
            level = self._launcher._classify(msg)
            self._launcher.root.after(0, self._launcher._log, msg, level)
        except Exception:
            pass


class TechStockLauncher:
    def __init__(self):
        self.process = None       # subprocess (modo dev)
        self._server = None       # uvicorn.Server (modo frozen)
        self.pg_process = None
        self.running = False
        self.pg_running = False
        self._stopping = False

        self.root = tk.Tk()
        self.root.title("TechStock v2.0 \u2014 Gestor de Servidor")
        self.root.geometry("780x720")
        self.root.minsize(650, 520)
        self.root.configure(bg=BG_DARK)

        # Icono
        try:
            ico = os.path.join(BASE_DIR, "static", "favicon.ico")
            if os.path.exists(ico):
                self.root.iconbitmap(ico)
        except Exception:
            pass

        # Centrar
        self.root.update_idletasks()
        x = max(0, (self.root.winfo_screenwidth() // 2) - 390)
        y = max(0, (self.root.winfo_screenheight() // 2) - 360)
        self.root.geometry(f"+{x}+{y}")

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        mode = "empaquetado" if _FROZEN else "desarrollo"
        self._log(f"TechStock v2.0 \u2014 Gestor de servidor ({mode})", "OK")
        if _FROZEN:
            self._log(f"Directorio: {BASE_DIR}", "INFO")
        else:
            self._log(f"Python: {VENV_PYTHON}", "INFO")
        self._log(f"PostgreSQL: {PG_BIN}", "INFO")
        self._log(f"Datos: {PG_DATA}", "INFO")

    # ────────────────────────────────────────────────────────
    #  UI
    # ────────────────────────────────────────────────────────

    def _build_ui(self):
        root = self.root

        # ── Header compacto ──
        header = tk.Frame(root, bg=BG_DARK)
        header.pack(fill="x", padx=24, pady=(18, 6))

        left = tk.Frame(header, bg=BG_DARK)
        left.pack(side="left")

        tk.Label(left, text="\u2b22", font=("Segoe UI", 32), fg=ACCENT,
                 bg=BG_DARK).pack(side="left", padx=(0, 12))

        titles = tk.Frame(left, bg=BG_DARK)
        titles.pack(side="left")
        tk.Label(titles, text="TechStock", font=("Segoe UI", 20, "bold"),
                 fg=TEXT_PRIMARY, bg=BG_DARK).pack(anchor="w")
        tk.Label(titles, text="Sistema de Inventario v2.0",
                 font=("Segoe UI", 9), fg=TEXT_SECONDARY,
                 bg=BG_DARK).pack(anchor="w")

        # ── Divider ──
        tk.Frame(root, bg=BORDER, height=1).pack(fill="x", padx=24, pady=8)

        # ── Status bar ──
        bar = tk.Frame(root, bg=BG_DARK)
        bar.pack(fill="x", padx=24, pady=4)

        # Status indicators
        st = tk.Frame(bar, bg=BG_DARK)
        st.pack(side="left")

        # PostgreSQL status
        pg_frame = tk.Frame(st, bg=BG_DARK)
        pg_frame.pack(side="left", padx=(0, 16))
        self._pg_dot = tk.Label(pg_frame, text="\u25cf", font=("Segoe UI", 10),
                                fg=DANGER, bg=BG_DARK)
        self._pg_dot.pack(side="left", padx=(0, 4))
        self._pg_status_var = tk.StringVar(value="PostgreSQL detenido")
        tk.Label(pg_frame, textvariable=self._pg_status_var,
                 font=("Segoe UI", 9), fg=TEXT_SECONDARY,
                 bg=BG_DARK).pack(side="left")

        # Server status
        sv_frame = tk.Frame(st, bg=BG_DARK)
        sv_frame.pack(side="left")
        self._dot = tk.Label(sv_frame, text="\u25cf", font=("Segoe UI", 10),
                             fg=DANGER, bg=BG_DARK)
        self._dot.pack(side="left", padx=(0, 4))
        self._status_var = tk.StringVar(value="Servidor detenido")
        tk.Label(sv_frame, textvariable=self._status_var,
                 font=("Segoe UI", 9), fg=TEXT_SECONDARY,
                 bg=BG_DARK).pack(side="left")

        self._url_var = tk.StringVar(value="")
        self._url_lbl = tk.Label(st, textvariable=self._url_var,
                                 font=("Segoe UI", 10), fg=ACCENT,
                                 bg=BG_DARK, cursor="hand2")
        self._url_lbl.pack(side="left", padx=(14, 0))
        self._url_lbl.bind("<Button-1>",
                           lambda e: self._open_browser() if self.running else None)

        # Botones
        btns = tk.Frame(bar, bg=BG_DARK)
        btns.pack(side="right")

        self._btn_start = tk.Button(
            btns, text="\u25b6  Iniciar", font=("Segoe UI", 10, "bold"),
            bg=ACCENT, fg="white", activebackground=ACCENT_HOVER,
            activeforeground="white", relief="flat", padx=18, pady=7,
            cursor="hand2", command=self._start_all)
        self._btn_start.pack(side="left", padx=3)

        self._btn_stop = tk.Button(
            btns, text="\u25a0  Detener", font=("Segoe UI", 10, "bold"),
            bg="#3a3a55", fg=TEXT_SECONDARY, activebackground="#4a4a65",
            activeforeground="white", relief="flat", padx=18, pady=7,
            cursor="hand2", command=self._stop_all, state="disabled")
        self._btn_stop.pack(side="left", padx=3)

        self._btn_web = tk.Button(
            btns, text="\U0001f310 Navegador", font=("Segoe UI", 10),
            bg="#1e1e35", fg=TEXT_SECONDARY, activebackground="#2e2e50",
            activeforeground="white", relief="flat", padx=14, pady=7,
            cursor="hand2", command=self._open_browser, state="disabled")
        self._btn_web.pack(side="left", padx=3)

        # ── Divider ──
        tk.Frame(root, bg=BORDER, height=1).pack(fill="x", padx=24, pady=8)

        # ── Log header ──
        lh = tk.Frame(root, bg=BG_DARK)
        lh.pack(fill="x", padx=24)

        tk.Label(lh, text="\U0001f4cb Registro de Actividad",
                 font=("Segoe UI", 10, "bold"), fg=TEXT_PRIMARY,
                 bg=BG_DARK).pack(side="left")

        tk.Button(lh, text="Limpiar", font=("Segoe UI", 8),
                  bg=BG_CARD, fg=TEXT_MUTED, activebackground="#2a2a45",
                  relief="flat", padx=10, pady=2, cursor="hand2",
                  command=self._clear_log).pack(side="right")

        # ── Log area ──
        log_border = tk.Frame(root, bg=BORDER)
        log_border.pack(fill="both", expand=True, padx=24, pady=(6, 12))

        self._log_text = tk.Text(
            log_border, bg=LOG_BG, fg=LOG_MSG_COLOR,
            font=("Consolas", 9), wrap="word", state="disabled",
            relief="flat", padx=10, pady=8, insertbackground=TEXT_PRIMARY,
            selectbackground=ACCENT, selectforeground="white",
            borderwidth=0, highlightthickness=0)

        scroll = tk.Scrollbar(log_border, command=self._log_text.yview,
                              bg=BG_CARD, troughcolor=BG_DARK,
                              highlightthickness=0, borderwidth=0)
        self._log_text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self._log_text.pack(fill="both", expand=True)

        # Tags de color
        self._log_text.tag_configure("ts", foreground=LOG_TIME_COLOR)
        self._log_text.tag_configure("INFO", foreground=LOG_INFO_COLOR)
        self._log_text.tag_configure("WARN", foreground=LOG_WARN_COLOR)
        self._log_text.tag_configure("ERROR", foreground=LOG_ERR_COLOR)
        self._log_text.tag_configure("OK", foreground=LOG_OK_COLOR)
        self._log_text.tag_configure("HTTP", foreground=LOG_HTTP_COLOR)
        self._log_text.tag_configure("msg", foreground=LOG_MSG_COLOR)

        # ── Footer ──
        ft = tk.Frame(root, bg=BG_DARK)
        ft.pack(fill="x", padx=24, pady=(0, 8))
        tk.Label(ft, text=f"Puerto web: 8000 | Puerto PG: {PG_PORT}",
                 font=("Segoe UI", 8), fg=TEXT_MUTED, bg=BG_DARK).pack(side="left")
        tk.Label(ft, text="TechStock \u00a9 2026",
                 font=("Segoe UI", 8), fg=TEXT_MUTED,
                 bg=BG_DARK).pack(side="right")

    # ────────────────────────────────────────────────────────
    #  Logging
    # ────────────────────────────────────────────────────────

    def _log(self, message, level="INFO"):
        ts = datetime.now().strftime("%H:%M:%S")
        tag = level if level in ("INFO", "WARN", "ERROR", "OK", "HTTP") else "INFO"

        self._log_text.configure(state="normal")
        self._log_text.insert("end", f"[{ts}] ", "ts")
        self._log_text.insert("end", f"{tag:<6}", tag)
        self._log_text.insert("end", f" {message}\n", "msg")
        self._log_text.configure(state="disabled")
        self._log_text.see("end")

    def _clear_log(self):
        self._log_text.configure(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.configure(state="disabled")

    # ────────────────────────────────────────────────────────
    #  Status helpers
    # ────────────────────────────────────────────────────────

    def _set_pg_status(self, text, color):
        self._pg_status_var.set(text)
        self._pg_dot.config(fg=color)

    def _set_status(self, text, color):
        self._status_var.set(text)
        self._dot.config(fg=color)

    def _enable_running_ui(self):
        self._btn_start.config(state="disabled")
        self._btn_stop.config(state="normal", bg=DANGER, fg="white")
        self._btn_web.config(state="normal")

    def _enable_stopped_ui(self):
        self.running = False
        self._url_var.set("")
        self._btn_start.config(state="normal")
        self._btn_stop.config(state="disabled", bg="#3a3a55", fg=TEXT_SECONDARY)
        self._btn_web.config(state="disabled")

    def _classify(self, line):
        """Clasifica una linea de log por nivel."""
        low = line.lower()
        if any(k in low for k in ("error", "traceback", "exception", "critical")):
            return "ERROR"
        if any(k in low for k in ("warning", "warn", "deprecat")):
            return "WARN"
        if any(k in low for k in ("started", "[ok]", "listo", "ready")):
            return "OK"
        if any(m in line for m in ("GET ", "POST ", "PUT ", "DELETE ", "PATCH ")):
            return "HTTP"
        return "INFO"

    # ────────────────────────────────────────────────────────
    #  PostgreSQL management
    # ────────────────────────────────────────────────────────

    def _pg_exists(self):
        """Verifica si PostgreSQL portable esta disponible."""
        return os.path.isfile(_pg_cmd("pg_ctl"))

    def _pg_init_db(self):
        """Inicializa el cluster de datos si no existe."""
        if os.path.exists(os.path.join(PG_DATA, "PG_VERSION")):
            return True

        self._log("Inicializando base de datos PostgreSQL...", "INFO")
        os.makedirs(PG_DATA, exist_ok=True)

        try:
            initdb = _pg_cmd("initdb")
            env = os.environ.copy()
            env["PGDATA"] = PG_DATA
            result = subprocess.run(
                [initdb, "-D", PG_DATA, "-U", "postgres", "-E", "UTF8",
                 "--locale=C", "--auth=trust"],
                capture_output=True, text=True, timeout=60, env=env,
                creationflags=_SUBPROCESS_FLAGS,
            )
            if result.returncode != 0:
                self._log(f"Error initdb: {result.stderr.strip()}", "ERROR")
                return False
            self._log("Cluster PostgreSQL inicializado.", "OK")

            # Configurar puerto en postgresql.conf
            conf_path = os.path.join(PG_DATA, "postgresql.conf")
            with open(conf_path, "a") as f:
                f.write(f"\n# TechStock config\n")
                f.write(f"port = {PG_PORT}\n")
                f.write(f"listen_addresses = 'localhost'\n")
                f.write(f"log_destination = 'stderr'\n")
                f.write(f"logging_collector = off\n")
                # Optimizaciones para inicio rapido
                f.write(f"shared_buffers = 128MB\n")
                f.write(f"fsync = on\n")
                f.write(f"synchronous_commit = off\n")

            return True
        except Exception as e:
            self._log(f"Error al inicializar: {e}", "ERROR")
            return False

    def _pg_start(self):
        """Inicia PostgreSQL portable."""
        if not self._pg_exists():
            self._log("PostgreSQL portable no encontrado en pgsql/", "ERROR")
            self._log("Ejecute el instalador para incluir PostgreSQL.", "ERROR")
            return False

        if not self._pg_init_db():
            return False

        self._set_pg_status("Iniciando PostgreSQL...", WARNING)
        self._log("Iniciando PostgreSQL...", "INFO")
        self.root.update()

        try:
            pg_ctl = _pg_cmd("pg_ctl")
            env = os.environ.copy()
            env["PGDATA"] = PG_DATA
            result = subprocess.run(
                [pg_ctl, "start", "-D", PG_DATA, "-l", PG_LOG,
                 "-w", "-t", "30",
                 "-o", f"-p {PG_PORT}"],
                capture_output=True, text=True, timeout=45, env=env,
                creationflags=_SUBPROCESS_FLAGS,
            )
            if result.returncode != 0:
                err = result.stderr.strip() or result.stdout.strip()
                self._log(f"Error al iniciar PG: {err}", "ERROR")
                self._set_pg_status("Error PostgreSQL", DANGER)
                return False

        except subprocess.TimeoutExpired:
            self._log("Timeout al iniciar PostgreSQL", "ERROR")
            self._set_pg_status("Timeout PostgreSQL", DANGER)
            return False
        except Exception as e:
            self._log(f"Error: {e}", "ERROR")
            self._set_pg_status("Error PostgreSQL", DANGER)
            return False

        self.pg_running = True
        self._set_pg_status("PostgreSQL activo", SUCCESS)
        self._log(f"PostgreSQL iniciado en puerto {PG_PORT}.", "OK")

        # Crear usuario y base de datos si no existen
        self._pg_ensure_db()
        return True

    def _pg_ensure_db(self):
        """Crea el usuario y la base de datos si no existen."""
        psql = _pg_cmd("psql")
        createdb = _pg_cmd("createdb")
        env = os.environ.copy()
        env["PGPORT"] = PG_PORT

        # Verificar si el usuario existe
        try:
            result = subprocess.run(
                [psql, "-U", "postgres", "-p", PG_PORT, "-tAc",
                 f"SELECT 1 FROM pg_roles WHERE rolname='{PG_USER}'"],
                capture_output=True, text=True, timeout=10, env=env,
                creationflags=_SUBPROCESS_FLAGS,
            )
            if "1" not in result.stdout:
                subprocess.run(
                    [psql, "-U", "postgres", "-p", PG_PORT, "-c",
                     f"CREATE USER {PG_USER} WITH PASSWORD '{PG_PASSWORD}' CREATEDB"],
                    capture_output=True, text=True, timeout=10, env=env,
                    creationflags=_SUBPROCESS_FLAGS,
                )
                self._log(f"Usuario '{PG_USER}' creado.", "OK")
        except Exception as e:
            self._log(f"Aviso creando usuario: {e}", "WARN")

        # Verificar si la BD existe
        try:
            result = subprocess.run(
                [psql, "-U", "postgres", "-p", PG_PORT, "-tAc",
                 f"SELECT 1 FROM pg_database WHERE datname='{PG_DB}'"],
                capture_output=True, text=True, timeout=10, env=env,
                creationflags=_SUBPROCESS_FLAGS,
            )
            if "1" not in result.stdout:
                subprocess.run(
                    [createdb, "-U", "postgres", "-p", PG_PORT,
                     "-O", PG_USER, PG_DB],
                    capture_output=True, text=True, timeout=10, env=env,
                    creationflags=_SUBPROCESS_FLAGS,
                )
                self._log(f"Base de datos '{PG_DB}' creada.", "OK")
        except Exception as e:
            self._log(f"Aviso creando BD: {e}", "WARN")

    def _pg_stop(self):
        """Detiene PostgreSQL portable."""
        if not self.pg_running:
            return

        self._log("Deteniendo PostgreSQL...", "WARN")
        try:
            pg_ctl = _pg_cmd("pg_ctl")
            env = os.environ.copy()
            env["PGDATA"] = PG_DATA
            subprocess.run(
                [pg_ctl, "stop", "-D", PG_DATA, "-m", "fast", "-w", "-t", "15"],
                capture_output=True, text=True, timeout=20, env=env,
                creationflags=_SUBPROCESS_FLAGS,
            )
        except Exception:
            pass

        self.pg_running = False
        self._set_pg_status("PostgreSQL detenido", DANGER)
        self._log("PostgreSQL detenido.", "INFO")

    # ────────────────────────────────────────────────────────
    #  Database connection check
    # ────────────────────────────────────────────────────────

    def _check_db_connection(self):
        """Verifica conexion a la base de datos."""
        if _FROZEN:
            return self._check_db_inprocess()
        else:
            return self._check_db_subprocess()

    def _check_db_inprocess(self):
        """Verificacion directa con imports (modo frozen)."""
        try:
            from sqlalchemy import text as sa_text
            from database import engine
            with engine.connect() as conn:
                conn.execute(sa_text("SELECT 1"))
            return True
        except Exception as e:
            self._log(f"Error DB: {e}", "ERROR")
            return False

    def _check_db_subprocess(self):
        """Verificacion via subprocess (modo desarrollo)."""
        try:
            chk = subprocess.run(
                [VENV_PYTHON, "-c",
                 "from database import engine; c=engine.connect(); c.close()"],
                cwd=BASE_DIR, capture_output=True, text=True, timeout=15,
                creationflags=_SUBPROCESS_FLAGS,
            )
            if chk.returncode != 0:
                err = chk.stderr.strip() or chk.stdout.strip() or "Sin detalle"
                self._log(f"Error DB: {err}", "ERROR")
                return False
            return True
        except Exception as e:
            self._log(f"Excepcion: {e}", "ERROR")
            return False

    # ────────────────────────────────────────────────────────
    #  Server control
    # ────────────────────────────────────────────────────────

    def _start_all(self):
        """Inicia PostgreSQL + servidor web."""
        if self.running:
            return

        self._stopping = False
        self._btn_start.config(state="disabled")
        self.root.update()

        # 1. Iniciar PostgreSQL
        if self._pg_exists():
            if not self._pg_start():
                self._btn_start.config(state="normal")
                return
        else:
            # PostgreSQL externo (no portable) — verificar conexion
            self._set_pg_status("Verificando PG externo...", WARNING)
            self._log("PG portable no encontrado, verificando PG externo...", "INFO")

        # 2. Configurar DATABASE_URL para el servidor
        db_url = os.environ.get("DATABASE_URL", "").strip()
        if not db_url and self.pg_running:
            os.environ["DATABASE_URL"] = (
                f"postgresql://{PG_USER}:{PG_PASSWORD}@localhost:{PG_PORT}/{PG_DB}"
            )

        # 3. Verificar conexion
        self._set_status("Verificando conexion...", WARNING)
        self._log("Verificando conexion a base de datos...", "INFO")
        self.root.update()

        if not self._check_db_connection():
            self._set_status("Error de conexion", DANGER)
            messagebox.showerror(
                "Error de Base de Datos",
                "No se pudo conectar a PostgreSQL.\n\n"
                "Verifique que PostgreSQL este disponible.")
            self._btn_start.config(state="normal")
            return

        self._log("Conexion a base de datos OK.", "OK")
        if not self.pg_running:
            self._set_pg_status("PostgreSQL externo", SUCCESS)

        # 4. Iniciar servidor web
        self._set_status("Iniciando servidor...", WARNING)
        self._log("Iniciando servidor en puerto 8000...", "INFO")
        self.root.update()

        if _FROZEN:
            self._start_server_inprocess()
        else:
            self._start_server_subprocess()

    def _start_server_inprocess(self):
        """Inicia uvicorn in-process (modo frozen/empaquetado)."""
        try:
            import uvicorn

            # Instalar handler de logging para capturar output de uvicorn
            handler = _TkLogHandler(self)
            handler.setFormatter(logging.Formatter("%(message)s"))
            for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "techstock"):
                lgr = logging.getLogger(logger_name)
                lgr.addHandler(handler)
                lgr.setLevel(logging.INFO)

            config = uvicorn.Config(
                "main:app",
                host="0.0.0.0",
                port=8000,
                log_level="info",
                access_log=True,
            )
            self._server = uvicorn.Server(config)

            self.running = True
            self._enable_running_ui()

            # Ejecutar en hilo daemon
            threading.Thread(target=self._run_server, daemon=True).start()
            threading.Thread(target=self._wait_ready, daemon=True).start()

        except Exception as e:
            self._set_status("Error al iniciar", DANGER)
            self._log(f"No se pudo iniciar: {e}", "ERROR")
            self._btn_start.config(state="normal")

    def _run_server(self):
        """Ejecuta uvicorn.Server.run() en hilo separado."""
        try:
            self._server.run()
        except Exception as e:
            self.root.after(0, self._log, f"Error servidor: {e}", "ERROR")

        # Si llega aqui, el servidor se detuvo
        if self.running and not self._stopping:
            self.root.after(0, self._unexpected_stop)

    def _start_server_subprocess(self):
        """Inicia main.py como subprocess (modo desarrollo)."""
        try:
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            self.process = subprocess.Popen(
                [VENV_PYTHON, "-u", "main.py"],
                cwd=BASE_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                creationflags=_SUBPROCESS_FLAGS,
            )
        except Exception as e:
            self._set_status("Error al iniciar", DANGER)
            self._log(f"No se pudo iniciar: {e}", "ERROR")
            self._btn_start.config(state="normal")
            return

        self.running = True
        self._enable_running_ui()

        # Hilos de monitoreo
        threading.Thread(target=self._read_output, daemon=True).start()
        threading.Thread(target=self._wait_ready, daemon=True).start()

    def _read_output(self):
        """Lee stdout del proceso subprocess y lo muestra en el log."""
        try:
            for raw in iter(self.process.stdout.readline, b""):
                if not self.running:
                    break
                line = raw.decode("utf-8", errors="replace").rstrip()
                if not line:
                    continue
                level = self._classify(line)
                self.root.after(0, self._log, line, level)
        except Exception:
            pass

        # Proceso terminado
        if self.running and not self._stopping:
            self.root.after(0, self._unexpected_stop)

    def _wait_ready(self):
        """Espera hasta que el servidor responda en localhost:8000."""
        import urllib.request
        for _ in range(30):
            if not self.running:
                return
            try:
                urllib.request.urlopen("http://localhost:8000", timeout=2)
                self.root.after(0, self._server_ready)
                return
            except Exception:
                time.sleep(1)
        self.root.after(0, lambda: self._set_status(
            "Iniciado (verificar puerto)", WARNING))

    def _server_ready(self):
        self._set_status("Servidor activo", SUCCESS)
        self._url_var.set("\U0001f517 http://localhost:8000")
        self._log("Servidor listo en http://localhost:8000", "OK")

    def _unexpected_stop(self):
        self._set_status("Servidor detenido inesperadamente", DANGER)
        self._log("El servidor se detuvo inesperadamente.", "ERROR")
        self._enable_stopped_ui()

    def _stop_all(self):
        """Detiene servidor web + PostgreSQL."""
        if not self.running and not self.pg_running:
            return

        self._stopping = True

        # 1. Detener servidor web
        if _FROZEN and self._server:
            self._log("Deteniendo servidor...", "WARN")
            self._server.should_exit = True
            # Esperar un momento a que el servidor termine
            time.sleep(1)
            self._server = None
        elif self.process:
            self._log("Deteniendo servidor...", "WARN")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None

        self._set_status("Servidor detenido", DANGER)
        self._log("Servidor detenido.", "INFO")

        # 2. Detener PostgreSQL portable
        if self.pg_running:
            self._pg_stop()

        self._enable_stopped_ui()

    def _open_browser(self):
        if self.running:
            webbrowser.open("http://localhost:8000")
            self._log("Navegador abierto.", "INFO")

    def _on_close(self):
        if self.running or self.pg_running:
            if messagebox.askyesno(
                "Cerrar TechStock",
                "El servidor esta corriendo.\n\u00bfDetenerlo y salir?"):
                self._stop_all()
            else:
                return
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = TechStockLauncher()
    app.run()
