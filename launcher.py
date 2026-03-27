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
import socket
import tkinter as tk
from tkinter import ttk, messagebox
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


def _get_local_ips():
    """Obtiene todas las IPs IPv4 locales (no-loopback)."""
    ips = set()
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127."):
                ips.add(ip)
    except Exception:
        pass
    # Fallback: truco UDP para obtener la IP principal
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if not ip.startswith("127."):
            ips.add(ip)
    except Exception:
        pass
    return sorted(ips)


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
        self._start_time = None

        # Log batching
        self._log_buffer = []
        self._flush_pending = False

        self.root = tk.Tk()
        self.root.title("TechStock v3.0")
        self.root.geometry("900x780")
        self.root.minsize(720, 580)
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
        x = max(0, (self.root.winfo_screenwidth() // 2) - 450)
        y = max(0, (self.root.winfo_screenheight() // 2) - 390)
        self.root.geometry(f"+{x}+{y}")

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        mode = "empaquetado" if _FROZEN else "desarrollo"
        self._log(f"TechStock v3.0 \u2014 Gestor de servidor ({mode})", "OK")
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
        tk.Label(titles, text="Sistema de Inventario v3.0",
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

        # ── Notebook (Tabs): Log + Info + Config ──
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

        # ── Tab 2: Server Info ──
        info_tab = ttk.Frame(self._notebook, style="Dark.TFrame")
        self._notebook.add(info_tab, text="  \U0001f4e1 Servidor  ")
        self._build_info_tab(info_tab)

        # ── Tab 3: Configuracion ──
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

    # ────────────────────────────────────────────────────────
    #  Server Info Tab
    # ────────────────────────────────────────────────────────

    def _build_info_tab(self, parent):
        """Construye la pestana de informacion del servidor."""
        canvas = tk.Canvas(parent, bg=BG_DARK, highlightthickness=0)
        scrollbar = tk.Scrollbar(parent, command=canvas.yview,
                                 bg=BG_CARD, troughcolor=BG_DARK,
                                 highlightthickness=0, borderwidth=0)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True, padx=4, pady=8)

        inner = tk.Frame(canvas, bg=BG_DARK)
        self._info_canvas_window = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(self._info_canvas_window, width=e.width)

        canvas.bind("<Configure>", _on_configure)

        # ── Seccion: Estado del Servidor ──
        self._info_section(inner, "\U0001f5a5  Estado del Servidor", 0)

        self._info_label(inner, "Estado:", 1)
        self._info_status_dot = tk.Label(inner, text="\u25cf", font=("Segoe UI", 10),
                                         fg=DANGER, bg=BG_DARK)
        self._info_status_dot.grid(row=1, column=1, sticky="w", padx=(0, 0), pady=3)
        self._info_status_var = tk.StringVar(value="Detenido")
        tk.Label(inner, textvariable=self._info_status_var,
                 font=("Segoe UI", 9, "bold"), fg=TEXT_PRIMARY,
                 bg=BG_DARK).grid(row=1, column=2, sticky="w", padx=(4, 16), pady=3)

        self._info_label(inner, "URL local:", 2)
        self._info_url_var = tk.StringVar(value="--")
        url_frame = tk.Frame(inner, bg=BG_DARK)
        url_frame.grid(row=2, column=1, columnspan=2, sticky="w", pady=3)
        self._info_url_lbl = tk.Label(url_frame, textvariable=self._info_url_var,
                                      font=("Consolas", 10), fg=ACCENT,
                                      bg=BG_DARK, cursor="hand2")
        self._info_url_lbl.pack(side="left")
        self._info_url_lbl.bind("<Button-1>",
                                lambda e: self._open_browser() if self.running else None)
        self._btn_copy_local = tk.Button(
            url_frame, text="\U0001f4cb", font=("Segoe UI", 8),
            bg=BG_CARD, fg=TEXT_MUTED, activebackground="#2a2a45",
            relief="flat", padx=6, pady=1, cursor="hand2",
            command=lambda: self._copy_to_clipboard(self._info_url_var.get()))
        self._btn_copy_local.pack(side="left", padx=(6, 0))

        self._info_label(inner, "Hora inicio:", 3)
        self._info_start_var = tk.StringVar(value="--")
        tk.Label(inner, textvariable=self._info_start_var,
                 font=("Segoe UI", 9), fg=TEXT_PRIMARY,
                 bg=BG_DARK).grid(row=3, column=1, columnspan=2, sticky="w", pady=3)

        self._info_label(inner, "Host:", 4)
        self._info_host_var = tk.StringVar(value="0.0.0.0")
        tk.Label(inner, textvariable=self._info_host_var,
                 font=("Consolas", 9), fg=TEXT_MUTED,
                 bg=BG_DARK).grid(row=4, column=1, columnspan=2, sticky="w", pady=3)

        self._info_label(inner, "PID:", 5)
        self._info_pid_var = tk.StringVar(value="--")
        tk.Label(inner, textvariable=self._info_pid_var,
                 font=("Consolas", 9), fg=TEXT_MUTED,
                 bg=BG_DARK).grid(row=5, column=1, columnspan=2, sticky="w", pady=3)

        # ── Seccion: Acceso de Red ──
        self._info_section(inner, "\U0001f4e1  Acceso de Red", 7)

        self._info_label(inner, "Hostname:", 8)
        hostname = "desconocido"
        try:
            hostname = socket.gethostname()
        except Exception:
            pass
        self._info_hostname_var = tk.StringVar(value=hostname)
        tk.Label(inner, textvariable=self._info_hostname_var,
                 font=("Consolas", 9), fg=TEXT_PRIMARY,
                 bg=BG_DARK).grid(row=8, column=1, columnspan=2, sticky="w", pady=3)

        # Nota de acceso
        note_frame = tk.Frame(inner, bg=BG_CARD, padx=12, pady=8)
        note_frame.grid(row=9, column=0, columnspan=3, sticky="ew", padx=16, pady=(8, 4))
        tk.Label(note_frame,
                 text="\U0001f4f6  Dispositivos en la misma red WiFi/LAN pueden acceder\n"
                      "     al sistema usando cualquiera de estas direcciones:",
                 font=("Segoe UI", 9), fg=TEXT_SECONDARY, bg=BG_CARD,
                 justify="left").pack(anchor="w")

        # Frame dinamico para IPs
        self._ips_frame = tk.Frame(inner, bg=BG_DARK)
        self._ips_frame.grid(row=10, column=0, columnspan=3, sticky="ew", padx=16, pady=(4, 2))

        # Boton actualizar IPs
        refresh_frame = tk.Frame(inner, bg=BG_DARK)
        refresh_frame.grid(row=11, column=0, columnspan=3, sticky="w", padx=16, pady=(2, 4))
        tk.Button(refresh_frame, text="\u21bb  Actualizar IPs", font=("Segoe UI", 8),
                  bg=BG_CARD, fg=TEXT_SECONDARY, activebackground="#2a2a45",
                  relief="flat", padx=10, pady=3, cursor="hand2",
                  command=self._refresh_ips).pack(side="left")

        # ── Seccion: Base de Datos ──
        self._info_section(inner, "\U0001f5c4  Base de Datos", 13)

        self._info_label(inner, "Estado:", 14)
        self._info_db_dot = tk.Label(inner, text="\u25cf", font=("Segoe UI", 10),
                                     fg=DANGER, bg=BG_DARK)
        self._info_db_dot.grid(row=14, column=1, sticky="w", padx=(0, 0), pady=3)
        self._info_db_status_var = tk.StringVar(value="Desconectado")
        tk.Label(inner, textvariable=self._info_db_status_var,
                 font=("Segoe UI", 9, "bold"), fg=TEXT_PRIMARY,
                 bg=BG_DARK).grid(row=14, column=2, sticky="w", padx=(4, 16), pady=3)

        self._info_label(inner, "Puerto PG:", 15)
        self._info_pg_port_var = tk.StringVar(value=PG_PORT)
        tk.Label(inner, textvariable=self._info_pg_port_var,
                 font=("Consolas", 9), fg=TEXT_PRIMARY,
                 bg=BG_DARK).grid(row=15, column=1, columnspan=2, sticky="w", pady=3)

        self._info_label(inner, "Base de datos:", 16)
        self._info_db_name_var = tk.StringVar(value=PG_DB)
        tk.Label(inner, textvariable=self._info_db_name_var,
                 font=("Consolas", 9), fg=TEXT_PRIMARY,
                 bg=BG_DARK).grid(row=16, column=1, columnspan=2, sticky="w", pady=3)

        self._info_label(inner, "Conexion:", 17)
        self._info_db_url_var = tk.StringVar(value="--")
        tk.Label(inner, textvariable=self._info_db_url_var,
                 font=("Consolas", 8), fg=TEXT_MUTED,
                 bg=BG_DARK, wraplength=500, justify="left"
                 ).grid(row=17, column=1, columnspan=2, sticky="w", pady=3)

        inner.columnconfigure(2, weight=1)

        # Poblar IPs iniciales
        self._refresh_ips()

    def _info_section(self, parent, title, row):
        """Titulo de seccion en info tab."""
        lbl = tk.Label(parent, text=title, font=("Segoe UI", 11, "bold"),
                       fg=TEXT_PRIMARY, bg=BG_DARK)
        lbl.grid(row=row, column=0, columnspan=3, sticky="w", padx=16, pady=(14, 4))
        sep = tk.Frame(parent, bg=BORDER, height=1)
        sep.grid(row=row, column=0, columnspan=3, sticky="ew", padx=16, pady=(36, 0))

    def _info_label(self, parent, text, row):
        """Label de campo en info tab."""
        lbl = tk.Label(parent, text=text, font=("Segoe UI", 9),
                       fg=TEXT_SECONDARY, bg=BG_DARK, anchor="e")
        lbl.grid(row=row, column=0, sticky="e", padx=(16, 8), pady=3)

    def _refresh_ips(self):
        """Actualiza la lista de IPs en el panel de info."""
        # Limpiar frame
        for w in self._ips_frame.winfo_children():
            w.destroy()

        ips = _get_local_ips()
        port = WEB_PORT

        if not ips:
            tk.Label(self._ips_frame,
                     text="  \u26a0  No se detectaron interfaces de red activas",
                     font=("Segoe UI", 9), fg=WARNING, bg=BG_DARK
                     ).pack(anchor="w", pady=2)
            return

        for ip in ips:
            url = f"http://{ip}:{port}"
            row = tk.Frame(self._ips_frame, bg=BG_DARK)
            row.pack(fill="x", pady=2)

            tk.Label(row, text="\u25cf", font=("Segoe UI", 8), fg=SUCCESS,
                     bg=BG_DARK).pack(side="left", padx=(4, 6))

            url_lbl = tk.Label(row, text=url, font=("Consolas", 10, "bold"),
                               fg=ACCENT, bg=BG_DARK, cursor="hand2")
            url_lbl.pack(side="left")
            url_lbl.bind("<Button-1>", lambda e, u=url: webbrowser.open(u)
                         if self.running else None)

            tk.Label(row, text=f"  ({ip})", font=("Segoe UI", 8),
                     fg=TEXT_MUTED, bg=BG_DARK).pack(side="left")

            tk.Button(row, text="\U0001f4cb", font=("Segoe UI", 8),
                      bg=BG_CARD, fg=TEXT_MUTED, activebackground="#2a2a45",
                      relief="flat", padx=5, pady=0, cursor="hand2",
                      command=lambda u=url: self._copy_to_clipboard(u)
                      ).pack(side="left", padx=(6, 0))

        # Localhost siempre
        row = tk.Frame(self._ips_frame, bg=BG_DARK)
        row.pack(fill="x", pady=2)
        tk.Label(row, text="\u25cf", font=("Segoe UI", 8), fg=TEXT_MUTED,
                 bg=BG_DARK).pack(side="left", padx=(4, 6))
        localhost_url = f"http://localhost:{port}"
        lh_lbl = tk.Label(row, text=localhost_url, font=("Consolas", 10),
                          fg=TEXT_SECONDARY, bg=BG_DARK, cursor="hand2")
        lh_lbl.pack(side="left")
        lh_lbl.bind("<Button-1>", lambda e: self._open_browser() if self.running else None)
        tk.Label(row, text="  (solo este equipo)", font=("Segoe UI", 8),
                 fg=TEXT_MUTED, bg=BG_DARK).pack(side="left")

    def _copy_to_clipboard(self, text):
        """Copia texto al portapapeles."""
        if not text or text == "--":
            return
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self._log(f"Copiado al portapapeles: {text}", "INFO")
        except Exception:
            pass

    def _update_info_panel(self, running=False):
        """Actualiza el panel de info con el estado actual."""
        port = WEB_PORT

        if running:
            self._info_status_var.set("Activo")
            self._info_status_dot.config(fg=SUCCESS)
            self._info_url_var.set(f"http://localhost:{port}")
            self._info_host_var.set(self._host_var.get().strip() or "0.0.0.0")
            self._info_start_var.set(
                self._start_time.strftime("%H:%M:%S - %d/%m/%Y") if self._start_time else "--")
            # PID
            if self.process:
                self._info_pid_var.set(str(self.process.pid))
            elif self._server:
                self._info_pid_var.set(str(os.getpid()))
            else:
                self._info_pid_var.set("--")
        else:
            self._info_status_var.set("Detenido")
            self._info_status_dot.config(fg=DANGER)
            self._info_url_var.set("--")
            self._info_host_var.set("--")
            self._info_start_var.set("--")
            self._info_pid_var.set("--")

        # DB info
        if self.pg_running or running:
            self._info_db_dot.config(fg=SUCCESS)
            self._info_db_status_var.set("Conectado")
        else:
            self._info_db_dot.config(fg=DANGER)
            self._info_db_status_var.set("Desconectado")

        self._info_pg_port_var.set(
            self._pg_port_var.get() if hasattr(self, "_pg_port_var") else PG_PORT)
        self._info_db_name_var.set(
            self._pg_db_var.get() if hasattr(self, "_pg_db_var") else PG_DB)

        db_url = os.environ.get("DATABASE_URL", "")
        if db_url:
            # Ocultar password en display
            display_url = db_url
            try:
                if "@" in db_url and ":" in db_url:
                    pre_at = db_url.split("@")[0]
                    post_at = db_url.split("@", 1)[1]
                    if ":" in pre_at:
                        scheme_user = pre_at.rsplit(":", 1)[0]
                        display_url = f"{scheme_user}:****@{post_at}"
            except Exception:
                pass
            self._info_db_url_var.set(display_url)
        else:
            self._info_db_url_var.set("--")

        # Refrescar IPs
        self._refresh_ips()

    # ────────────────────────────────────────────────────────
    #  Config Tab
    # ────────────────────────────────────────────────────────

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
    #  Logging (batched)
    # ────────────────────────────────────────────────────────

    def _log(self, message, level="INFO"):
        """Agrega mensaje al buffer y programa flush."""
        ts = datetime.now().strftime("%H:%M:%S")
        tag = level if level in ("INFO", "WARN", "ERROR", "OK", "HTTP") else "INFO"
        self._log_buffer.append((ts, tag, message))
        if not self._flush_pending:
            self._flush_pending = True
            self.root.after(50, self._flush_log)

    def _flush_log(self):
        """Vacia el buffer de log al widget Text en una sola operacion."""
        self._flush_pending = False
        if not self._log_buffer:
            return

        buf = self._log_buffer[:]
        self._log_buffer.clear()

        self._log_text.configure(state="normal")
        for ts, tag, message in buf:
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
        self._update_info_panel(running=False)

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

    def _pg_env(self):
        """Retorna env dict con PGDATA y PATH configurados."""
        env = os.environ.copy()
        env["PGDATA"] = PG_DATA
        env["PGPORT"] = PG_PORT
        env["PGCTLTIMEOUT"] = "120"
        # Agregar bin/ y lib/ de PG al PATH para que encuentre DLLs
        pg_paths = PG_BIN + ";" + os.path.join(PG_DIR, "lib")
        env["PATH"] = pg_paths + ";" + env.get("PATH", "")
        return env

    def _pg_exists(self):
        return os.path.isfile(_pg_cmd("pg_ctl"))

    def _pg_read_log_tail(self, lines=15):
        """Lee las ultimas lineas del log de PostgreSQL para diagnostico."""
        try:
            if os.path.exists(PG_LOG):
                with open(PG_LOG, "r", errors="replace") as f:
                    all_lines = f.readlines()
                    tail = all_lines[-lines:] if len(all_lines) > lines else all_lines
                    return [l.rstrip() for l in tail if l.strip()]
        except Exception:
            pass
        return []

    def _pg_check_stale_pid(self):
        """Verifica y limpia postmaster.pid stale (crash anterior)."""
        pid_file = os.path.join(PG_DATA, "postmaster.pid")
        if not os.path.exists(pid_file):
            return False

        try:
            with open(pid_file, "r") as f:
                first_line = f.readline().strip()
                pid = int(first_line)

            # Verificar si el proceso sigue vivo
            import signal
            try:
                os.kill(pid, 0)  # signal 0 = check if alive
                # Proceso existe — PG podria estar corriendo
                self.root.after(0, self._log,
                    f"PostgreSQL ya tiene un proceso activo (PID {pid})", "WARN")
                return False
            except OSError:
                # Proceso no existe — PID stale
                self.root.after(0, self._log,
                    f"Limpiando PID stale de crash anterior (PID {pid})...", "WARN")
                os.remove(pid_file)
                return True

        except (ValueError, IOError):
            # PID file corrupto — eliminarlo
            self.root.after(0, self._log,
                "Archivo postmaster.pid corrupto, limpiando...", "WARN")
            try:
                os.remove(pid_file)
            except Exception:
                pass
            return True

    def _pg_check_port_in_use(self):
        """Verifica si el puerto PG ya esta en uso."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            result = s.connect_ex(("127.0.0.1", int(PG_PORT)))
            return result == 0  # True = puerto en uso

    def _pg_check_connection(self):
        """Verifica conectividad SQL real a PostgreSQL (no solo puerto)."""
        try:
            psql = _pg_cmd("psql")
            env = self._pg_env()
            result = subprocess.run(
                [psql, "-U", "postgres", "-h", "127.0.0.1", "-p", PG_PORT, "-tAc", "SELECT 1"],
                capture_output=True, text=True, timeout=5, env=env,
                creationflags=_SUBPROCESS_FLAGS,
            )
            return result.returncode == 0 and "1" in result.stdout
        except Exception:
            return False

    def _pg_fix_config(self):
        """Revisa y corrige configuraciones problematicas en postgresql.conf."""
        conf_path = os.path.join(PG_DATA, "postgresql.conf")
        if not os.path.exists(conf_path):
            return
        try:
            import re
            with open(conf_path, "r") as f:
                content = f.read()
            original = content
            fixes = []

            # 1. Reducir shared_buffers si es mayor a 32MB
            match = re.search(r"shared_buffers\s*=\s*(\d+)MB", content)
            if match and int(match.group(1)) > 32:
                content = re.sub(r"shared_buffers\s*=\s*\d+MB", "shared_buffers = 32MB", content)
                fixes.append(f"shared_buffers: {match.group(1)}MB -> 32MB")

            # 2. Forzar IPv4 (localhost puede resolver a IPv6 y fallar)
            if "listen_addresses = 'localhost'" in content:
                content = content.replace(
                    "listen_addresses = 'localhost'",
                    "listen_addresses = '127.0.0.1'")
                fixes.append("listen_addresses: localhost -> 127.0.0.1")

            # 3. synchronous_commit debe ser on (off causa crashes en Windows)
            if "synchronous_commit = off" in content:
                content = content.replace(
                    "synchronous_commit = off",
                    "synchronous_commit = on")
                fixes.append("synchronous_commit: off -> on")

            # 4. Agregar max_connections si no existe
            if "max_connections" not in content:
                content += "\nmax_connections = 20\n"
                fixes.append("max_connections: agregado (20)")

            # 5. Agregar work_mem si no existe
            if "work_mem" not in content:
                content += "work_mem = 1MB\n"
                fixes.append("work_mem: agregado (1MB)")

            if content != original:
                with open(conf_path, "w") as f:
                    f.write(content)
                for fix in fixes:
                    self.root.after(0, self._log, f"postgresql.conf: {fix}", "WARN")
        except Exception as e:
            self.root.after(0, self._log, f"Error revisando postgresql.conf: {e}", "WARN")

    def _pg_force_cleanup(self):
        """Fuerza la limpieza de un PG en mal estado: mata procesos y limpia PID."""
        # 1. Intentar pg_ctl stop -m immediate (no espera, mata todo)
        try:
            pg_ctl = _pg_cmd("pg_ctl")
            env = self._pg_env()
            subprocess.run(
                [pg_ctl, "stop", "-D", PG_DATA, "-m", "immediate", "-t", "5"],
                capture_output=True, text=True, timeout=10, env=env,
                creationflags=_SUBPROCESS_FLAGS,
            )
        except Exception:
            pass

        # 2. Buscar y matar cualquier proceso postgres huerfano en nuestro puerto
        if sys.platform == "win32":
            try:
                result = subprocess.run(
                    ["netstat", "-ano"],
                    capture_output=True, text=True, timeout=5,
                    creationflags=_SUBPROCESS_FLAGS,
                )
                for line in result.stdout.splitlines():
                    if f":{PG_PORT}" in line and "LISTENING" in line:
                        parts = line.split()
                        pid = int(parts[-1])
                        subprocess.run(
                            ["taskkill", "/F", "/PID", str(pid)],
                            capture_output=True, timeout=5,
                            creationflags=_SUBPROCESS_FLAGS,
                        )
                        self.root.after(0, self._log,
                            f"Proceso PG huerfano (PID {pid}) terminado.", "WARN")
                        time.sleep(1)
                        break
            except Exception:
                pass

        # 3. Limpiar PID file
        self._pg_check_stale_pid()
        time.sleep(0.5)

    def _pg_init_db(self):
        if os.path.exists(os.path.join(PG_DATA, "PG_VERSION")):
            self.root.after(0, self._log, "Cluster PG existente encontrado.", "INFO")
            self._pg_fix_config()
            return True

        self.root.after(0, self._log, "Primera ejecucion: inicializando PostgreSQL...", "INFO")
        self.root.after(0, self._log, "Esto puede tomar 1-2 minutos la primera vez.", "INFO")
        os.makedirs(PG_DATA, exist_ok=True)

        try:
            initdb = _pg_cmd("initdb")
            env = self._pg_env()

            proc = subprocess.Popen(
                [initdb, "-D", PG_DATA, "-U", "postgres", "-E", "UTF8",
                 "--locale=C", "--auth=trust"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, env=env, creationflags=_SUBPROCESS_FLAGS,
            )

            start_t = time.time()
            for line in iter(proc.stdout.readline, ""):
                line = line.rstrip()
                if line:
                    elapsed = int(time.time() - start_t)
                    self.root.after(0, self._log, f"[initdb {elapsed}s] {line}", "INFO")

            proc.wait(timeout=120)

            if proc.returncode != 0:
                self.root.after(0, self._log, f"initdb fallo con codigo {proc.returncode}", "ERROR")
                return False

            self.root.after(0, self._log, "Cluster PostgreSQL inicializado.", "OK")

            # Configurar postgresql.conf
            conf_path = os.path.join(PG_DATA, "postgresql.conf")
            with open(conf_path, "a") as f:
                f.write(f"\n# TechStock config\n")
                f.write(f"port = {PG_PORT}\n")
                f.write(f"listen_addresses = '127.0.0.1'\n")
                f.write(f"log_destination = 'stderr'\n")
                f.write(f"logging_collector = off\n")
                f.write(f"shared_buffers = 32MB\n")
                f.write(f"max_connections = 20\n")
                f.write(f"work_mem = 1MB\n")
                f.write(f"fsync = on\n")
                f.write(f"synchronous_commit = on\n")

            # Configurar pg_hba.conf para IPv4 trust
            hba_path = os.path.join(PG_DATA, "pg_hba.conf")
            with open(hba_path, "w") as f:
                f.write("# TechStock — solo conexiones locales IPv4\n")
                f.write("local   all   all                 trust\n")
                f.write("host    all   all   127.0.0.1/32  trust\n")

            return True
        except subprocess.TimeoutExpired:
            self.root.after(0, self._log, "Timeout al inicializar PostgreSQL (>120s)", "ERROR")
            self.root.after(0, self._log, "Posible causa: antivirus escaneando archivos", "WARN")
            return False
        except Exception as e:
            self.root.after(0, self._log, f"Error al inicializar: {e}", "ERROR")
            return False

    def _pg_start(self):
        if not self._pg_exists():
            self.root.after(0, self._log, "PostgreSQL portable no encontrado en pgsql/", "ERROR")
            self.root.after(0, self._log, f"Buscado en: {_pg_cmd('pg_ctl')}", "ERROR")
            return False

        if not self._pg_init_db():
            return False

        # Diagnostico pre-inicio
        self._pg_check_stale_pid()

        if self._pg_check_port_in_use():
            self.root.after(0, self._log,
                f"Puerto {PG_PORT} ya esta en uso \u2014 PG puede estar corriendo", "WARN")
            self.pg_running = True
            self.root.after(0, self._set_pg_status, "PostgreSQL (externo/previo)", SUCCESS)
            self._pg_ensure_db()
            return True

        # Primera ejecucion necesita mas tiempo
        _first_start = not os.path.exists(PG_LOG) or os.path.getsize(PG_LOG) < 100
        _max_wait = 45 if _first_start else 30

        self.root.after(0, self._set_pg_status, "Iniciando PostgreSQL...", WARNING)
        self.root.after(0, self._log, "Iniciando PostgreSQL...", "INFO")

        if _first_start:
            self.root.after(0, self._log, "Primera ejecucion — puede tomar hasta 45s...", "INFO")

        try:
            pg_ctl = _pg_cmd("pg_ctl")
            env = self._pg_env()

            # Iniciar PG sin -w (no esperar) para evitar que pg_ctl se cuelgue
            proc = subprocess.Popen(
                [pg_ctl, "start", "-D", PG_DATA, "-l", PG_LOG,
                 "-o", f"-p {PG_PORT}"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, env=env, creationflags=_SUBPROCESS_FLAGS,
            )

            # Esperar a que pg_ctl termine (solo lanza el proceso, no espera)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                self.root.after(0, self._log, "pg_ctl no respondio en 10s", "ERROR")

            rc = proc.returncode
            stdout = ""
            try:
                stdout = proc.stdout.read()
            except Exception:
                pass

            if rc is not None and rc != 0:
                err = stdout.strip() if stdout else f"Codigo de salida: {rc}"
                self.root.after(0, self._log, f"Error al iniciar PG: {err}", "ERROR")

                log_tail = self._pg_read_log_tail()
                if log_tail:
                    self.root.after(0, self._log, "--- Ultimas lineas de pg.log ---", "WARN")
                    for line in log_tail:
                        self.root.after(0, self._log, f"  {line}", "WARN")

                self.root.after(0, self._set_pg_status, "Error PostgreSQL", DANGER)
                self.root.after(0, self._log,
                    "Posibles causas: antivirus, permisos, VC++ Redistributable faltante", "WARN")
                return False

        except Exception as e:
            self.root.after(0, self._log, f"Error inesperado: {e}", "ERROR")
            self.root.after(0, self._set_pg_status, "Error PostgreSQL", DANGER)
            return False

        # Esperar a que PG responda en el puerto (polling propio)
        self.root.after(0, self._log, "Esperando que PostgreSQL acepte conexiones...", "INFO")
        for i in range(_max_wait):  # Max 30-45 segundos
            if self._pg_check_port_in_use():
                break
            if i > 0 and i % 5 == 0:
                self.root.after(0, self._set_pg_status,
                    f"Iniciando PostgreSQL... ({i}s)", WARNING)
            time.sleep(1)
        else:
            self.root.after(0, self._log,
                f"PostgreSQL no respondio en {_max_wait}s en puerto {PG_PORT}", "ERROR")
            log_tail = self._pg_read_log_tail()
            if log_tail:
                self.root.after(0, self._log, "--- pg.log ---", "WARN")
                for line in log_tail:
                    self.root.after(0, self._log, f"  {line}", "WARN")
            self.root.after(0, self._set_pg_status, "Error PostgreSQL", DANGER)
            return False

        self.pg_running = True
        self.root.after(0, self._set_pg_status, "PostgreSQL activo", SUCCESS)
        self.root.after(0, self._log, f"PostgreSQL iniciado en puerto {PG_PORT}.", "OK")

        # Esperar a que PG acepte SQL real antes de crear usuario/DB
        self.root.after(0, self._log, "Verificando que PostgreSQL acepte consultas...", "INFO")
        for _i in range(15):
            if self._pg_check_connection():
                break
            time.sleep(1)

        self._pg_ensure_db()
        return True

    def _pg_ensure_db(self):
        psql = _pg_cmd("psql")
        createdb = _pg_cmd("createdb")
        env = self._pg_env()

        self.root.after(0, self._log, "Verificando usuario y base de datos...", "INFO")

        try:
            result = subprocess.run(
                [psql, "-U", "postgres", "-h", "127.0.0.1", "-p", PG_PORT, "-tAc",
                 f"SELECT 1 FROM pg_roles WHERE rolname='{PG_USER}'"],
                capture_output=True, text=True, timeout=15, env=env,
                creationflags=_SUBPROCESS_FLAGS,
            )
            if result.returncode != 0:
                err = result.stderr.strip()
                self.root.after(0, self._log, f"Error consultando roles: {err}", "ERROR")
                return
            if "1" not in result.stdout:
                r = subprocess.run(
                    [psql, "-U", "postgres", "-h", "127.0.0.1", "-p", PG_PORT, "-c",
                     f"CREATE USER {PG_USER} WITH PASSWORD '{PG_PASSWORD}' CREATEDB"],
                    capture_output=True, text=True, timeout=15, env=env,
                    creationflags=_SUBPROCESS_FLAGS,
                )
                if r.returncode == 0:
                    self.root.after(0, self._log, f"Usuario '{PG_USER}' creado.", "OK")
                else:
                    self.root.after(0, self._log, f"Error creando usuario: {r.stderr.strip()}", "ERROR")
            else:
                self.root.after(0, self._log, f"Usuario '{PG_USER}' ya existe.", "INFO")
        except Exception as e:
            self.root.after(0, self._log, f"Error verificando usuario: {e}", "ERROR")

        try:
            result = subprocess.run(
                [psql, "-U", "postgres", "-h", "127.0.0.1", "-p", PG_PORT, "-tAc",
                 f"SELECT 1 FROM pg_database WHERE datname='{PG_DB}'"],
                capture_output=True, text=True, timeout=15, env=env,
                creationflags=_SUBPROCESS_FLAGS,
            )
            if result.returncode != 0:
                err = result.stderr.strip()
                self.root.after(0, self._log, f"Error consultando BD: {err}", "ERROR")
                return
            if "1" not in result.stdout:
                r = subprocess.run(
                    [createdb, "-U", "postgres", "-h", "127.0.0.1", "-p", PG_PORT,
                     "-O", PG_USER, PG_DB],
                    capture_output=True, text=True, timeout=15, env=env,
                    creationflags=_SUBPROCESS_FLAGS,
                )
                if r.returncode == 0:
                    self.root.after(0, self._log, f"Base de datos '{PG_DB}' creada.", "OK")
                else:
                    self.root.after(0, self._log, f"Error creando BD: {r.stderr.strip()}", "ERROR")
            else:
                self.root.after(0, self._log, f"Base de datos '{PG_DB}' ya existe.", "INFO")
        except Exception as e:
            self.root.after(0, self._log, f"Error verificando BD: {e}", "ERROR")

    def _pg_stop(self):
        if not self.pg_running:
            return

        self.root.after(0, self._log, "Deteniendo PostgreSQL...", "WARN")
        try:
            pg_ctl = _pg_cmd("pg_ctl")
            env = self._pg_env()
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

    def _pg_health_monitor(self):
        """Thread que monitorea la salud de PostgreSQL y lo reinicia si se cae."""
        _consecutive_fails = 0
        while self.running and not self._stopping:
            time.sleep(10)
            if not self.running or self._stopping or not self.pg_running:
                break
            if not self._pg_exists():
                break
            if not self._pg_check_connection():
                _consecutive_fails += 1
                if _consecutive_fails >= 3:
                    self.root.after(0, self._log,
                        "PostgreSQL no responde tras multiples intentos. Deteniendo monitor.", "ERROR")
                    self.root.after(0, self._set_pg_status,
                        "PostgreSQL caido — reinicie la app", DANGER)
                    break

                self.root.after(0, self._log,
                    f"PostgreSQL dejo de responder (intento {_consecutive_fails}/3). Reiniciando...", "ERROR")
                self.root.after(0, self._set_pg_status,
                    "Reiniciando PostgreSQL...", WARNING)

                # Mostrar pg.log para diagnostico
                log_tail = self._pg_read_log_tail()
                if log_tail:
                    self.root.after(0, self._log, "--- pg.log (crash) ---", "WARN")
                    for line in log_tail:
                        self.root.after(0, self._log, f"  {line}", "WARN")

                # Forzar limpieza antes de reiniciar
                self._pg_force_cleanup()

                if self._pg_start():
                    self.root.after(0, self._log,
                        "PostgreSQL reiniciado exitosamente.", "OK")
                    _consecutive_fails = 0
                else:
                    self.root.after(0, self._log,
                        "No se pudo reiniciar PostgreSQL.", "ERROR")
            else:
                _consecutive_fails = 0

    # ────────────────────────────────────────────────────────
    #  Web port management
    # ────────────────────────────────────────────────────────

    def _web_port_in_use(self):
        """Verifica si el puerto web ya esta en uso."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                return s.connect_ex(("localhost", WEB_PORT)) == 0
        except Exception:
            return False

    def _find_pid_on_port(self, port):
        """Busca el PID del proceso usando un puerto (Windows)."""
        if sys.platform != "win32":
            return None
        try:
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True, text=True, timeout=10,
                creationflags=_SUBPROCESS_FLAGS,
            )
            for line in result.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 5 and f":{port}" in parts[1] and parts[3] == "LISTENING":
                    return int(parts[4])
        except Exception:
            pass
        return None

    def _free_web_port(self):
        """Intenta liberar el puerto web matando el proceso que lo usa.

        Retorna True si el puerto quedo libre, False si no.
        """
        pid = self._find_pid_on_port(WEB_PORT)
        if not pid:
            self.root.after(0, self._log,
                f"No se pudo identificar el proceso en puerto {WEB_PORT}", "WARN")
            return False

        # No matar nuestro propio proceso
        if pid == os.getpid():
            return False

        self.root.after(0, self._log,
            f"Terminando proceso anterior en puerto {WEB_PORT} (PID {pid})...", "WARN")
        try:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True, timeout=10,
                    creationflags=_SUBPROCESS_FLAGS,
                )
            else:
                os.kill(pid, 15)  # SIGTERM
            time.sleep(1)

            # Verificar que el puerto quedo libre
            if not self._web_port_in_use():
                self.root.after(0, self._log,
                    f"Puerto {WEB_PORT} liberado.", "OK")
                return True
            else:
                self.root.after(0, self._log,
                    f"El puerto {WEB_PORT} sigue ocupado despues de terminar el proceso", "WARN")
                return False
        except Exception as e:
            self.root.after(0, self._log, f"Error al terminar proceso: {e}", "ERROR")
            return False

    # ────────────────────────────────────────────────────────
    #  Database connection check (fast, unified)
    # ────────────────────────────────────────────────────────

    def _check_db_connection(self):
        """Verifica la conexion a la DB: socket rapido + SQLAlchemy."""
        pg_port = int(PG_PORT)

        # Paso 1: check rapido de socket (max 3s)
        self.root.after(0, self._log, f"Verificando puerto {pg_port}...", "INFO")
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(3)
                result = s.connect_ex(("localhost", pg_port))
                if result != 0:
                    self.root.after(0, self._log,
                        f"Puerto {pg_port} no responde \u2014 PostgreSQL no esta disponible", "ERROR")
                    self.root.after(0, self._log,
                        "Verifique que PostgreSQL este corriendo o ajuste el puerto en Configuracion", "WARN")
                    return False
        except Exception as e:
            self.root.after(0, self._log, f"Error verificando puerto: {e}", "ERROR")
            return False

        self.root.after(0, self._log, f"Puerto {pg_port} responde. Verificando conexion SQL...", "INFO")

        # Paso 2: conexion real con SQLAlchemy (timeout 5s)
        try:
            from sqlalchemy import create_engine, text as sa_text

            db_url = os.environ.get("DATABASE_URL",
                f"postgresql://{PG_USER}:{PG_PASSWORD}@127.0.0.1:{PG_PORT}/{PG_DB}")

            test_engine = create_engine(
                db_url,
                pool_pre_ping=True,
                pool_size=1,
                max_overflow=0,
                connect_args={"connect_timeout": 5},
            )
            with test_engine.connect() as conn:
                conn.execute(sa_text("SELECT 1"))
            test_engine.dispose()
            return True
        except Exception as e:
            err_msg = str(e)
            # Mensaje amigable para errores comunes
            if "does not exist" in err_msg:
                self.root.after(0, self._log,
                    f"La base de datos '{PG_DB}' no existe. Se creara al iniciar.", "WARN")
                return True  # DB no existe pero PG responde — main.py la creara
            if "password authentication failed" in err_msg:
                self.root.after(0, self._log,
                    "Error de autenticacion \u2014 verifique usuario y password en Configuracion", "ERROR")
            elif "Connection refused" in err_msg:
                self.root.after(0, self._log,
                    "Conexion rechazada \u2014 PostgreSQL no acepta conexiones", "ERROR")
            else:
                self.root.after(0, self._log, f"Error de conexion: {err_msg[:200]}", "ERROR")
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
            # 1. Construir DATABASE_URL desde la config SIEMPRE
            #    (antes de cualquier check, para que todo use los valores correctos)
            existing_url = os.environ.get("DATABASE_URL", "").strip()
            constructed_url = (
                f"postgresql://{PG_USER}:{PG_PASSWORD}@127.0.0.1:{PG_PORT}/{PG_DB}"
            )
            if not existing_url:
                os.environ["DATABASE_URL"] = constructed_url
                self.root.after(0, self._log,
                    f"DATABASE_URL configurada: ...@localhost:{PG_PORT}/{PG_DB}", "INFO")
            else:
                self.root.after(0, self._log,
                    f"DATABASE_URL existente detectada en entorno", "INFO")

            # 2. Iniciar PostgreSQL portable (si existe)
            if self._pg_exists():
                if not self._pg_start():
                    self.root.after(0, self._on_start_failed, "No se pudo iniciar PostgreSQL")
                    return
            else:
                self.root.after(0, self._set_pg_status, "Verificando PG externo...", WARNING)
                self.root.after(0, self._log,
                    "PG portable no encontrado, verificando PostgreSQL externo...", "INFO")

            # 3. Verificar conexion a la base de datos
            self.root.after(0, self._set_status, "Verificando conexion...", WARNING)

            if not self._check_db_connection():
                self.root.after(0, self._on_start_failed,
                    "No se pudo conectar a PostgreSQL.\n"
                    "Verifique la configuracion en la pestana de Configuracion.")
                return

            self.root.after(0, self._log, "Conexion a base de datos verificada.", "OK")

            # Mostrar diagnostico PG
            log_tail = self._pg_read_log_tail(5)
            if log_tail:
                self.root.after(0, self._log, "--- pg.log (ultimas lineas) ---", "INFO")
                for line in log_tail:
                    self.root.after(0, self._log, f"  {line}", "INFO")

            if not self.pg_running:
                self.root.after(0, self._set_pg_status, "PostgreSQL externo", SUCCESS)
                self.pg_running = True

            # 4. Verificar puerto web libre
            if self._web_port_in_use():
                self.root.after(0, self._log,
                    f"Puerto {WEB_PORT} ya esta en uso. Intentando liberar...", "WARN")
                if not self._free_web_port():
                    self.root.after(0, self._on_start_failed,
                        f"El puerto {WEB_PORT} esta ocupado por otro proceso.\n"
                        f"Cierre la instancia anterior o cambie el puerto en Configuracion.")
                    return

            # 5. Iniciar servidor web
            self.root.after(0, self._set_status, "Iniciando servidor...", WARNING)
            self.root.after(0, self._log, f"Iniciando servidor web en puerto {WEB_PORT}...", "INFO")

            # Lanzar servidor desde el hilo principal para UI/server
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
                log_config=None,
            )
            self._server = uvicorn.Server(config)

            self.running = True
            self._start_time = datetime.now()
            self._enable_running_ui()

            threading.Thread(target=self._run_server, daemon=True).start()
            threading.Thread(target=self._wait_ready, daemon=True).start()
            if self.pg_running and self._pg_exists():
                threading.Thread(target=self._pg_health_monitor, daemon=True).start()

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
        self._start_time = datetime.now()
        self._enable_running_ui()

        threading.Thread(target=self._read_output, daemon=True).start()
        threading.Thread(target=self._wait_ready, daemon=True).start()
        if self.pg_running and self._pg_exists():
            threading.Thread(target=self._pg_health_monitor, daemon=True).start()

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

    def _process_alive(self):
        """Verifica si el proceso del servidor sigue vivo."""
        if _FROZEN:
            return self._server is not None and self.running
        return self.process is not None and self.process.poll() is None

    def _wait_ready(self):
        """Espera a que el servidor responda, verificando que el proceso siga vivo."""
        # Fase 1: Esperar a que el puerto este escuchando
        for i in range(60):
            if not self.running:
                return
            # Detectar si el proceso murio antes de estar listo
            if not self._process_alive():
                self.root.after(0, self._log,
                    "El proceso del servidor termino antes de estar listo.", "ERROR")
                self.root.after(0, self._unexpected_stop)
                return
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    if s.connect_ex(("localhost", WEB_PORT)) == 0:
                        break
            except Exception:
                pass
            time.sleep(0.5)
        else:
            self.root.after(0, lambda: self._set_status(
                "Timeout esperando servidor", WARNING))
            self.root.after(0, self._log,
                "El servidor no respondio en 30s. Puede estar cargando.", "WARN")
            return

        # Verificar que sigue vivo despues de detectar el puerto
        if not self._process_alive():
            self.root.after(0, self._log,
                "El proceso del servidor termino inesperadamente.", "ERROR")
            self.root.after(0, self._unexpected_stop)
            return

        # Fase 2: Esperar respuesta HTTP real
        import urllib.request
        for i in range(30):
            if not self.running:
                return
            if not self._process_alive():
                self.root.after(0, self._log,
                    "El proceso del servidor termino durante la carga.", "ERROR")
                self.root.after(0, self._unexpected_stop)
                return
            try:
                urllib.request.urlopen(f"http://localhost:{WEB_PORT}", timeout=3)
                self.root.after(0, self._server_ready)
                return
            except Exception:
                time.sleep(1)

        # Si el socket responde pero HTTP no, el servidor esta cargando (migrations, etc)
        if self._process_alive():
            self.root.after(0, self._server_ready)
        else:
            self.root.after(0, self._unexpected_stop)

    def _server_ready(self):
        self._set_status("Servidor activo", SUCCESS)
        self._url_var.set(f"http://localhost:{WEB_PORT}")
        self._log(f"Servidor listo en http://localhost:{WEB_PORT}", "OK")

        # Mostrar IPs de acceso en red
        ips = _get_local_ips()
        if ips:
            self._log("Acceso desde la red local:", "OK")
            for ip in ips:
                self._log(f"  \u2192 http://{ip}:{WEB_PORT}", "OK")

        self._update_footer()
        self._update_info_panel(running=True)

        # Cambiar a tab de info del servidor
        self._notebook.select(1)

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

        self._stopping = False
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
