#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

# ── Colores ──
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}[OK]${NC} $1"; }
err()  { echo -e "  ${RED}[ERROR]${NC} $1"; }
warn() { echo -e "  ${YELLOW}[AVISO]${NC} $1"; }
info() { echo -e "  ${CYAN}[INFO]${NC} $1"; }

echo ""
echo -e "  ${BOLD}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "  ${BOLD}║        TechStock v2.0 - Instalador Automático        ║${NC}"
echo -e "  ${BOLD}║       Sistema de Inventario con PostgreSQL            ║${NC}"
echo -e "  ${BOLD}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

# ─────────────────────────────────────────────────────────────
#  PASO 1: Verificar Python
# ─────────────────────────────────────────────────────────────
echo -e "${BOLD}[1/7] Verificando Python...${NC}"

PYTHON_CMD=""
for cmd in python3 python; do
    if command -v "$cmd" &> /dev/null; then
        PYTHON_CMD="$cmd"
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    err "Python no encontrado."
    echo "  Instale Python 3.10+:"
    echo "    Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
    echo "    macOS:         brew install python3"
    echo "    Fedora:        sudo dnf install python3"
    exit 1
fi

PYVER=$($PYTHON_CMD --version 2>&1)
ok "$PYVER encontrado."

# ─────────────────────────────────────────────────────────────
#  PASO 2: Verificar / Instalar PostgreSQL
# ─────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}[2/7] Verificando PostgreSQL...${NC}"

if command -v psql &> /dev/null; then
    PGVER=$(psql --version | head -1)
    ok "$PGVER encontrado."
else
    warn "PostgreSQL no encontrado."
    echo ""

    # Detectar sistema operativo e instalar
    if [ "$(uname)" = "Darwin" ]; then
        # macOS
        if command -v brew &> /dev/null; then
            echo "  Instalando PostgreSQL via Homebrew..."
            read -p "  ¿Continuar? (s/n): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Ss]$ ]]; then
                brew install postgresql@16
                brew services start postgresql@16
                ok "PostgreSQL instalado e iniciado."
            else
                err "Instalación cancelada."
                exit 1
            fi
        else
            err "Homebrew no encontrado. Instale Homebrew primero: https://brew.sh"
            exit 1
        fi
    elif command -v apt-get &> /dev/null; then
        # Debian/Ubuntu
        echo "  Instalando PostgreSQL via apt..."
        read -p "  Se requiere sudo. ¿Continuar? (s/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Ss]$ ]]; then
            sudo apt-get update -qq
            sudo apt-get install -y postgresql postgresql-client libpq-dev
            sudo systemctl start postgresql
            sudo systemctl enable postgresql
            ok "PostgreSQL instalado e iniciado."
        else
            err "Instalación cancelada."
            exit 1
        fi
    elif command -v dnf &> /dev/null; then
        # Fedora/RHEL
        echo "  Instalando PostgreSQL via dnf..."
        read -p "  Se requiere sudo. ¿Continuar? (s/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Ss]$ ]]; then
            sudo dnf install -y postgresql-server postgresql-contrib
            sudo postgresql-setup --initdb 2>/dev/null || true
            sudo systemctl start postgresql
            sudo systemctl enable postgresql
            ok "PostgreSQL instalado e iniciado."
        else
            err "Instalación cancelada."
            exit 1
        fi
    elif command -v pacman &> /dev/null; then
        # Arch
        echo "  Instalando PostgreSQL via pacman..."
        read -p "  Se requiere sudo. ¿Continuar? (s/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Ss]$ ]]; then
            sudo pacman -S --noconfirm postgresql
            sudo -u postgres initdb -D /var/lib/postgres/data 2>/dev/null || true
            sudo systemctl start postgresql
            sudo systemctl enable postgresql
            ok "PostgreSQL instalado e iniciado."
        else
            err "Instalación cancelada."
            exit 1
        fi
    else
        err "No se pudo detectar el gestor de paquetes."
        echo "  Instale PostgreSQL manualmente: https://www.postgresql.org/download/"
        exit 1
    fi
fi

# ─────────────────────────────────────────────────────────────
#  PASO 3: Configurar conexión a PostgreSQL
# ─────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}[3/7] Configurando conexión a PostgreSQL...${NC}"

PG_HOST="localhost"
PG_PORT="5432"
PG_USER="postgres"
PG_PASS="postgres"
PG_DBNAME="inventario"

if [ -f ".env" ]; then
    info "Archivo .env existente encontrado."
    cat .env
    echo ""
    read -p "  ¿Mantener la configuración existente? (s/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        # Cargar .env
        export $(grep -v '^#' .env | xargs)
    else
        rm -f .env
    fi
fi

