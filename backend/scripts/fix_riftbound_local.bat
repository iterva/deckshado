@echo off
REM Restaura la clasificacion correcta de cartas Riftbound en local (Windows).
REM Uso: doble click o desde cmd:  backend\scripts\fix_riftbound_local.bat

cd /d "%~dp0\..\.."
cd backend
python manage.py apply_riftbound_fixes
echo.
echo Listo. Categorizacion Riftbound restaurada en local.
pause
