#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════
#  TechStock v2.0 — Instalador Completo (Linux/macOS)
# ══════════════════════════════════════════════════════════
set -e
cd "$(dirname "$0")"

# Colores
G='\033[0;92m'; R='\033[0;91m'; Y='\033[0;93m'; C='\033[0;96m'
M='\033[0;95m'; B='\033[1m'; D='\033[2m'; N='\033[0m'

ok()   { echo -e "   ${G}✓${N} $1"; }
fail() { echo -e "   ${R}✗${N} $1"; }
warn() { echo -e "   ${Y}⚠${N} $1"; }
info() { echo -e "   ${C}ℹ${N} $1"; }
spin() { echo -e "   ${C}⧖${N} $1"; }

clear
echo ""
echo -e " ${M}╔═══════════════════════════════════════════════════════════╗${N}"
echo -e " ${M}║${N}                                                           ${M}║${N}"
echo -e " ${M}║${N}   ${B}${C}████████╗███████╗ ██████╗██╗  ██╗${N}                    ${M}║${N}"
echo -e " ${M}║${N}   ${B}${C}╚══██╔══╝██╔════╝██╔════╝██║  ██║${N}                    ${M}║${N}"
echo -e " ${M}║${N}   ${B}${C}   ██║   █████╗  ██║     ███████║${N}                    ${M}║${N}"
echo -e " ${M}║${N}   ${B}${C}   ██║   ██╔══╝  ██║     ██╔══██║${N}                    ${M}║${N}"
echo -e " ${M}║${N}   ${B}${C}   ██║   ███████╗╚██████╗██║  ██║${N}                    ${M}║${N}"
echo -e " ${M}║${N}   ${B}${C}   ╚═╝   ╚══════╝ ╚═════╝╚═╝  ╚═╝${N}  ${M}Stock v2.0${N}     ${M}║${N}"
echo -e " ${M}║${N}                                                           ${M}║${N}"
echo -e " ${M}║${N}   ${D}Instalador Completo — Sistema de Inventario${N}            ${M}║${N}"
echo -e " ${M}║${N}                                                           ${M}║${N}"
echo -e " ${M}╚═══════════════════════════════════════════════════════════╝${N}"
echo ""

ERRORS=0

# ══════════════════════════════════════════════════════════
#  PASO 1/6: Python
# ══════════════════════════════════════════════════════════
echo -e " ${B}══════════════════════════════════════════════════════════${N}"
echo -e " ${B}${C}[1/6]${N} ${B}Verificando Python...${N}"
echo -e " ${B}══════════════════════════════════════════════════════════${N}"

PYTHON_CMD=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PYTHON_CMD="$cmd"
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    warn "Python no encontrado. Intentando instalar..."
    if [ "$(uname)" = "Darwin" ]; then
        if command -v brew &>/dev/null; then
            spin "Instalando Python via Homebrew..."
            brew install python3
            PYTHON_CMD="python3"
        else
            fail "Homebrew no encontrado. Instale desde https://brew.sh"
            exit 1
        fi
    elif command -v apt-get &>/dev/null; then
        spin "Instalando Python via apt..."
        sudo apt-get update -qq
        sudo apt-get install -y python3 python3-venv python3-pip python3-dev libpq-dev
        PYTHON_CMD="python3"
    elif command -v dnf &>/dev/null; then
        spin "Instalando Python via dnf..."
        sudo dnf install -y python3 python3-pip python3-devel libpq-devel
        PYTHON_CMD="python3"
    elif command -v pacman &>/dev/null; then
        spin "Instalando Python via pacman..."
        sudo pacman -S --noconfirm python python-pip
        PYTHON_CMD="python3"
    else
        fail "No se pudo instalar Python. Instale Python 3.10+ manualmente."
        exit 1
    fi
fi

PYVER=$($PYTHON_CMD --version 2>&1)
ok "$PYVER encontrado."

# ══════════════════════════════════════════════════════════
#  PASO 2/6: PostgreSQL
# ══════════════════════════════════════════════════════════
echo ""
echo -e " ${B}══════════════════════════════════════════════════════════${N}"
echo -e " ${B}${C}[2/6]${N} ${B}Verificando PostgreSQL...${N}"
echo -e " ${B}══════════════════════════════════════════════════════════${N}"

if command -v psql &>/dev/null; then
    PGVER=$(psql --version | head -1)
    ok "$PGVER encontrado."
