#!/usr/bin/env bash
cd "$(dirname "$0")"

# ── Colores ──
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

BACKUP_DIR="$(pwd)/backups"
mkdir -p "$BACKUP_DIR"

# ── Cargar configuración ──
PG_HOST="localhost"
PG_PORT="5432"
PG_USER="postgres"
PG_PASS="postgres"
PG_DBNAME="inventario"

if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Parsear DATABASE_URL
if [ -n "$DATABASE_URL" ] && command -v python3 &> /dev/null || command -v python &> /dev/null; then
    PYTHON_CMD=$(command -v python3 || command -v python)
    eval $($PYTHON_CMD -c "
from urllib.parse import urlparse
p = urlparse('$DATABASE_URL')
print(f'PG_HOST={p.hostname or \"localhost\"}')
print(f'PG_PORT={p.port or 5432}')
print(f'PG_USER={p.username or \"postgres\"}')
print(f'PG_PASS={p.password or \"postgres\"}')
print(f'PG_DBNAME={(p.path or \"/inventario\").lstrip(\"/\")}')
" 2>/dev/null)
fi

export PGPASSWORD="$PG_PASS"

# ── Verificar herramientas ──
check_tools() {
    if ! command -v psql &> /dev/null; then
        echo -e "${RED}[ERROR]${NC} psql no encontrado. Instale PostgreSQL client."
        exit 1
    fi
    if ! command -v pg_dump &> /dev/null; then
        echo -e "${RED}[ERROR]${NC} pg_dump no encontrado. Instale PostgreSQL client."
        exit 1
    fi
}

# ── Funciones ──

crear_backup_completo() {
    check_tools
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    FILENAME="techstock_full_${TIMESTAMP}.sql"
    FILEPATH="$BACKUP_DIR/$FILENAME"

    echo -e "  Creando backup completo..."
    pg_dump -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DBNAME" \
        --no-owner --no-acl -f "$FILEPATH" 2>&1

    SIZE=$(du -h "$FILEPATH" | cut -f1)
    echo -e "  ${GREEN}[OK]${NC} Backup creado: $FILENAME ($SIZE)"
}

crear_backup_datos() {
    check_tools
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    FILENAME="techstock_data_${TIMESTAMP}.sql"
    FILEPATH="$BACKUP_DIR/$FILENAME"

    echo -e "  Creando backup de datos..."
    pg_dump -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DBNAME" \
        --data-only --no-owner --no-acl --column-inserts -f "$FILEPATH" 2>&1

    SIZE=$(du -h "$FILEPATH" | cut -f1)
    echo -e "  ${GREEN}[OK]${NC} Backup de datos: $FILENAME ($SIZE)"
}

restaurar_backup() {
    check_tools
    echo ""
    echo -e "  ${BOLD}Backups disponibles:${NC}"
    echo "  ─────────────────────────────────────────────────"

    FILES=()
    i=0
    for f in $(ls -t "$BACKUP_DIR"/*.sql 2>/dev/null); do
        i=$((i+1))
        fname=$(basename "$f")
        fsize=$(du -h "$f" | cut -f1)
        fdate=$(date -r "$f" "+%Y-%m-%d %H:%M" 2>/dev/null || stat -c '%y' "$f" 2>/dev/null | cut -d. -f1)
        echo "  $i. $fname  ($fsize)  $fdate"
        FILES+=("$f")
    done

    if [ $i -eq 0 ]; then
        echo -e "  ${YELLOW}[AVISO]${NC} No hay backups disponibles."
        return
    fi

    echo ""
    read -p "  Seleccione el número (0=cancelar): " NUM

    if [ "$NUM" = "0" ] || [ -z "$NUM" ]; then
        return
    fi

    IDX=$((NUM-1))
    if [ $IDX -lt 0 ] || [ $IDX -ge ${#FILES[@]} ]; then
        echo -e "  ${RED}[ERROR]${NC} Número inválido."
        return
    fi

    SELECTED="${FILES[$IDX]}"
    SELECTED_NAME=$(basename "$SELECTED")

    echo ""
    echo -e "  ${YELLOW}ATENCIÓN: Esto reemplazará TODOS los datos actuales.${NC}"
    echo "  Archivo: $SELECTED_NAME"
    read -p "  ¿Está seguro? (s/n): " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        return
    fi

    echo "  Restaurando..."

    # Cerrar conexiones activas
    psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -c \
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$PG_DBNAME' AND pid <> pg_backend_pid();" &> /dev/null

    # Recrear base de datos
    psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -c "DROP DATABASE IF EXISTS $PG_DBNAME;" &> /dev/null
    psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -c "CREATE DATABASE $PG_DBNAME ENCODING 'UTF8';" &> /dev/null

    # Restaurar
    psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DBNAME" -f "$SELECTED" &> /dev/null

    echo -e "  ${GREEN}[OK]${NC} Base de datos restaurada desde: $SELECTED_NAME"
}

listar_backups() {
    echo ""
    echo -e "  ${BOLD}Copias de seguridad existentes${NC}"
    echo "  Directorio: $BACKUP_DIR"
    echo "  ─────────────────────────────────────────────────────"

    COUNT=0
    TOTAL=0
    for f in $(ls -t "$BACKUP_DIR"/*.sql 2>/dev/null); do
        COUNT=$((COUNT+1))
        fname=$(basename "$f")
        fsize_h=$(du -h "$f" | cut -f1)
        fsize_b=$(stat -f%z "$f" 2>/dev/null || stat -c%s "$f" 2>/dev/null)
        fdate=$(date -r "$f" "+%Y-%m-%d %H:%M" 2>/dev/null || stat -c '%y' "$f" 2>/dev/null | cut -d. -f1)
        TOTAL=$((TOTAL + fsize_b))
        printf "  %2d. %-45s %8s  %s\n" "$COUNT" "$fname" "$fsize_h" "$fdate"
    done

    if [ $COUNT -eq 0 ]; then
        echo "  (No hay backups)"
    else
        TOTAL_MB=$((TOTAL / 1048576))
        echo "  ─────────────────────────────────────────────────────"
        echo "  Total: $COUNT archivo(s), ~${TOTAL_MB} MB"
    fi
}

limpiar_backups() {
    echo ""
    read -p "  ¿Cuántas copias conservar? [5]: " KEEP
    KEEP=${KEEP:-5}

    COUNT=0
    DELETED=0
    for f in $(ls -t "$BACKUP_DIR"/*.sql 2>/dev/null); do
        COUNT=$((COUNT+1))
        if [ $COUNT -gt $KEEP ]; then
            rm "$f"
            DELETED=$((DELETED+1))
            echo "  Eliminado: $(basename "$f")"
        fi
    done

    if [ $DELETED -eq 0 ]; then
        echo "  No hay backups antiguos para eliminar."
    else
        echo -e "  ${GREEN}[OK]${NC} $DELETED backup(s) eliminado(s). Se conservaron las últimas $KEEP copias."
    fi
}

programar_cron() {
    echo ""
    echo -e "  ${BOLD}Programar backup automático (cron)${NC}"
    echo ""
    echo "  1. Diario (2:00 AM)"
    echo "  2. Semanal (lunes 2:00 AM)"
    echo "  3. Mensual (día 1, 2:00 AM)"
    echo "  4. Eliminar cron existente"
    echo "  5. Cancelar"
    echo ""
    read -p "  Seleccione [1-5]: " FREQ

    SCRIPT_PATH="$(pwd)/backup.sh"
    CRON_CMD="$SCRIPT_PATH --auto"
    CRON_TAG="# TechStock_Backup_Auto"

    if [ "$FREQ" = "5" ]; then return; fi

    if [ "$FREQ" = "4" ]; then
        crontab -l 2>/dev/null | grep -v "TechStock_Backup_Auto" | crontab -
        echo -e "  ${GREEN}[OK]${NC} Cron eliminado."
        return
    fi

    # Eliminar entrada anterior
    crontab -l 2>/dev/null | grep -v "TechStock_Backup_Auto" > /tmp/cron_temp 2>/dev/null || true

    case "$FREQ" in
        1) echo "0 2 * * * $CRON_CMD $CRON_TAG" >> /tmp/cron_temp
           DESC="diario a las 2:00 AM" ;;
        2) echo "0 2 * * 1 $CRON_CMD $CRON_TAG" >> /tmp/cron_temp
           DESC="semanal (lunes 2:00 AM)" ;;
        3) echo "0 2 1 * * $CRON_CMD $CRON_TAG" >> /tmp/cron_temp
           DESC="mensual (día 1, 2:00 AM)" ;;
        *) echo -e "  ${RED}[ERROR]${NC} Opción no válida."; return ;;
    esac

    crontab /tmp/cron_temp
    rm /tmp/cron_temp
    echo -e "  ${GREEN}[OK]${NC} Cron configurado: $DESC"
}

# ── Modo automático (llamado desde cron) ──
if [ "$1" = "--auto" ]; then
    set -e
    crear_backup_completo

    # Limpiar backups automáticos antiguos (conservar 30)
    COUNT=0
    for f in $(ls -t "$BACKUP_DIR"/techstock_auto_*.sql 2>/dev/null "$BACKUP_DIR"/techstock_full_*.sql 2>/dev/null); do
        COUNT=$((COUNT+1))
        if [ $COUNT -gt 30 ]; then
            rm "$f"
        fi
    done
    exit 0
fi

# ── Menú interactivo ──
while true; do
    clear
    echo ""
    echo -e "  ${BOLD}╔═══════════════════════════════════════════════════════╗${NC}"
    echo -e "  ${BOLD}║      TechStock - Copias de Seguridad (Backups)       ║${NC}"
    echo -e "  ${BOLD}╚═══════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  Base de datos: ${CYAN}${PG_DBNAME}${NC} en ${CYAN}${PG_HOST}:${PG_PORT}${NC}"
    echo -e "  Directorio:    ${CYAN}${BACKUP_DIR}${NC}"
    echo ""
    echo -e "  ${BOLD}Opciones:${NC}"
    echo ""
    echo "  1. Crear copia de seguridad completa"
    echo "  2. Crear copia de seguridad (solo datos)"
    echo "  3. Restaurar desde copia de seguridad"
    echo "  4. Ver copias de seguridad existentes"
    echo "  5. Eliminar copias antiguas"
    echo "  6. Programar backup automático (cron)"
    echo "  7. Salir"
    echo ""
    read -p "  Seleccione una opción [1-7]: " opcion

    case "$opcion" in
        1) crear_backup_completo ;;
        2) crear_backup_datos ;;
        3) restaurar_backup ;;
        4) listar_backups ;;
        5) limpiar_backups ;;
        6) programar_cron ;;
        7) exit 0 ;;
        *) echo -e "  ${RED}[ERROR]${NC} Opción no válida." ;;
    esac

    echo ""
    read -p "  Presione ENTER para continuar..."
done
