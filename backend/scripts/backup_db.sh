#!/usr/bin/env bash
# Backup automático de la base de datos SQLite y archivos media de Deckshado.
# Mantiene los últimos 14 días de backups locales.
#
# Uso (PythonAnywhere o cualquier Linux):
#   chmod +x backend/scripts/backup_db.sh
#   ./backend/scripts/backup_db.sh
#
# Cron sugerido (diario 3am UTC):
#   0 3 * * * /home/iterva/Proyecto-deckshado/backend/scripts/backup_db.sh >> /home/iterva/backup.log 2>&1
#
# Para descargar el backup más reciente desde tu máquina:
#   scp pythonanywhere:~/Proyecto-deckshado/backend/backups/db_latest.sqlite3 ./

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DB_PATH="$BACKEND_DIR/db.sqlite3"
BACKUP_DIR="$BACKEND_DIR/backups"
RETENTION_DAYS=14
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

mkdir -p "$BACKUP_DIR"

if [ ! -f "$DB_PATH" ]; then
  echo "[backup] ERROR: no existe $DB_PATH" >&2
  exit 1
fi

# Backup consistente con sqlite3 .backup (no requiere parar el server).
BACKUP_FILE="$BACKUP_DIR/db_${TIMESTAMP}.sqlite3"
if command -v sqlite3 >/dev/null 2>&1; then
  sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'"
else
  # Fallback a copia simple
  cp "$DB_PATH" "$BACKUP_FILE"
fi

# Comprimir
gzip -f "$BACKUP_FILE"
BACKUP_FILE_GZ="${BACKUP_FILE}.gz"

# Symlink "latest" para descarga fácil
ln -sf "$BACKUP_FILE_GZ" "$BACKUP_DIR/db_latest.sqlite3.gz"

# Borrar backups más viejos que RETENTION_DAYS
find "$BACKUP_DIR" -name 'db_*.sqlite3.gz' -type f -mtime +${RETENTION_DAYS} -delete

echo "[backup] OK -> $BACKUP_FILE_GZ"
