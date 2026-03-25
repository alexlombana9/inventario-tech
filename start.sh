#!/usr/bin/env bash
cd "$(dirname "$0")"

# Cargar variables de entorno
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Activar entorno virtual
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "[AVISO] Entorno virtual no encontrado. Ejecute ./instalar.sh primero."
    exit 1
fi

# Verificar conexion a PostgreSQL (inline)
python -c "from database import engine; c=engine.connect(); c.close()" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[ERROR] No se pudo conectar a PostgreSQL."
    echo "Verifique que el servicio esta corriendo."
    echo "Intente: sudo systemctl start postgresql"
    exit 1
fi

python main.py
