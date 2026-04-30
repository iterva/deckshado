# Backups automáticos de la base de datos

Script: `backend/scripts/backup_db.sh`

## Qué hace
- Crea un snapshot consistente de `db.sqlite3` en `backend/backups/db_YYYYMMDD_HHMMSS.sqlite3.gz`.
- Mantiene los últimos **14 días** y borra el resto.
- Crea un symlink `db_latest.sqlite3.gz` apuntando al backup más reciente.

## Configurar en PythonAnywhere

1. Sube los cambios y reinstala:
   ```bash
   cd ~/Proyecto-deckshado
   git pull
   chmod +x backend/scripts/backup_db.sh
   ```
2. Ve a la pestaña **Tasks** en PythonAnywhere y crea una tarea diaria:
   - Hora UTC: `03:00`
   - Comando: `/home/iterva/Proyecto-deckshado/backend/scripts/backup_db.sh`

   > El plan free permite **1 tarea diaria** y se desactiva sola cada cierto tiempo (hay que reactivarla).

## Descargar backup desde tu PC (Windows / PowerShell)

Usando el panel de archivos web de PythonAnywhere o vía API:

```powershell
# Reemplaza TU_API_TOKEN con el token de https://www.pythonanywhere.com/account/#api_token
$token = "TU_API_TOKEN"
$path  = "/home/iterva/Proyecto-deckshado/backend/backups/db_latest.sqlite3.gz"
Invoke-WebRequest `
  -Uri "https://www.pythonanywhere.com/api/v0/user/iterva/files/path$path" `
  -Headers @{ Authorization = "Token $token" } `
  -OutFile "db_latest.sqlite3.gz"
```

## Backup manual ad-hoc

```bash
ssh iterva@ssh.pythonanywhere.com   # solo planes pagos
# o usa la consola web → Bash console
~/Proyecto-deckshado/backend/scripts/backup_db.sh
```

## Restaurar un backup

```bash
cd ~/Proyecto-deckshado/backend
gunzip -c backups/db_20260101_030000.sqlite3.gz > db.sqlite3.restored
mv db.sqlite3 db.sqlite3.bak
mv db.sqlite3.restored db.sqlite3
# Reload la web app desde el dashboard de PythonAnywhere
```