else
    warn "PostgreSQL no encontrado. Instalando..."

    if [ "$(uname)" = "Darwin" ]; then
        if command -v brew &>/dev/null; then
            brew install postgresql@16
            brew services start postgresql@16
        fi
    elif command -v apt-get &>/dev/null; then
        sudo apt-get install -y postgresql postgresql-client
        sudo systemctl start postgresql
        sudo systemctl enable postgresql
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y postgresql-server postgresql-contrib
        sudo postgresql-setup --initdb 2>/dev/null || true
        sudo systemctl start postgresql
        sudo systemctl enable postgresql
    elif command -v pacman &>/dev/null; then
        sudo pacman -S --noconfirm postgresql
        sudo -u postgres initdb -D /var/lib/postgres/data 2>/dev/null || true
        sudo systemctl start postgresql
        sudo systemctl enable postgresql
    else
        fail "Instale PostgreSQL manualmente: https://www.postgresql.org/download/"
        exit 1
    fi
    ok "PostgreSQL instalado e iniciado."
fi

# ══════════════════════════════════════════════════════════
#  PASO 3/6: Configurar conexion
# ══════════════════════════════════════════════════════════
echo ""
echo -e " ${B}══════════════════════════════════════════════════════════${N}"
echo -e " ${B}${C}[3/6]${N} ${B}Configurando conexion a PostgreSQL...${N}"
echo -e " ${B}══════════════════════════════════════════════════════════${N}"

PG_HOST="localhost"; PG_PORT="5432"; PG_USER="postgres"
PG_PASS="postgres"; PG_DBNAME="inventario"

if [ -f ".env" ]; then
    info "Archivo .env existente encontrado."
    cat .env
    echo ""
    read -p "   Mantener configuracion existente? (s/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        rm -f .env
    fi
fi

if [ ! -f ".env" ]; then
    echo ""
    echo -e "   ${D}Ingrese datos de conexion (ENTER = valor por defecto):${N}"
    read -p "   Host [$PG_HOST]: " input; PG_HOST="${input:-$PG_HOST}"
    read -p "   Puerto [$PG_PORT]: " input; PG_PORT="${input:-$PG_PORT}"
    read -p "   Usuario [$PG_USER]: " input; PG_USER="${input:-$PG_USER}"
    read -p "   Contrasena [$PG_PASS]: " input; PG_PASS="${input:-$PG_PASS}"
    read -p "   Base de datos [$PG_DBNAME]: " input; PG_DBNAME="${input:-$PG_DBNAME}"
    echo "DATABASE_URL=postgresql://${PG_USER}:${PG_PASS}@${PG_HOST}:${PG_PORT}/${PG_DBNAME}" > .env
    ok "Archivo .env creado."
fi

export $(grep -v '^#' .env | xargs)
export PGPASSWORD="$PG_PASS"

# Verificar conexion y crear DB
if psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -c "SELECT 1" &>/dev/null; then
    ok "Conexion a PostgreSQL verificada."
    if ! psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DBNAME" -c "SELECT 1" &>/dev/null; then
        spin "Creando base de datos '$PG_DBNAME'..."
        psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -c "CREATE DATABASE $PG_DBNAME ENCODING 'UTF8';" 2>&1
        ok "Base de datos '$PG_DBNAME' creada."
    else
        info "Base de datos '$PG_DBNAME' ya existe."
    fi
else
    warn "Intentando con peer authentication (sudo -u postgres)..."
    sudo -u postgres psql -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$PG_USER') THEN CREATE ROLE $PG_USER WITH LOGIN PASSWORD '$PG_PASS' CREATEDB; END IF; END \$\$;" 2>/dev/null
    sudo -u postgres psql -c "CREATE DATABASE $PG_DBNAME OWNER $PG_USER ENCODING 'UTF8';" 2>/dev/null || true
    ok "Base de datos configurada."
fi

# ══════════════════════════════════════════════════════════
#  PASO 4/6: Entorno virtual + dependencias
# ══════════════════════════════════════════════════════════
echo ""
echo -e " ${B}══════════════════════════════════════════════════════════${N}"
echo -e " ${B}${C}[4/6]${N} ${B}Creando entorno virtual e instalando dependencias...${N}"
echo -e " ${B}══════════════════════════════════════════════════════════${N}"

if [ -d "venv" ] && [ -f "venv/bin/activate" ]; then
    info "Entorno virtual ya existe."
else
    spin "Creando entorno virtual..."
    $PYTHON_CMD -m venv venv
    ok "Entorno virtual creado."
fi

source venv/bin/activate
spin "Actualizando pip..."
pip install --upgrade pip -q
spin "Instalando paquetes..."
pip install -r requirements.txt -q
ok "Dependencias instaladas."

