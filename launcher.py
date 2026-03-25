"""TechStock Launcher — Interfaz para gestionar el servidor con visor de logs."""
import os
import sys
import subprocess
import threading
import webbrowser
import tkinter as tk
from tkinter import messagebox
from datetime import datetime

# ── Ruta base ──
if getattr(sys, "frozen", False):
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

# ── Python del venv ──
VENV_PYTHON = os.path.join(BASE_DIR, "venv", "Scripts", "python.exe")
if not os.path.exists(VENV_PYTHON):
    VENV_PYTHON = os.path.join(BASE_DIR, "venv", "bin", "python")
if not os.path.exists(VENV_PYTHON):
    VENV_PYTHON = sys.executable

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


class TechStockLauncher:
    def __init__(self):
        self.process = None
        self.running = False
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

        self._log("TechStock v2.0 \u2014 Gestor de servidor listo.", "OK")
        self._log(f"Python: {VENV_PYTHON}", "INFO")

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

        # ── Status + Controls ──
        bar = tk.Frame(root, bg=BG_DARK)
        bar.pack(fill="x", padx=24, pady=4)

        # Status
        st = tk.Frame(bar, bg=BG_DARK)
        st.pack(side="left")

        self._dot = tk.Label(st, text="\u25cf", font=("Segoe UI", 13),
                             fg=DANGER, bg=BG_DARK)
        self._dot.pack(side="left", padx=(0, 6))

        self._status_var = tk.StringVar(value="Servidor detenido")
        self._status_lbl = tk.Label(st, textvariable=self._status_var,
                                    font=("Segoe UI", 11, "bold"),
                                    fg=TEXT_PRIMARY, bg=BG_DARK)
        self._status_lbl.pack(side="left")

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
            cursor="hand2", command=self._start_server)
        self._btn_start.pack(side="left", padx=3)

        self._btn_stop = tk.Button(
            btns, text="\u25a0  Detener", font=("Segoe UI", 10, "bold"),
            bg="#3a3a55", fg=TEXT_SECONDARY, activebackground="#4a4a65",
            activeforeground="white", relief="flat", padx=18, pady=7,
            cursor="hand2", command=self._stop_server, state="disabled")
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
        tk.Label(ft, text="Puerto: 8000", font=("Segoe UI", 8),
                 fg=TEXT_MUTED, bg=BG_DARK).pack(side="left")
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

    # ────────────────────────────────────────────────────────
    #  Server control
    # ────────────────────────────────────────────────────────

    def _start_server(self):
        if self.running:
            return

        self._stopping = False
        self._set_status("Verificando base de datos\u2026", WARNING)
        self._log("Verificando conexi\u00f3n a base de datos\u2026", "INFO")
        self.root.update()

        # Verificar DB
        try:
            chk = subprocess.run(
                [VENV_PYTHON, "-c",
                 "from database import engine; c=engine.connect(); c.close()"],
                cwd=BASE_DIR, capture_output=True, text=True, timeout=15)
            if chk.returncode != 0:
                err = chk.stderr.strip() or chk.stdout.strip() or "Sin detalle"
                self._set_status("Error de conexi\u00f3n", DANGER)
                self._log(f"Error DB: {err}", "ERROR")
                messagebox.showerror(
                    "Error de Base de Datos",
                    f"No se pudo conectar a PostgreSQL.\n\n{err}\n\n"
                    "Verifique que PostgreSQL est\u00e1 corriendo.\n"
                    "(Servicios de Windows \u203a postgresql-x64-16 \u203a Iniciar)")
                return
        except Exception as e:
            self._set_status("Error", DANGER)
            self._log(f"Excepci\u00f3n: {e}", "ERROR")
            return

        self._log("Conexi\u00f3n a base de datos OK.", "OK")
        self._set_status("Iniciando servidor\u2026", WARNING)
        self._log("Iniciando servidor en puerto 8000\u2026", "INFO")
        self.root.update()

        # Iniciar proceso
        try:
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            self.process = subprocess.Popen(
                [VENV_PYTHON, "-u", "main.py"],
                cwd=BASE_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                creationflags=(subprocess.CREATE_NO_WINDOW
                               if sys.platform == "win32" else 0),
            )
        except Exception as e:
            self._set_status("Error al iniciar", DANGER)
            self._log(f"No se pudo iniciar: {e}", "ERROR")
            return

        self.running = True
        self._enable_running_ui()

        # Hilos de monitoreo
        threading.Thread(target=self._read_output, daemon=True).start()
        threading.Thread(target=self._wait_ready, daemon=True).start()

    def _read_output(self):
        """Lee stdout del proceso y lo muestra en el log."""
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

    def _classify(self, line):
        """Clasifica una linea de log por nivel."""
        low = line.lower()
        if any(k in low for k in ("error", "traceback", "exception", "critical")):
            return "ERROR"
        if any(k in low for k in ("warning", "warn", "deprecat")):
            return "WARN"
        if any(k in low for k in ("started", "[ok]", "listo", "ready")):
            return "OK"
        if any(m in line for m in ("GET ", "POST ", "PUT ", "DELETE ", "PATCH ", "HEAD ", "OPTIONS ")):
            return "HTTP"
        return "INFO"

    def _wait_ready(self):
        """Espera hasta que el servidor responda en localhost:8000."""
        import time
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
        self._set_status("Servidor en ejecuci\u00f3n", SUCCESS)
        self._url_var.set("\U0001f517 http://localhost:8000")
        self._log("Servidor listo en http://localhost:8000", "OK")

    def _unexpected_stop(self):
        self._set_status("Servidor detenido inesperadamente", DANGER)
        self._log("El servidor se detuvo inesperadamente.", "ERROR")
        self._enable_stopped_ui()

    def _stop_server(self):
        if not self.process:
            return
        self._stopping = True
        self._log("Deteniendo servidor\u2026", "WARN")
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
        self.process = None
        self._set_status("Servidor detenido", DANGER)
        self._log("Servidor detenido.", "INFO")
        self._enable_stopped_ui()

    def _open_browser(self):
        if self.running:
            webbrowser.open("http://localhost:8000")
            self._log("Navegador abierto.", "INFO")

    def _on_close(self):
        if self.running:
            if messagebox.askyesno(
                "Cerrar TechStock",
                "El servidor est\u00e1 corriendo.\n\u00bfDetenerlo y salir?"):
                self._stop_server()
            else:
                return
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = TechStockLauncher()
    app.run()
