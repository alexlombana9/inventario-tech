#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════
#  TechStock v2.0 — Desinstalador (Linux/macOS)
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
echo -e " ${M}║${N}   ${B}${R}████████╗███████╗ ██████╗██╗  ██╗${N}                    ${M}║${N}"
echo -e " ${M}║${N}   ${B}${R}╚══██╔══╝██╔════╝██╔════╝██║  ██║${N}                    ${M}║${N}"
echo -e " ${M}║${N}   ${B}${R}   ██║   █████╗  ██║     ███████║${N}                    ${M}║${N}"
echo -e " ${M}║${N}   ${B}${R}   ██║   ██╔══╝  ██║     ██╔══██║${N}                    ${M}║${N}"
echo -e " ${M}║${N}   ${B}${R}   ██║   ███████╗╚██████╗██║  ██║${N}                    ${M}║${N}"
echo -e " ${M}║${N}   ${B}${R}   ╚═╝   ╚══════╝ ╚═════╝╚═╝  ╚═╝${N}  ${M}Stock v2.0${N}     ${M}║${N}"
echo -e " ${M}║${N}                                                           ${M}║${N}"
echo -e " ${M}║${N}   ${D}Desinstalador — Sistema de Inventario${N}                  ${M}║${N}"
echo -e " ${M}║${N}                                                           ${M}║${N}"
echo -e " ${M}╚═══════════════════════════════════════════════════════════╝${N}"
echo ""
echo -e " ${Y}ATENCION:${N} Este proceso eliminara la instalacion de TechStock."
echo -e " ${D}El codigo fuente NO se elimina, solo los archivos generados.${N}"
echo -e " ${D}Puede volver a instalar ejecutando instalar.sh${N}"
echo ""
echo -e " ${B}Se eliminara:${N}"
echo -e "   ${C}1.${N} Entorno virtual      ${D}(venv/)${N}"
echo -e "   ${C}2.${N} Configuracion        ${D}(.env, .secret_key)${N}"
echo -e "   ${C}3.${N} Archivos de build    ${D}(build/, dist/, *.spec)${N}"
echo -e "   ${C}4.${N} Cron job             ${D}(backup automatico)${N}"
echo -e "   ${C}5.${N} Cache                ${D}(__pycache__, .pytest_cache, etc.)${N}"
echo ""

read -p "   Desea continuar con la desinstalacion? (s/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo ""
    echo -e " ${C}Desinstalacion cancelada.${N}"
    exit 0
fi
echo ""

# ══════════════════════════════════════════════════════════
#  Preguntar sobre la base de datos
# ══════════════════════════════════════════════════════════
DROP_DB=0
echo -e " ${Y}¿Desea ELIMINAR la base de datos PostgreSQL?${N}"
echo -e " ${D}  Si elige SI, se perderan TODOS los datos (productos, ventas, etc.)${N}"
echo -e " ${D}  Si elige NO, los datos se conservan para una futura reinstalacion.${N}"
echo ""
read -p "   Eliminar base de datos? (s/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]; then
    DROP_DB=1
fi
echo ""

# ══════════════════════════════════════════════════════════
#  Preguntar sobre los backups
# ══════════════════════════════════════════════════════════
DROP_BACKUPS=0
if [ -d "backups" ]; then
    BK_COUNT=$(find backups -name "*.sql" 2>/dev/null | wc -l)
    if [ "$BK_COUNT" -gt 0 ]; then
        echo -e " ${Y}Se encontraron $BK_COUNT copia(s) de seguridad.${N}"
        echo -e " ${D}  Carpeta: backups/${N}"
        echo ""
        read -p "   Eliminar copias de seguridad? (s/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Ss]$ ]]; then
            DROP_BACKUPS=1
        fi
        echo ""
    fi
fi

echo -e " ${B}══════════════════════════════════════════════════════════${N}"
echo -e " ${B}Desinstalando TechStock...${N}"
echo -e " ${B}══════════════════════════════════════════════════════════${N}"
echo ""

# ══════════════════════════════════════════════════════════
#  1. Eliminar cron job de backup automatico
# ══════════════════════════════════════════════════════════
echo -e " ${C}[1/6]${N} Eliminando cron job de backup..."
if crontab -l 2>/dev/null | grep -q "TechStock_Backup"; then
    crontab -l 2>/dev/null | grep -v "TechStock_Backup" | crontab -
    ok "Cron job de backup eliminado."
else
    info "No habia cron job de backup."
fi

# ══════════════════════════════════════════════════════════
#  2. Eliminar archivos de build
# ══════════════════════════════════════════════════════════
echo -e " ${C}[2/6]${N} Eliminando archivos de build..."
rm -f TechStock.spec backup_auto.sh 2>/dev/null || true
rm -rf build dist 2>/dev/null || true
ok "Archivos de build eliminados."

# ══════════════════════════════════════════════════════════
#  3. Eliminar entorno virtual
# ══════════════════════════════════════════════════════════
echo -e " ${C}[3/6]${N} Eliminando entorno virtual..."
if [ -d "venv" ]; then
    rm -rf venv
    if [ ! -d "venv" ]; then
        ok "Entorno virtual eliminado."
    else
        warn "No se pudo eliminar completamente. Intente cerrar otros programas."
    fi
else
    info "No habia entorno virtual."
fi

# ══════════════════════════════════════════════════════════
#  4. Eliminar archivos de configuracion
# ══════════════════════════════════════════════════════════
echo -e " ${C}[4/6]${N} Eliminando archivos de configuracion..."

# Leer datos de .env antes de eliminarlo (para DROP DB)
PG_HOST="localhost"; PG_PORT="5432"; PG_USER="postgres"
PG_PASS="postgres"; PG_DBNAME="inventario"

