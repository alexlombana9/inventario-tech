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
from tkinter import ttk
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
_APPDATA_DIR = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "TechStock"
)
PG_DATA = os.path.join(_APPDATA_DIR, "pgdata")
PG_LOG = os.path.join(_APPDATA_DIR, "pg.log")
PG_PORT = "5433"
PG_USER = "techstock"
PG_DB = "techstock"
PG_PASSWORD = "techstock"
WEB_PORT = 8000

# ── Paleta de colores ──
BG_DARK = "#0f0f1a"
BG_CARD = "#1a1a2e"
BG_INPUT = "#12122a"
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
        self.process = None
        self._server = None
        self.pg_process = None
        self.running = False
        self.pg_running = False
        self._stopping = False
        self._starting = False
        self._auto_browser = True

        self.root = tk.Tk()
        self.root.title("TechStock v2.0")
        self.root.geometry("860x740")
        self.root.minsize(700, 560)
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
        x = max(0, (self.root.winfo_screenwidth() // 2) - 430)
        y = max(0, (self.root.winfo_screenheight() // 2) - 370)
        self.root.geometry(f"+{x}+{y}")

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        mode = "empaquetado" if _FROZEN else "desarrollo"
        self._log(f"TechStock v2.0 \u2014 Gestor de servidor ({mode})", "OK")
        if _FROZEN:
            self._log(f"Directorio: {BASE_DIR}", "INFO")
        else:
            self._log(f"Python: {VENV_PYTHON}", "INFO")
        pg_label = PG_BIN if os.path.isdir(PG_BIN) else "no encontrado (PG externo)"
        self._log(f"PostgreSQL: {pg_label}", "INFO")
        self._log(f"Datos: {PG_DATA}", "INFO")

    # ────────────────────────────────────────────────────────
    #  UI
    # ────────────────────────────────────────────────────────

    def _build_ui(self):
        root = self.root

        # ── Header ──
        header = tk.Frame(root, bg=BG_DARK)
        header.pack(fill="x", padx=24, pady=(18, 6))

        left = tk.Frame(header, bg=BG_DARK)
        left.pack(side="left")

        tk.Label(left, text="\u2b22", font=("Segoe UI", 28), fg=ACCENT,
                 bg=BG_DARK).pack(side="left", padx=(0, 10))

        titles = tk.Frame(left, bg=BG_DARK)
        titles.pack(side="left")
        tk.Label(titles, text="TechStock", font=("Segoe UI", 18, "bold"),
                 fg=TEXT_PRIMARY, bg=BG_DARK).pack(anchor="w")
        tk.Label(titles, text="Sistema de Inventario v2.0",
                 font=("Segoe UI", 9), fg=TEXT_SECONDARY,
                 bg=BG_DARK).pack(anchor="w")

        # ── Divider ──
        tk.Frame(root, bg=BORDER, height=1).pack(fill="x", padx=24, pady=8)

        # ── Control Panel (Status + Buttons) ──
        control = tk.Frame(root, bg=BG_DARK)
        control.pack(fill="x", padx=24, pady=4)

        # Left: status indicators
        st = tk.Frame(control, bg=BG_DARK)
        st.pack(side="left")

        # PostgreSQL status
        pg_frame = tk.Frame(st, bg=BG_DARK)
        pg_frame.pack(side="left", padx=(0, 18))
        self._pg_dot = tk.Label(pg_frame, text="\u25cf", font=("Segoe UI", 11),
                                fg=DANGER, bg=BG_DARK)
        self._pg_dot.pack(side="left", padx=(0, 5))
        self._pg_status_var = tk.StringVar(value="PostgreSQL detenido")
        tk.Label(pg_frame, textvariable=self._pg_status_var,
                 font=("Segoe UI", 9), fg=TEXT_SECONDARY,
                 bg=BG_DARK).pack(side="left")

        # Server status
        sv_frame = tk.Frame(st, bg=BG_DARK)
        sv_frame.pack(side="left", padx=(0, 12))
        self._dot = tk.Label(sv_frame, text="\u25cf", font=("Segoe UI", 11),
                             fg=DANGER, bg=BG_DARK)
        self._dot.pack(side="left", padx=(0, 5))
        self._status_var = tk.StringVar(value="Servidor detenido")
        tk.Label(sv_frame, textvariable=self._status_var,
                 font=("Segoe UI", 9), fg=TEXT_SECONDARY,
                 bg=BG_DARK).pack(side="left")

        # URL link
        self._url_var = tk.StringVar(value="")
        self._url_lbl = tk.Label(st, textvariable=self._url_var,
                                 font=("Segoe UI", 10, "underline"), fg=ACCENT,
                                 bg=BG_DARK, cursor="hand2")
        self._url_lbl.pack(side="left", padx=(8, 0))
        self._url_lbl.bind("<Button-1>",
                           lambda e: self._open_browser() if self.running else None)

        # Right: buttons
        btns = tk.Frame(control, bg=BG_DARK)
        btns.pack(side="right")

        self._btn_start = tk.Button(
            btns, text="\u25b6  Iniciar", font=("Segoe UI", 10, "bold"),
            bg=ACCENT, fg="white", activebackground=ACCENT_HOVER,
            activeforeground="white", relief="flat", padx=18, pady=7,
            cursor="hand2", command=self._on_start)
        self._btn_start.pack(side="left", padx=3)

        self._btn_stop = tk.Button(
            btns, text="\u25a0  Detener", font=("Segoe UI", 10, "bold"),
            bg="#3a3a55", fg=TEXT_SECONDARY, activebackground="#4a4a65",
            activeforeground="white", relief="flat", padx=18, pady=7,
            cursor="hand2", command=self._on_stop, state="disabled")
        self._btn_stop.pack(side="left", padx=3)

        self._btn_web = tk.Button(
            btns, text="\U0001f310 Abrir", font=("Segoe UI", 10),
            bg="#1e1e35", fg=TEXT_SECONDARY, activebackground="#2e2e50",
            activeforeground="white", relief="flat", padx=14, pady=7,
            cursor="hand2", command=self._open_browser, state="disabled")
        self._btn_web.pack(side="left", padx=3)

        # ── Divider ──
        tk.Frame(root, bg=BORDER, height=1).pack(fill="x", padx=24, pady=8)

        # ── Notebook (Tabs): Log + Config ──
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Dark.TNotebook", background=BG_DARK, borderwidth=0)
        style.configure("Dark.TNotebook.Tab",
                        background=BG_CARD, foreground=TEXT_SECONDARY,
                        padding=[14, 6], font=("Segoe UI", 9))
        style.map("Dark.TNotebook.Tab",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", "white")])
        style.configure("Dark.TFrame", background=BG_DARK)

        self._notebook = ttk.Notebook(root, style="Dark.TNotebook")
        self._notebook.pack(fill="both", expand=True, padx=24, pady=(0, 4))

        # ── Tab 1: Log ──
        log_tab = ttk.Frame(self._notebook, style="Dark.TFrame")
        self._notebook.add(log_tab, text="  \U0001f4cb Registro  ")

        # Log header
        lh = tk.Frame(log_tab, bg=BG_DARK)
        lh.pack(fill="x", pady=(8, 4), padx=4)

        tk.Label(lh, text="Registro de actividad del servidor",
                 font=("Segoe UI", 9), fg=TEXT_MUTED,
                 bg=BG_DARK).pack(side="left")

        tk.Button(lh, text="Limpiar", font=("Segoe UI", 8),
                  bg=BG_CARD, fg=TEXT_MUTED, activebackground="#2a2a45",
                  relief="flat", padx=10, pady=2, cursor="hand2",
                  command=self._clear_log).pack(side="right")

        # Log area
        log_border = tk.Frame(log_tab, bg=BORDER)
        log_border.pack(fill="both", expand=True, padx=4, pady=(0, 4))

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

        # ── Tab 2: Configuracion ──
        config_tab = ttk.Frame(self._notebook, style="Dark.TFrame")
        self._notebook.add(config_tab, text="  \u2699 Configuraci\u00f3n  ")
        self._build_config_tab(config_tab)

        # ── Footer ──
        ft = tk.Frame(root, bg=BG_DARK)
        ft.pack(fill="x", padx=24, pady=(0, 8))
        self._footer_var = tk.StringVar(
            value=f"Puerto web: {WEB_PORT}  |  Puerto PG: {PG_PORT}  |  Detenido"
        )
        tk.Label(ft, textvariable=self._footer_var,
                 font=("Segoe UI", 8), fg=TEXT_MUTED, bg=BG_DARK).pack(side="left")
        tk.Label(ft, text="TechStock \u00a9 2026",
                 font=("Segoe UI", 8), fg=TEXT_MUTED,
                 bg=BG_DARK).pack(side="right")

    def _build_config_tab(self, parent):
        """Construye la pestana de configuracion."""
        canvas = tk.Canvas(parent, bg=BG_DARK, highlightthickness=0)
        canvas.pack(fill="both", expand=True, padx=4, pady=8)

        inner = tk.Frame(canvas, bg=BG_DARK)
        canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(canvas.find_all()[0], width=e.width)

        canvas.bind("<Configure>", _on_configure)

        # -- Seccion: Servidor --
        self._section(inner, "Servidor Web", row=0)

        self._config_label(inner, "Puerto web:", 1)
        self._web_port_var = tk.StringVar(value=str(WEB_PORT))
        self._config_entry(inner, self._web_port_var, 1)

        self._config_label(inner, "Host:", 2)
        self._host_var = tk.StringVar(value="0.0.0.0")
        self._config_entry(inner, self._host_var, 2)

        self._auto_browser_var = tk.BooleanVar(value=True)
        cb = tk.Checkbutton(
            inner, text="Abrir navegador automaticamente al iniciar",
            variable=self._auto_browser_var,
            font=("Segoe UI", 9), fg=TEXT_SECONDARY, bg=BG_DARK,
            selectcolor=BG_INPUT, activebackground=BG_DARK,
            activeforeground=TEXT_PRIMARY, highlightthickness=0,
        )
        cb.grid(row=3, column=0, columnspan=2, sticky="w", padx=16, pady=(8, 2))

        # -- Seccion: Base de Datos --
        self._section(inner, "Base de Datos (PostgreSQL)", row=5)

        self._config_label(inner, "Puerto PG:", 6)
        self._pg_port_var = tk.StringVar(value=PG_PORT)
        self._config_entry(inner, self._pg_port_var, 6)

        self._config_label(inner, "Usuario:", 7)
        self._pg_user_var = tk.StringVar(value=PG_USER)
        self._config_entry(inner, self._pg_user_var, 7)

        self._config_label(inner, "Base de datos:", 8)
        self._pg_db_var = tk.StringVar(value=PG_DB)
        self._config_entry(inner, self._pg_db_var, 8)

        self._config_label(inner, "Password:", 9)
        self._pg_pass_var = tk.StringVar(value=PG_PASSWORD)
        e = self._config_entry(inner, self._pg_pass_var, 9)
        e.configure(show="\u2022")

        # -- Seccion: Rutas --
        self._section(inner, "Rutas del Sistema", row=11)

        self._config_label(inner, "Directorio app:", 12)
        tk.Label(inner, text=BASE_DIR, font=("Consolas", 8),
                 fg=TEXT_MUTED, bg=BG_DARK, anchor="w").grid(
            row=12, column=1, sticky="w", padx=(0, 16), pady=3)

        self._config_label(inner, "Datos PG:", 13)
        tk.Label(inner, text=PG_DATA, font=("Consolas", 8),
                 fg=TEXT_MUTED, bg=BG_DARK, anchor="w").grid(
            row=13, column=1, sticky="w", padx=(0, 16), pady=3)

        pg_portable = "Si" if os.path.isdir(PG_BIN) else "No (PostgreSQL externo)"
        self._config_label(inner, "PG portable:", 14)
        tk.Label(inner, text=pg_portable, font=("Segoe UI", 9),
                 fg=SUCCESS if os.path.isdir(PG_BIN) else WARNING,
                 bg=BG_DARK, anchor="w").grid(
            row=14, column=1, sticky="w", padx=(0, 16), pady=3)

        # -- Nota --
        note = tk.Label(
            inner,
            text="Nota: Los cambios de puerto y credenciales aplican al reiniciar el servidor.",
            font=("Segoe UI", 8, "italic"), fg=TEXT_MUTED, bg=BG_DARK,
        )
        note.grid(row=16, column=0, columnspan=2, sticky="w", padx=16, pady=(16, 4))

        inner.columnconfigure(1, weight=1)

    def _section(self, parent, title, row):
        """Titulo de seccion en config."""
        lbl = tk.Label(parent, text=title, font=("Segoe UI", 11, "bold"),
                       fg=TEXT_PRIMARY, bg=BG_DARK)
        lbl.grid(row=row, column=0, columnspan=2, sticky="w", padx=16, pady=(14, 4))
        sep = tk.Frame(parent, bg=BORDER, height=1)
        sep.grid(row=row, column=0, columnspan=2, sticky="ew", padx=16, pady=(36, 0))

    def _config_label(self, parent, text, row):
        lbl = tk.Label(parent, text=text, font=("Segoe UI", 9),
                       fg=TEXT_SECONDARY, bg=BG_DARK, anchor="e")
        lbl.grid(row=row, column=0, sticky="e", padx=(16, 8), pady=3)

    def _config_entry(self, parent, var, row):
        e = tk.Entry(
            parent, textvariable=var, font=("Consolas", 9),
            bg=BG_INPUT, fg=TEXT_PRIMARY, insertbackground=TEXT_PRIMARY,
            relief="flat", highlightthickness=1, highlightcolor=ACCENT,
            highlightbackground=BORDER,
        )
        e.grid(row=row, column=1, sticky="ew", padx=(0, 16), pady=3, ipady=3)
        return e

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

    def _update_footer(self):
        state = "Activo" if self.running else "Detenido"
        port = self._web_port_var.get() if hasattr(self, "_web_port_var") else WEB_PORT
        pg_port = self._pg_port_var.get() if hasattr(self, "_pg_port_var") else PG_PORT
        self._footer_var.set(f"Puerto web: {port}  |  Puerto PG: {pg_port}  |  {state}")

    def _enable_running_ui(self):
        self._btn_start.config(state="disabled")
        self._btn_stop.config(state="normal", bg=DANGER, fg="white")
        self._btn_web.config(state="normal")
        self._update_footer()

    def _enable_stopped_ui(self):
        self.running = False
        self._starting = False
        self._url_var.set("")
        self._btn_start.config(state="normal")
        self._btn_stop.config(state="disabled", bg="#3a3a55", fg=TEXT_SECONDARY)
        self._btn_web.config(state="disabled")
        self._update_footer()

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
    #  Read config from UI
    # ────────────────────────────────────────────────────────

    def _read_config(self):
        """Lee la configuracion actual de los campos de la UI."""
        global PG_PORT, PG_USER, PG_DB, PG_PASSWORD, WEB_PORT
        try:
            WEB_PORT = int(self._web_port_var.get().strip() or 8000)
        except ValueError:
            WEB_PORT = 8000
        try:
            PG_PORT = self._pg_port_var.get().strip() or "5433"
        except Exception:
            PG_PORT = "5433"
        PG_USER = self._pg_user_var.get().strip() or "techstock"
        PG_DB = self._pg_db_var.get().strip() or "techstock"
        PG_PASSWORD = self._pg_pass_var.get().strip() or "techstock"
        self._auto_browser = self._auto_browser_var.get()

    # ────────────────────────────────────────────────────────
    #  PostgreSQL management
    # ────────────────────────────────────────────────────────

    def _pg_exists(self):
        return os.path.isfile(_pg_cmd("pg_ctl"))

    def _pg_init_db(self):
        if os.path.exists(os.path.join(PG_DATA, "PG_VERSION")):
            return True

        self.root.after(0, self._log, "Inicializando base de datos PostgreSQL...", "INFO")
        os.makedirs(PG_DATA, exist_ok=True)

        try:
            initdb = _pg_cmd("initdb")
            env = os.environ.copy()
            env["PGDATA"] = PG_DATA
            result = subprocess.run(
                [initdb, "-D", PG_DATA, "-U", "postgres", "-E", "UTF8",
                 "--locale=C", "--auth=trust"],
                capture_output=True, text=True, timeout=120, env=env,
                creationflags=_SUBPROCESS_FLAGS,
            )
            if result.returncode != 0:
                self.root.after(0, self._log, f"Error initdb: {result.stderr.strip()}", "ERROR")
                return False
            self.root.after(0, self._log, "Cluster PostgreSQL inicializado.", "OK")

            # Configurar puerto en postgresql.conf
            conf_path = os.path.join(PG_DATA, "postgresql.conf")
            with open(conf_path, "a") as f:
                f.write(f"\n# TechStock config\n")
                f.write(f"port = {PG_PORT}\n")
                f.write(f"listen_addresses = 'localhost'\n")
                f.write(f"log_destination = 'stderr'\n")
                f.write(f"logging_collector = off\n")
                f.write(f"shared_buffers = 128MB\n")
                f.write(f"fsync = on\n")
                f.write(f"synchronous_commit = off\n")

            return True
        except subprocess.TimeoutExpired:
            self.root.after(0, self._log, "Timeout al inicializar PostgreSQL (>120s)", "ERROR")
            return False
        except Exception as e:
            self.root.after(0, self._log, f"Error al inicializar: {e}", "ERROR")
            return False

    def _pg_start(self):
        if not self._pg_exists():
            self.root.after(0, self._log, "PostgreSQL portable no encontrado en pgsql/", "ERROR")
            return False

        if not self._pg_init_db():
            return False

        self.root.after(0, self._set_pg_status, "Iniciando PostgreSQL...", WARNING)
        self.root.after(0, self._log, "Iniciando PostgreSQL...", "INFO")

        try:
            pg_ctl = _pg_cmd("pg_ctl")
            env = os.environ.copy()
            env["PGDATA"] = PG_DATA
            result = subprocess.run(
                [pg_ctl, "start", "-D", PG_DATA, "-l", PG_LOG,
                 "-w", "-t", "60",
                 "-o", f"-p {PG_PORT}"],
                capture_output=True, text=True, timeout=90, env=env,
                creationflags=_SUBPROCESS_FLAGS,
            )
            if result.returncode != 0:
                err = result.stderr.strip() or result.stdout.strip()
                self.root.after(0, self._log, f"Error al iniciar PG: {err}", "ERROR")
                self.root.after(0, self._set_pg_status, "Error PostgreSQL", DANGER)
                return False

        except subprocess.TimeoutExpired:
            self.root.after(0, self._log, "Timeout al iniciar PostgreSQL (>90s)", "ERROR")
            self.root.after(0, self._set_pg_status, "Timeout PostgreSQL", DANGER)
            return False
        except Exception as e:
            self.root.after(0, self._log, f"Error: {e}", "ERROR")
            self.root.after(0, self._set_pg_status, "Error PostgreSQL", DANGER)
            return False

        self.pg_running = True
        self.root.after(0, self._set_pg_status, "PostgreSQL activo", SUCCESS)
        self.root.after(0, self._log, f"PostgreSQL iniciado en puerto {PG_PORT}.", "OK")

        self._pg_ensure_db()
        return True

    def _pg_ensure_db(self):
        psql = _pg_cmd("psql")
        createdb = _pg_cmd("createdb")
        env = os.environ.copy()
        env["PGPORT"] = PG_PORT

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
                self.root.after(0, self._log, f"Usuario '{PG_USER}' creado.", "OK")
        except Exception as e:
            self.root.after(0, self._log, f"Aviso creando usuario: {e}", "WARN")

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
                self.root.after(0, self._log, f"Base de datos '{PG_DB}' creada.", "OK")
        except Exception as e:
            self.root.after(0, self._log, f"Aviso creando BD: {e}", "WARN")

    def _pg_stop(self):
        if not self.pg_running:
            return

        self.root.after(0, self._log, "Deteniendo PostgreSQL...", "WARN")
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
        self.root.after(0, self._set_pg_status, "PostgreSQL detenido", DANGER)
        self.root.after(0, self._log, "PostgreSQL detenido.", "INFO")

    # ────────────────────────────────────────────────────────
    #  Database connection check
    # ────────────────────────────────────────────────────────

    def _check_db_connection(self):
        if _FROZEN:
            return self._check_db_inprocess()
        else:
            return self._check_db_subprocess()

    def _check_db_inprocess(self):
        try:
            from sqlalchemy import text as sa_text
            from database import engine
            with engine.connect() as conn:
                conn.execute(sa_text("SELECT 1"))
            return True
        except Exception as e:
            self.root.after(0, self._log, f"Error DB: {e}", "ERROR")
            return False

    def _check_db_subprocess(self):
        try:
            chk = subprocess.run(
                [VENV_PYTHON, "-c",
                 "from database import engine; c=engine.connect(); c.close()"],
                cwd=BASE_DIR, capture_output=True, text=True, timeout=15,
                creationflags=_SUBPROCESS_FLAGS,
            )
            if chk.returncode != 0:
                err = chk.stderr.strip() or chk.stdout.strip() or "Sin detalle"
                self.root.after(0, self._log, f"Error DB: {err}", "ERROR")
                return False
            return True
        except Exception as e:
            self.root.after(0, self._log, f"Excepcion: {e}", "ERROR")
            return False

    # ────────────────────────────────────────────────────────
    #  Server control — NON-BLOCKING
    # ────────────────────────────────────────────────────────

    def _on_start(self):
        """Handler del boton Iniciar — lanza startup en background."""
        if self.running or self._starting:
            return
        self._starting = True
        self._read_config()
        self._btn_start.config(state="disabled")
        self._notebook.select(0)  # Cambiar a tab de log
        threading.Thread(target=self._start_all_bg, daemon=True).start()

    def _start_all_bg(self):
        """Ejecuta toda la secuencia de inicio en un hilo background."""
        try:
            # 1. Iniciar PostgreSQL
            if self._pg_exists():
                if not self._pg_start():
                    self.root.after(0, self._on_start_failed, "No se pudo iniciar PostgreSQL")
                    return
            else:
                self.root.after(0, self._set_pg_status, "Verificando PG externo...", WARNING)
                self.root.after(0, self._log, "PG portable no encontrado, verificando PG externo...", "INFO")

            # 2. Configurar DATABASE_URL
            db_url = os.environ.get("DATABASE_URL", "").strip()
            if not db_url and self.pg_running:
                os.environ["DATABASE_URL"] = (
                    f"postgresql://{PG_USER}:{PG_PASSWORD}@localhost:{PG_PORT}/{PG_DB}"
                )

            # 3. Verificar conexion
            self.root.after(0, self._set_status, "Verificando conexion...", WARNING)
            self.root.after(0, self._log, "Verificando conexion a base de datos...", "INFO")

            if not self._check_db_connection():
                self.root.after(0, self._on_start_failed,
                                "No se pudo conectar a PostgreSQL.\nVerifique que este disponible.")
                return

            self.root.after(0, self._log, "Conexion a base de datos OK.", "OK")
            if not self.pg_running:
                self.root.after(0, self._set_pg_status, "PostgreSQL externo", SUCCESS)

            # 4. Iniciar servidor web
            self.root.after(0, self._set_status, "Iniciando servidor...", WARNING)
            self.root.after(0, self._log, f"Iniciando servidor en puerto {WEB_PORT}...", "INFO")

            # Cambiar al hilo principal para operaciones de UI/server
            self.root.after(0, self._launch_server)

        except Exception as e:
            self.root.after(0, self._on_start_failed, f"Error inesperado: {e}")

    def _on_start_failed(self, msg):
        """Callback cuando el inicio falla."""
        self._set_status("Error al iniciar", DANGER)
        self._log(msg, "ERROR")
        self._enable_stopped_ui()

    def _launch_server(self):
        """Lanza el servidor web (llamado desde hilo principal)."""
        if _FROZEN:
            self._start_server_inprocess()
        else:
            self._start_server_subprocess()

    def _start_server_inprocess(self):
        try:
            import uvicorn

            handler = _TkLogHandler(self)
            handler.setFormatter(logging.Formatter("%(message)s"))
            for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "techstock"):
                lgr = logging.getLogger(logger_name)
                lgr.addHandler(handler)
                lgr.setLevel(logging.INFO)

            config = uvicorn.Config(
                "main:app",
                host=self._host_var.get().strip() or "0.0.0.0",
                port=WEB_PORT,
                log_level="info",
                access_log=True,
            )
            self._server = uvicorn.Server(config)

            self.running = True
            self._enable_running_ui()

            threading.Thread(target=self._run_server, daemon=True).start()
            threading.Thread(target=self._wait_ready, daemon=True).start()

        except Exception as e:
            self._on_start_failed(f"No se pudo iniciar: {e}")

    def _run_server(self):
        try:
            self._server.run()
        except Exception as e:
            self.root.after(0, self._log, f"Error servidor: {e}", "ERROR")

        if self.running and not self._stopping:
            self.root.after(0, self._unexpected_stop)

    def _start_server_subprocess(self):
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
            self._on_start_failed(f"No se pudo iniciar: {e}")
            return

        self.running = True
        self._enable_running_ui()

        threading.Thread(target=self._read_output, daemon=True).start()
        threading.Thread(target=self._wait_ready, daemon=True).start()

    def _read_output(self):
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

        if self.running and not self._stopping:
            self.root.after(0, self._unexpected_stop)

    def _wait_ready(self):
        import urllib.request
        for _ in range(45):
            if not self.running:
                return
            try:
                urllib.request.urlopen(f"http://localhost:{WEB_PORT}", timeout=2)
                self.root.after(0, self._server_ready)
                return
            except Exception:
                time.sleep(1)
        self.root.after(0, lambda: self._set_status(
            "Iniciado (verificar puerto)", WARNING))

    def _server_ready(self):
        self._set_status("Servidor activo", SUCCESS)
        self._url_var.set(f"http://localhost:{WEB_PORT}")
        self._log(f"Servidor listo en http://localhost:{WEB_PORT}", "OK")
        self._update_footer()
        if self._auto_browser:
            self._open_browser()

    def _unexpected_stop(self):
        self._set_status("Servidor detenido inesperadamente", DANGER)
        self._log("El servidor se detuvo inesperadamente.", "ERROR")
        self._enable_stopped_ui()

    def _on_stop(self):
        """Handler del boton Detener — lanza stop en background."""
        if not self.running and not self.pg_running:
            return
        self._btn_stop.config(state="disabled")
        threading.Thread(target=self._stop_all_bg, daemon=True).start()

    def _stop_all_bg(self):
        """Detiene todo en hilo background para no trabar la UI."""
        self._stopping = True

        # 1. Detener servidor web
        if _FROZEN and self._server:
            self.root.after(0, self._log, "Deteniendo servidor...", "WARN")
            self._server.should_exit = True
            time.sleep(2)
            self._server = None
        elif self.process:
            self.root.after(0, self._log, "Deteniendo servidor...", "WARN")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None

        self.root.after(0, self._set_status, "Servidor detenido", DANGER)
        self.root.after(0, self._log, "Servidor detenido.", "INFO")

        # 2. Detener PostgreSQL portable
        if self.pg_running:
            self._pg_stop()

        self.root.after(0, self._enable_stopped_ui)

    def _open_browser(self):
        if self.running:
            webbrowser.open(f"http://localhost:{WEB_PORT}")
            self._log("Navegador abierto.", "INFO")

    def _on_close(self):
        if self.running or self.pg_running:
            if messagebox.askyesno(
                "Cerrar TechStock",
                "El servidor esta corriendo.\n\u00bfDetenerlo y salir?"):
                self._stopping = True
                # Detener en background y luego cerrar
                def _close_after_stop():
                    self._stop_all_bg()
                    self.root.after(0, self.root.destroy)
                threading.Thread(target=_close_after_stop, daemon=True).start()
            else:
                return
        else:
            self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = TechStockLauncher()
    app.run()
