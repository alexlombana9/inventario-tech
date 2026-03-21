"""Verifica la conexion a PostgreSQL (usado por start.bat)."""
import sys
try:
    from database import engine
    conn = engine.connect()
    conn.close()
    print("[OK] Conexion a PostgreSQL verificada.")
    sys.exit(0)
except Exception as e:
    print(f"[ERROR] No se pudo conectar a PostgreSQL: {e}")
    sys.exit(1)
