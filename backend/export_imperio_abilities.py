"""
Exporta todas las cartas del formato Imperio a un Excel para análisis manual
de habilidades (qué dispara, qué efecto, qué falta implementar en proyecto-imp).

Uso:
    python manage.py shell < export_imperio_abilities.py
o más simple:
    python export_imperio_abilities.py
"""
import os
import sys
import django

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from cards.models import Card

OUTPUT = os.path.join(BASE_DIR, "imperio_abilities.xlsx")

# Columnas: datos de la carta + columnas vacías para que tú las llenes
HEADERS = [
    "myl_id", "Edición", "Edid", "Nombre", "Tipo", "Raza", "Rareza",
    "Costo", "Fuerza", "Habilidad",
    # --- columnas de trabajo ---
    "Trigger",          # etb / activated / fase_final / attack / block / leaves_play / static / passive / none
    "Timing",           # vigilia / tu_turno / cualquier_turno / libre / -
    "Frecuencia",       # once_turn / unlimited / -
    "Costo activación", # paga N oros / descarta / exile X / -
    "Efecto(s)",        # draw / discard / exile / mill / tutor / pump / damage / counter / move_to_zone / transform / static_modifier / notice
    "Objetivo",         # self / opponent / any / all_allies / etc
    "Estado parser",    # OK / parcial / NO / no_aplica
    "Falta implementar",# qué falta para que funcione
    "Notas",
]

qs = (
    Card.objects
    .filter(edition__format__code="imp")
    .select_related("edition", "card_type", "race", "rarity")
    .order_by("card_type__name", "race__name", "edition__date_release", "edid")
)

wb = Workbook()
ws = wb.active
ws.title = "Imperio"

# Header
header_font = Font(bold=True, color="FFFFFF")
header_fill = PatternFill("solid", fgColor="1F2937")
for col_idx, name in enumerate(HEADERS, start=1):
    c = ws.cell(row=1, column=col_idx, value=name)
    c.font = header_font
    c.fill = header_fill
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

# Filas
total = 0
con_hab = 0
sin_hab = 0
for card in qs.iterator():
    ability = (card.ability or "").strip()
    if not ability:
        sin_hab += 1
        continue  # las que no tienen habilidad no necesitan análisis
    con_hab += 1
    row = [
        card.myl_id,
        card.edition.title if card.edition else "",
        card.edid,
        card.name,
        card.card_type.name if card.card_type else "",
        card.race.name if card.race else "",
        card.rarity.name if card.rarity else "",
        card.cost or "",
        card.damage or "",
        ability,
        "", "", "", "", "", "", "", "", "",  # columnas de trabajo vacías
    ]
    ws.append(row)
    total += 1

# Anchos y formato
widths = {
    "A": 12, "B": 28, "C": 6, "D": 28, "E": 14, "F": 18, "G": 12,
    "H": 8,  "I": 8,  "J": 70,
    "K": 14, "L": 16, "M": 14, "N": 22, "O": 30, "P": 18,
    "Q": 14, "R": 28, "S": 28,
}
for col, w in widths.items():
    ws.column_dimensions[col].width = w

# Wrap en habilidad y notas
for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
    for cell in row:
        if cell.column_letter in ("J", "N", "O", "R", "S"):
            cell.alignment = Alignment(wrap_text=True, vertical="top")
        else:
            cell.alignment = Alignment(vertical="top")

ws.freeze_panes = "D2"
ws.auto_filter.ref = ws.dimensions

# Hoja resumen
ws2 = wb.create_sheet("Resumen")
ws2["A1"] = "Cartas Imperio totales"
ws2["B1"] = qs.count()
ws2["A2"] = "Con habilidad (en hoja)"
ws2["B2"] = con_hab
ws2["A3"] = "Sin habilidad (omitidas)"
ws2["B3"] = sin_hab
for r in (1, 2, 3):
    ws2.cell(row=r, column=1).font = Font(bold=True)
ws2.column_dimensions["A"].width = 30
ws2.column_dimensions["B"].width = 12

wb.save(OUTPUT)
print(f"OK -> {OUTPUT}")
print(f"Total Imperio: {qs.count()} | con habilidad: {con_hab} | sin habilidad: {sin_hab}")
