"""TechStock Launcher - Interfaz gráfica moderna para iniciar/detener el servidor."""
import os
import sys
import subprocess
import threading
import webbrowser
import tkinter as tk
from tkinter import messagebox, font as tkfont

# Ruta base del proyecto
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(BASE_DIR)

# Cargar .env
env_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

# Detectar Python del venv
VENV_PYTHON = os.path.join(BASE_DIR, "venv", "Scripts", "python.exe")
if not os.path.exists(VENV_PYTHON):
    VENV_PYTHON = os.path.join(BASE_DIR, "venv", "bin", "python")
if not os.path.exists(VENV_PYTHON):
    VENV_PYTHON = sys.executable

# ── Paleta de colores ──
BG_DARK = "#0f0f1a"
BG_CARD = "#1a1a2e"
BG_CARD_HOVER = "#222240"
ACCENT = "#6c63ff"
ACCENT_HOVER = "#857dff"
ACCENT_DARK = "#4a42d4"
SUCCESS = "#00c9a7"
DANGER = "#ff6b6b"
WARNING = "#ffc93c"
TEXT_PRIMARY = "#e8e8f0"
TEXT_SECONDARY = "#8888a0"
TEXT_MUTED = "#555570"
BORDER = "#2a2a45"


class RoundedFrame(tk.Canvas):
    """Canvas que simula un frame con bordes redondeados."""

    def __init__(self, parent, bg_color=BG_CARD, radius=16, **kwargs):
        super().__init__(parent, highlightthickness=0, bg=BG_DARK, **kwargs)
        self.bg_color = bg_color
        self.radius = radius
        self.bind("<Configure>", self._draw)

    def _draw(self, event=None):
        self.delete("bg")
        w, h, r = self.winfo_width(), self.winfo_height(), self.radius
        self.create_round_rect(0, 0, w, h, r, fill=self.bg_color, outline="", tags="bg")
        self.tag_lower("bg")

    def create_round_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = [
            x1 + r, y1, x1 + r, y1, x2 - r, y1, x2 - r, y1,
            x2, y1, x2, y1 + r, x2, y1 + r, x2, y2 - r,
            x2, y2 - r, x2, y2, x2 - r, y2, x2 - r, y2,
            x1 + r, y2, x1 + r, y2, x1, y2, x1, y2 - r,
            x1, y2 - r, x1, y1 + r, x1, y1 + r, x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)


class ModernButton(tk.Canvas):
    """Botón moderno con efecto hover y bordes redondeados."""

    def __init__(self, parent, text="", icon="", bg=ACCENT, fg="white",
                 hover_bg=ACCENT_HOVER, width=180, height=44, command=None,
                 font_size=11, **kwargs):
        super().__init__(parent, width=width, height=height,
                         highlightthickness=0, bg=BG_DARK, cursor="hand2", **kwargs)
        self.bg_color = bg
        self.hover_color = hover_bg
        self.fg_color = fg
        self.command = command
        self.disabled = False
        self._width = width
        self._height = height
        self.display_text = f"{icon}  {text}" if icon else text
        self.font_size = font_size

        self._draw(self.bg_color)

        self.bind("<Enter>", lambda e: self._on_hover(True))
        self.bind("<Leave>", lambda e: self._on_hover(False))
        self.bind("<Button-1>", lambda e: self._on_click())

    def _draw(self, color):
        self.delete("all")
        w, h, r = self._width, self._height, 10
        points = [
            r, 0, r, 0, w - r, 0, w - r, 0, w, 0, w, r, w, r,
            w, h - r, w, h - r, w, h, w - r, h, w - r, h,
            r, h, r, h, 0, h, 0, h - r, 0, h - r, 0, r, 0, r, 0, 0,
        ]
        self.create_polygon(points, smooth=True, fill=color, outline="")
        self.create_text(
            w // 2, h // 2, text=self.display_text,
            fill=self.fg_color if not self.disabled else TEXT_MUTED,
            font=("Segoe UI", self.font_size, "bold"),
        )

    def _on_hover(self, entering):
        if self.disabled:
            return
        self._draw(self.hover_color if entering else self.bg_color)

    def _on_click(self):
        if not self.disabled and self.command:
            self.command()

    def set_disabled(self, state):
        self.disabled = state
        self.configure(cursor="" if state else "hand2")
        self._draw("#2a2a40" if state else self.bg_color)


