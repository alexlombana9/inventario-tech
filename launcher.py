"""TechStock Launcher - Interfaz gráfica para iniciar/detener el servidor."""
import os
import sys
import subprocess
import threading
import webbrowser
import tkinter as tk
from tkinter import messagebox

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
    VENV_PYTHON = sys.executable


class TechStockLauncher:
    def __init__(self):
        self.process = None
        self.running = False

        self.root = tk.Tk()
        self.root.title("TechStock v2.0")
        self.root.geometry("420x340")
        self.root.resizable(False, False)
        self.root.configure(bg="#1a1a2e")

        # Icono (sin error si no existe)
        try:
            icon_path = os.path.join(BASE_DIR, "static", "favicon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass

        # Header
        tk.Label(
            self.root, text="TechStock v2.0",
            font=("Segoe UI", 20, "bold"), fg="#e94560", bg="#1a1a2e"
        ).pack(pady=(25, 5))

        tk.Label(
            self.root, text="Sistema de Inventario",
            font=("Segoe UI", 11), fg="#a0a0b0", bg="#1a1a2e"
        ).pack()

        # Status
        self.status_var = tk.StringVar(value="Detenido")
        self.status_label = tk.Label(
            self.root, textvariable=self.status_var,
            font=("Segoe UI", 12, "bold"), fg="#ff6b6b", bg="#1a1a2e"
        )
        self.status_label.pack(pady=(20, 5))

        self.url_var = tk.StringVar(value="")
        tk.Label(
            self.root, textvariable=self.url_var,
            font=("Segoe UI", 10), fg="#4ecdc4", bg="#1a1a2e", cursor="hand2"
        ).pack()

        # Botones
        btn_frame = tk.Frame(self.root, bg="#1a1a2e")
        btn_frame.pack(pady=25)

        self.btn_start = tk.Button(
            btn_frame, text="  Iniciar Servidor  ",
            font=("Segoe UI", 12, "bold"), bg="#0f3460", fg="white",
            activebackground="#16213e", activeforeground="white",
            relief="flat", padx=20, pady=8, command=self.start_server
        )
        self.btn_start.pack(side="left", padx=8)

        self.btn_stop = tk.Button(
            btn_frame, text="  Detener  ",
            font=("Segoe UI", 12, "bold"), bg="#533483", fg="white",
            activebackground="#3a1f5e", activeforeground="white",
            relief="flat", padx=20, pady=8, command=self.stop_server,
            state="disabled"
        )
        self.btn_stop.pack(side="left", padx=8)

        self.btn_browser = tk.Button(
            self.root, text="Abrir en Navegador",
            font=("Segoe UI", 10), bg="#1a1a2e", fg="#4ecdc4",
            activebackground="#1a1a2e", activeforeground="#7efff5",
            relief="flat", cursor="hand2", command=self.open_browser,
            state="disabled"
        )
        self.btn_browser.pack()

        # Info
        tk.Label(
            self.root, text="Usuario: admin  |  Clave: admin123",
            font=("Segoe UI", 9), fg="#555570", bg="#1a1a2e"
        ).pack(side="bottom", pady=10)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def start_server(self):
        if self.running:
            return

        # Verificar conexion a PostgreSQL
        self.status_var.set("Verificando base de datos...")
        self.status_label.config(fg="#f0c040")
        self.root.update()

        try:
            check = subprocess.run(
                [VENV_PYTHON, "_check_db.py"],
                cwd=BASE_DIR, capture_output=True, text=True, timeout=15
            )
            if check.returncode != 0:
                error_msg = check.stderr.strip() or check.stdout.strip() or "No se pudo conectar"
                self.status_var.set("Error de conexion")
                self.status_label.config(fg="#ff6b6b")
                messagebox.showerror(
                    "Error de Base de Datos",
                    f"No se pudo conectar a PostgreSQL.\n\n{error_msg}\n\n"
                    "Verifique que el servicio de PostgreSQL esta corriendo.\n"
                    "(Servicios de Windows > postgresql-x64-16 > Iniciar)"
                )
                return
        except Exception as e:
            self.status_var.set("Error")
            self.status_label.config(fg="#ff6b6b")
            messagebox.showerror("Error", str(e))
            return

        # Iniciar servidor
        self.status_var.set("Iniciando...")
        self.status_label.config(fg="#f0c040")
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
            self.status_var.set("Error al iniciar")
            self.status_label.config(fg="#ff6b6b")
            messagebox.showerror("Error", str(e))
            return

        self.running = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.btn_browser.config(state="normal")

        # Esperar a que el servidor este listo
        threading.Thread(target=self._wait_for_server, daemon=True).start()

    def _wait_for_server(self):
        """Espera a que el servidor responda y actualiza el estado."""
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

        self.root.after(0, lambda: self.status_var.set("Iniciado (verificar puerto)"))

    def _server_ready(self):
        self.status_var.set("En ejecucion")
        self.status_label.config(fg="#4ecdc4")
        self.url_var.set("http://localhost:8000")

    def stop_server(self):
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None

        self.running = False
        self.status_var.set("Detenido")
        self.status_label.config(fg="#ff6b6b")
        self.url_var.set("")
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.btn_browser.config(state="disabled")

    def open_browser(self):
        webbrowser.open("http://localhost:8000")

    def on_close(self):
        if self.running:
            if messagebox.askyesno("Cerrar", "El servidor esta corriendo. ¿Desea detenerlo y salir?"):
                self.stop_server()
            else:
                return
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = TechStockLauncher()
    app.run()
