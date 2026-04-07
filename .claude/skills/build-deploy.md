# Build y Deploy — TechStock

## PyInstaller Build
- Entry point: `launcher.py` (GUI tkinter que gestiona PG portable + servidor)
- Spec file: `techstock.spec` — incluye static/, templates/, assets
- Comando: `pyinstaller techstock.spec --clean`
- Output: `dist/TechStock/` (directorio con exe + dependencias)
- PyInstaller 6.x: static/templates empaquetados en `_MEIPASS`, no junto al exe

## Instalador Windows (Inno Setup)
- Script: `installer/techstock.iss`
- Automatizacion completa: `build_installer.bat`
- Flujo: PyInstaller → copiar PG portable → Inno Setup → `.exe` instalador
- Incluye: app empaquetada + PostgreSQL 16 portable (puerto 5433)
- Output: `dist/installer/TechStock_Setup_v3.0.exe`

## Docker
```bash
docker-compose up -d     # PostgreSQL 16 (alpine) + app en :8000
docker-compose down      # Detener
docker-compose logs -f web  # Ver logs
```
- `Dockerfile`: python:3.11-slim + psycopg2
- `docker-compose.yml`: PG 16 + app web, volumen persistente para datos

## Desarrollo Local
```bash
pip install -r requirements.txt   # Produccion
pip install -r requirements-dev.txt  # + pytest, httpx, coverage
python main.py                    # http://localhost:8000 (requiere PG activo)
```

## Checklist Pre-Deploy
- [ ] `pytest --tb=short -q` — todos los tests pasan
- [ ] No hay secrets hardcoded (`.secret_key` auto-generado, `.env` no commiteado)
- [ ] `requirements.txt` actualizado con versiones pinned
- [ ] Migraciones idempotentes en `migrations.py` (se ejecutan al startup)
- [ ] `seed.py` idempotente (solo crea si tabla vacia)
- [ ] Variables de entorno: `DATABASE_URL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`
- [ ] Puerto PG portable: 5433 (no conflicta con PG sistema en 5432)