# ══════════════════════════════════════════════════════════
#  PASO 5/7: Credenciales del usuario administrador (ROOT)
# ══════════════════════════════════════════════════════════
echo ""
echo -e " ${B}══════════════════════════════════════════════════════════${N}"
echo -e " ${B}${C}[5/7]${N} ${B}Configurando usuario administrador (ROOT)...${N}"
echo -e " ${B}══════════════════════════════════════════════════════════${N}"
echo ""
echo -e "   ${D}Configure las credenciales del usuario principal.${N}"
echo -e "   ${D}Presione ENTER para usar el valor por defecto [entre corchetes].${N}"
echo ""

ADMIN_USERNAME="admin"
ADMIN_PASSWORD=""
ADMIN_NAME="Administrador"

read -p "   Usuario administrador [admin]: " input
ADMIN_USERNAME="${input:-admin}"

read -sp "   Contrasena del administrador: " input
echo
if [ -z "$input" ]; then
    ADMIN_PASSWORD="admin123"
    warn "Se usara la contrasena por defecto: admin123"
    echo -e "   ${Y}  Cambiela despues del primer inicio de sesion.${N}"
else
    ADMIN_PASSWORD="$input"
fi

read -p "   Nombre completo [Administrador]: " input
ADMIN_NAME="${input:-Administrador}"

echo ""
ok "Usuario: $ADMIN_USERNAME"
ok "Nombre:  $ADMIN_NAME"

export ADMIN_USERNAME ADMIN_PASSWORD ADMIN_NAME

# ══════════════════════════════════════════════════════════
#  PASO 6/7: Inicializar base de datos
# ══════════════════════════════════════════════════════════
echo ""
echo -e " ${B}══════════════════════════════════════════════════════════${N}"
echo -e " ${B}${C}[6/7]${N} ${B}Inicializando base de datos...${N}"
echo -e " ${B}══════════════════════════════════════════════════════════${N}"

spin "Creando tablas y datos iniciales..."
python -c "
from database import engine, Base, SessionLocal
from models import *
from migrations import run_migrations
from seed import run_seed
Base.metadata.create_all(bind=engine)
run_migrations(engine)
db = SessionLocal()
run_seed(db)
db.close()
"
ok "Tablas creadas."
ok "Migraciones aplicadas."
ok "Usuario '$ADMIN_USERNAME' creado."

mkdir -p backups static/uploads

# ══════════════════════════════════════════════════════════
#  PASO 7/7: Verificacion final
# ══════════════════════════════════════════════════════════
echo ""
echo -e " ${B}══════════════════════════════════════════════════════════${N}"
echo -e " ${B}${C}[7/7]${N} ${B}Verificacion final...${N}"
echo -e " ${B}══════════════════════════════════════════════════════════${N}"

python -c "from database import engine; c=engine.connect(); c.close()" 2>/dev/null
if [ $? -eq 0 ]; then
    ok "Conexion a base de datos OK."
else
    fail "No se pudo verificar la conexion."
    ERRORS=$((ERRORS+1))
fi

# ══════════════════════════════════════════════════════════
#  RESUMEN
# ══════════════════════════════════════════════════════════
echo ""
echo ""
if [ $ERRORS -eq 0 ]; then
    echo -e " ${G}╔═══════════════════════════════════════════════════════════╗${N}"
    echo -e " ${G}║${N}                                                           ${G}║${N}"
    echo -e " ${G}║${N}   ${G}✓  INSTALACION COMPLETADA EXITOSAMENTE${N}                 ${G}║${N}"
    echo -e " ${G}║${N}                                                           ${G}║${N}"
    echo -e " ${G}╚═══════════════════════════════════════════════════════════╝${N}"
else
    echo -e " ${Y}╔═══════════════════════════════════════════════════════════╗${N}"
    echo -e " ${Y}║${N}   ${Y}⚠  INSTALACION COMPLETADA CON ADVERTENCIAS${N}             ${Y}║${N}"
    echo -e " ${Y}╚═══════════════════════════════════════════════════════════╝${N}"
fi

echo ""
echo -e " ${B}Como iniciar TechStock:${N}"
echo ""
echo -e "   ${C}./start.sh${N}"
echo ""
echo -e " ${B}Datos de acceso:${N}"
echo ""
echo -e "   ${C}URL:${N}       http://localhost:8000"
echo -e "   ${C}Usuario:${N}   $ADMIN_USERNAME"
echo -e "   ${C}Nombre:${N}    $ADMIN_NAME"
echo ""

read -p "   Desea iniciar TechStock ahora? (s/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]; then
    python main.py
fi
