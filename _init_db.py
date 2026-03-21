"""Script de inicializacion de base de datos (usado por setup.bat/setup.sh)."""
from database import engine, Base, SessionLocal
from models import *
from migrations import run_migrations
from seed import run_seed

print("  Creando tablas...")
Base.metadata.create_all(bind=engine)
print("  Ejecutando migraciones...")
run_migrations(engine)
print("  Insertando datos iniciales...")
db = SessionLocal()
try:
    run_seed(db)
finally:
    db.close()
print("  Listo.")
