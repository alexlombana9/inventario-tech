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
    echo "[AVISO] Entorno virtual no encontrado. Ejecute ./setup.sh primero."
    exit 1
fi

# Verificar conexión a PostgreSQL
python -c "
from database import engine
try:
    conn = engine.connect()
    conn.close()
except Exception as e:
    print(f'[ERROR] No se pudo conectar a PostgreSQL: {e}')
    print('Verifique que el servicio de PostgreSQL está corriendo.')
    exit(1)
" 2>&1

if [ $? -ne 0 ]; then
    echo "Intente: sudo systemctl start postgresql"
    exit 1
fi

python main.py