class TechStockLauncher:
    def __init__(self):
        self.process = None
        self.running = False

        self.root = tk.Tk()
        self.root.title("TechStock v2.0")
        self.root.geometry("520x580")
        self.root.resizable(False, False)
        self.root.configure(bg=BG_DARK)

        # Icono
        try:
            icon_path = os.path.join(BASE_DIR, "static", "favicon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass

        # Centrar en pantalla
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - 260
        y = (self.root.winfo_screenheight() // 2) - 290
        self.root.geometry(f"+{x}+{y}")

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self):
        root = self.root

        # ── Header con gradiente simulado ──
        header = tk.Frame(root, bg=BG_DARK, height=140)
        header.pack(fill="x", pady=(30, 0))
        header.pack_propagate(False)

        # Logo (simulated with unicode)
        logo_frame = tk.Frame(header, bg=BG_DARK)
        logo_frame.pack()

        # Icono grande
        tk.Label(
            logo_frame, text="\u2b22", font=("Segoe UI", 48), fg=ACCENT, bg=BG_DARK
        ).pack()

        tk.Label(
            header, text="TechStock",
            font=("Segoe UI", 28, "bold"), fg=TEXT_PRIMARY, bg=BG_DARK
        ).pack(pady=(0, 2))

        tk.Label(
            header, text="Sistema de Inventario  v2.0",
            font=("Segoe UI", 11), fg=TEXT_SECONDARY, bg=BG_DARK
        ).pack()

        # ── Divider ──
        tk.Frame(root, bg=BORDER, height=1).pack(fill="x", padx=60, pady=20)

        # ── Status Card ──
        status_frame = tk.Frame(root, bg=BG_DARK)
        status_frame.pack(pady=(0, 5))

        self.status_indicator = tk.Label(
            status_frame, text="\u25cf", font=("Segoe UI", 14), fg=DANGER, bg=BG_DARK
        )
        self.status_indicator.pack(side="left", padx=(0, 8))

        self.status_var = tk.StringVar(value="Servidor detenido")
        self.status_label = tk.Label(
            status_frame, textvariable=self.status_var,
            font=("Segoe UI", 13, "bold"), fg=TEXT_PRIMARY, bg=BG_DARK
        )
        self.status_label.pack(side="left")

        # URL
        self.url_var = tk.StringVar(value="")
        self.url_label = tk.Label(
            root, textvariable=self.url_var,
            font=("Segoe UI", 11), fg=ACCENT, bg=BG_DARK, cursor="hand2"
        )
        self.url_label.pack(pady=(2, 0))
        self.url_label.bind("<Button-1>", lambda e: self.open_browser() if self.running else None)

        # ── Botones principales ──
        btn_frame = tk.Frame(root, bg=BG_DARK)
        btn_frame.pack(pady=25)

        self.btn_start = ModernButton(
            btn_frame, text="Iniciar Servidor", icon="\u25b6",
            bg=ACCENT, hover_bg=ACCENT_HOVER, width=200, height=48,
            command=self.start_server, font_size=12,
        )
        self.btn_start.pack(side="left", padx=8)

        self.btn_stop = ModernButton(
            btn_frame, text="Detener", icon="\u25a0",
            bg="#3a3a55", hover_bg="#4a4a65", width=140, height=48,
            command=self.stop_server, font_size=12,
        )
        self.btn_stop.pack(side="left", padx=8)
        self.btn_stop.set_disabled(True)

        # Botón navegador
        self.btn_browser = ModernButton(
            root, text="Abrir en Navegador", icon="\U0001f310",
            bg="#1e1e35", hover_bg="#2e2e50", width=220, height=40,
            command=self.open_browser, font_size=10,
        )
        self.btn_browser.pack(pady=(0, 10))
        self.btn_browser.set_disabled(True)

        # ── Divider ──
        tk.Frame(root, bg=BORDER, height=1).pack(fill="x", padx=60, pady=10)

        # ── Info bar ──
        info_frame = tk.Frame(root, bg=BG_DARK)
        info_frame.pack(pady=(5, 0))

        tk.Label(
            info_frame, text="Puerto: 8000",
            font=("Segoe UI", 9), fg=TEXT_MUTED, bg=BG_DARK
        ).pack(side="left", padx=15)

        tk.Label(
            info_frame, text="\u2502",
            font=("Segoe UI", 9), fg=BORDER, bg=BG_DARK
        ).pack(side="left")

        tk.Label(
            info_frame, text="Usuario: admin",
            font=("Segoe UI", 9), fg=TEXT_MUTED, bg=BG_DARK
        ).pack(side="left", padx=15)

        tk.Label(
            info_frame, text="\u2502",
            font=("Segoe UI", 9), fg=BORDER, bg=BG_DARK
        ).pack(side="left")

        tk.Label(
            info_frame, text="Clave: admin123",
            font=("Segoe UI", 9), fg=TEXT_MUTED, bg=BG_DARK
        ).pack(side="left", padx=15)

        # Footer
        tk.Label(
            root, text="TechStock \u00a9 2026  \u2014  Gesti\u00f3n de Inventario",
            font=("Segoe UI", 8), fg=TEXT_MUTED, bg=BG_DARK
        ).pack(side="bottom", pady=12)

    def start_server(self):
        if self.running:
            return

        self._set_status("Verificando base de datos...", WARNING, WARNING)
        self.root.update()

        # Verificar conexion a PostgreSQL (inline, sin _check_db.py)
        try:
            check = subprocess.run(
                [VENV_PYTHON, "-c",
                 "from database import engine; c=engine.connect(); c.close()"],
                cwd=BASE_DIR, capture_output=True, text=True, timeout=15
            )
            if check.returncode != 0:
                error_msg = check.stderr.strip() or check.stdout.strip() or "No se pudo conectar"
                self._set_status("Error de conexi\u00f3n", DANGER, DANGER)
                messagebox.showerror(
                    "Error de Base de Datos",
                    f"No se pudo conectar a PostgreSQL.\n\n{error_msg}\n\n"
                    "Verifique que el servicio de PostgreSQL est\u00e1 corriendo.\n"
                    "(Servicios de Windows > postgresql-x64-16 > Iniciar)"
                )
                return
        except Exception as e:
            self._set_status("Error", DANGER, DANGER)
            messagebox.showerror("Error", str(e))
            return

        # Iniciar servidor
        self._set_status("Iniciando servidor...", WARNING, WARNING)
        self.root.update()

        try:
            self.process = subprocess.Popen(
                [VENV_PYTHON, "main.py"],
                cwd=BASE_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
        except Exception as e:
            self._set_status("Error al iniciar", DANGER, DANGER)
            messagebox.showerror("Error", str(e))
            return

        self.running = True
        self.btn_start.set_disabled(True)
        self.btn_stop.set_disabled(False)
        self.btn_browser.set_disabled(False)

        threading.Thread(target=self._wait_for_server, daemon=True).start()

    def _wait_for_server(self):
        import time
        for _ in range(30):
            if not self.running:
                return
            try:
                import urllib.request
                urllib.request.urlopen("http://localhost:8000", timeout=2)
                self.root.after(0, self._server_ready)
                return
            except Exception:
                time.sleep(1)

        self.root.after(0, lambda: self._set_status(
            "Iniciado (verificar puerto)", WARNING, WARNING
        ))

    def _server_ready(self):
        self._set_status("Servidor en ejecuci\u00f3n", SUCCESS, SUCCESS)
        self.url_var.set("\U0001f517  http://localhost:8000")

    def _set_status(self, text, indicator_color, label_color=None):
        self.status_var.set(text)
        self.status_indicator.config(fg=indicator_color)
        if label_color:
            self.status_label.config(fg=label_color)

    def stop_server(self):
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None

        self.running = False
        self._set_status("Servidor detenido", DANGER, TEXT_PRIMARY)
        self.url_var.set("")
        self.btn_start.set_disabled(False)
        self.btn_stop.set_disabled(True)
        self.btn_browser.set_disabled(True)

    def open_browser(self):
        webbrowser.open("http://localhost:8000")

    def on_close(self):
        if self.running:
            if messagebox.askyesno(
                "Cerrar TechStock",
                "El servidor est\u00e1 corriendo.\n\u00bfDesea detenerlo y salir?"
            ):
                self.stop_server()
            else:
                return
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = TechStockLauncher()
    app.run()
