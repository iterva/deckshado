#!/usr/bin/env bash
# Restaura la clasificacion correcta de cartas Riftbound en PythonAnywhere.
# Uso (desde cualquier carpeta en PA con el virtualenv activado):
#   bash ~/deckshado/backend/scripts/fix_riftbound_pa.sh
#
# Lo que hace:
#   1. git pull en ~/deckshado (por si hay nuevos fixes en el repo).
#   2. python manage.py apply_riftbound_fixes
#        - reclasifica heuristicamente (unit/spell/gear/battlefield/legend)
#        - oculta cartas con arte placeholder (/missing/)
#        - fuerza legends manuales
#        - aplica colores canonicos
#        - unifica colores entre variantes del mismo champion
#   3. touch al WSGI para recargar la app web.
#
# Si load_riftbound_cards (o cualquier otra cosa) vuelve a romper la
# clasificacion, basta con re-ejecutar este script.

set -e

REPO_DIR="${REPO_DIR:-$HOME/deckshado}"
WSGI_FILE="${WSGI_FILE:-/var/www/iterva_pythonanywhere_com_wsgi.py}"

echo "==> git pull en $REPO_DIR"
cd "$REPO_DIR"
git pull --ff-only

echo "==> python manage.py apply_riftbound_fixes"
cd "$REPO_DIR/backend"
python manage.py apply_riftbound_fixes

if [ -f "$WSGI_FILE" ]; then
  echo "==> touch $WSGI_FILE (reload webapp)"
  touch "$WSGI_FILE"
else
  echo "!! WSGI no encontrado en $WSGI_FILE (skip reload)"
fi

echo "==> Listo. Categorizacion Riftbound restaurada."