if [ ! -f ".env" ]; then
    echo ""
    echo "  Ingrese los datos de conexión (ENTER = valor por defecto)."
    echo ""
    read -p "  Host [$PG_HOST]: " input; PG_HOST="${input:-$PG_HOST}"
    read -p "  Puerto [$PG_PORT]: " input; PG_PORT="${input:-$PG_PORT}"
    read -p "  Usuario [$PG_USER]: " input; PG_USER="${input:-$PG_USER}"
    read -p "  Contraseña [$PG_PASS]: " input; PG_PASS="${input:-$PG_PASS}"
    read -p "  Base de datos [$PG_DBNAME]: " input; PG_DBNAME="${input:-$PG_DBNAME}"

    echo "DATABASE_URL=postgresql://${PG_USER}:${PG_PASS}@${PG_HOST}:${PG_PORT}/${PG_DBNAME}" > .env
    ok "Archivo .env creado."
fi

# Cargar variables
export $(grep -v '^#' .env | xargs)

# ─────────────────────────────────────────────────────────────
#  PASO 4: Crear base de datos PostgreSQL
# ─────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}[4/7] Creando base de datos PostgreSQL...${NC}"

export PGPASSWORD="$PG_PASS"

# Verificar conexión
if psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -c "SELECT 1" &> /dev/null; then
    ok "Conexión a PostgreSQL verificada."
else
    warn "No se pudo conectar con usuario '$PG_USER'."
    echo "  Intentando con peer authentication (sudo -u postgres)..."

    if sudo -u postgres psql -c "SELECT 1" &> /dev/null; then
        # Crear usuario si no existe
        sudo -u postgres psql -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$PG_USER') THEN CREATE ROLE $PG_USER WITH LOGIN PASSWORD '$PG_PASS' CREATEDB; END IF; END \$\$;" 2>/dev/null
        # Crear base de datos
        sudo -u postgres psql -c "CREATE DATABASE $PG_DBNAME OWNER $PG_USER ENCODING 'UTF8';" 2>/dev/null || true

        # Configurar pg_hba.conf para password auth si es necesario
        warn "Si tiene problemas de autenticación, edite pg_hba.conf:"
        echo "    Cambie 'peer' a 'md5' para conexiones locales."

        ok "Base de datos configurada via peer auth."
    else
        err "No se pudo conectar a PostgreSQL."
        echo "  Verifique que el servicio está corriendo: sudo systemctl status postgresql"
        exit 1
    fi
else
    # Conexión directa funciona — verificar si la DB ya existe
    if psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DBNAME" -c "SELECT 1" &> /dev/null; then
        info "La base de datos '$PG_DBNAME' ya existe."
    else
        echo "  Creando base de datos '$PG_DBNAME'..."
        psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -c "CREATE DATABASE $PG_DBNAME ENCODING 'UTF8';" 2>&1
        if [ $? -ne 0 ]; then
            err "No se pudo crear la base de datos."
            exit 1
        fi
        ok "Base de datos '$PG_DBNAME' creada."
    fi
fi

# ─────────────────────────────────────────────────────────────
#  PASO 5: Crear entorno virtual Python
# ─────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}[5/7] Configurando entorno virtual Python...${NC}"

if [ -d "venv" ] && [ -f "venv/bin/activate" ]; then
    info "Entorno virtual ya existe."
else
    echo "  Creando entorno virtual..."
    $PYTHON_CMD -m venv venv
    ok "Entorno virtual creado."
fi

# ─────────────────────────────────────────────────────────────
#  PASO 6: Instalar dependencias Python
# ─────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}[6/7] Instalando dependencias Python...${NC}"

source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    err "Falló la instalación de dependencias."
    exit 1
fi
ok "Dependencias instaladas."

# ─────────────────────────────────────────────────────────────
#  PASO 7: Inicializar tablas y datos
# ─────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}[7/7] Inicializando base de datos...${NC}"

python _init_db.py

if [ $? -ne 0 ]; then
    err "Error al inicializar la base de datos."
    exit 1
fi
ok "Base de datos inicializada."

# ── Crear directorios necesarios ──
mkdir -p backups static/uploads

# ─────────────────────────────────────────────────────────────
#  RESUMEN
# ─────────────────────────────────────────────────────────────
echo ""
echo -e "  ${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "  ${GREEN}║         Instalación completada exitosamente!         ║${NC}"
echo -e "  ${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  Para iniciar TechStock:"
echo "    ./start.sh"
echo ""
echo "  Para copias de seguridad:"
echo "    ./backup.sh"
echo ""
echo "  Datos de acceso:"
echo "    URL:       http://localhost:8000"
echo "    Usuario:   admin"
echo "    Clave:     admin123"
echo ""
echo "  Base de datos:"
echo "    $DATABASE_URL"
echo ""