if [ -f ".env" ]; then
    # Parsear DATABASE_URL
    DB_URL=$(grep "^DATABASE_URL=" .env 2>/dev/null | cut -d'=' -f2-)
    if [ -n "$DB_URL" ]; then
        PG_HOST=$(echo "$DB_URL" | python3 -c "from urllib.parse import urlparse; import sys; p=urlparse(sys.stdin.read().strip()); print(p.hostname or 'localhost')" 2>/dev/null || echo "localhost")
        PG_PORT=$(echo "$DB_URL" | python3 -c "from urllib.parse import urlparse; import sys; p=urlparse(sys.stdin.read().strip()); print(p.port or 5432)" 2>/dev/null || echo "5432")
        PG_USER=$(echo "$DB_URL" | python3 -c "from urllib.parse import urlparse; import sys; p=urlparse(sys.stdin.read().strip()); print(p.username or 'postgres')" 2>/dev/null || echo "postgres")
        PG_PASS=$(echo "$DB_URL" | python3 -c "from urllib.parse import urlparse; import sys; p=urlparse(sys.stdin.read().strip()); print(p.password or 'postgres')" 2>/dev/null || echo "postgres")
        PG_DBNAME=$(echo "$DB_URL" | python3 -c "from urllib.parse import urlparse; import sys; p=urlparse(sys.stdin.read().strip()); print((p.path or '/inventario').lstrip('/'))" 2>/dev/null || echo "inventario")
    fi
    rm -f .env
    ok ".env eliminado."
else
    info "No habia .env"
fi

if [ -f ".secret_key" ]; then
    rm -f .secret_key
    ok ".secret_key eliminado."
fi
rm -f .coverage 2>/dev/null || true

# ══════════════════════════════════════════════════════════
#  5. Eliminar cache y archivos temporales
# ══════════════════════════════════════════════════════════
echo -e " ${C}[5/6]${N} Eliminando cache y archivos temporales..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
rm -rf .pytest_cache htmlcov 2>/dev/null || true

if [ "$DROP_BACKUPS" -eq 1 ]; then
    rm -rf backups
    ok "Copias de seguridad eliminadas."
else
    info "Copias de seguridad conservadas en backups/"
fi

ok "Cache limpiado."

# ══════════════════════════════════════════════════════════
#  6. Eliminar base de datos (opcional)
# ══════════════════════════════════════════════════════════
echo -e " ${C}[6/6]${N} Base de datos..."
if [ "$DROP_DB" -eq 1 ]; then
    if command -v psql &>/dev/null; then
        spin "Eliminando base de datos '$PG_DBNAME'..."
        export PGPASSWORD="$PG_PASS"

        # Cerrar conexiones activas
        psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" \
            -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$PG_DBNAME' AND pid <> pg_backend_pid();" \
            >/dev/null 2>&1 || true

        # Eliminar base de datos
        if psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" \
            -c "DROP DATABASE IF EXISTS $PG_DBNAME;" >/dev/null 2>&1; then
            ok "Base de datos '$PG_DBNAME' eliminada."
        else
            # Intentar con peer authentication
            if sudo -u postgres psql -c "DROP DATABASE IF EXISTS $PG_DBNAME;" >/dev/null 2>&1; then
                ok "Base de datos '$PG_DBNAME' eliminada (via peer auth)."
            else
                warn "No se pudo eliminar la base de datos."
                echo -e "   ${D}Puede eliminarla manualmente con: DROP DATABASE $PG_DBNAME;${N}"
            fi
        fi
        unset PGPASSWORD
    else
        warn "psql no encontrado. No se pudo eliminar la base de datos."
        echo -e "   ${D}Eliminela manualmente desde pgAdmin o psql.${N}"
    fi
else
    info "Base de datos conservada (puede reutilizarse al reinstalar)."
fi

# ══════════════════════════════════════════════════════════
#  RESUMEN
# ══════════════════════════════════════════════════════════
echo ""
echo ""
echo -e " ${G}╔═══════════════════════════════════════════════════════════╗${N}"
echo -e " ${G}║${N}                                                           ${G}║${N}"
echo -e " ${G}║${N}   ${G}✓  DESINSTALACION COMPLETADA${N}                           ${G}║${N}"
echo -e " ${G}║${N}                                                           ${G}║${N}"
echo -e " ${G}╚═══════════════════════════════════════════════════════════╝${N}"
echo ""
echo -e " ${B}Elementos eliminados:${N}"
echo -e "   ${G}✓${N} Entorno virtual (venv)"
echo -e "   ${G}✓${N} Configuracion (.env, .secret_key)"
echo -e "   ${G}✓${N} Archivos de build"
echo -e "   ${G}✓${N} Cron job de backup"
echo -e "   ${G}✓${N} Cache y archivos temporales"
if [ "$DROP_DB" -eq 1 ]; then
    echo -e "   ${G}✓${N} Base de datos PostgreSQL"
else
    echo -e "   ${C}~${N} Base de datos conservada"
fi
if [ "$DROP_BACKUPS" -eq 1 ]; then
    echo -e "   ${G}✓${N} Copias de seguridad"
else
    echo -e "   ${C}~${N} Copias de seguridad conservadas"
fi
echo ""
echo -e " ${B}Elementos conservados:${N}"
echo -e "   ${C}~${N} Codigo fuente del proyecto"
echo -e "   ${C}~${N} Python (instalacion del sistema)"
echo -e "   ${C}~${N} PostgreSQL (instalacion del sistema)"
echo ""
echo -e " ${B}Para reinstalar:${N}"
echo -e "   Ejecute ${C}./instalar.sh${N}"
echo ""
