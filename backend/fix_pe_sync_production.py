"""
Script DEFINITIVO para sincronizar clasificación PE en producción.
Fuerza el tipo, raza y edición correctos para TODAS las cartas PE.
Ejecutar en PythonAnywhere después de git pull.
"""
import django, os, sys, json
os.environ['DJANGO_SETTINGS_MODULE'] = 'backend.settings'
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from cards.models import Card, CardType, Race, Edition

# Cargar estado correcto
json_path = os.path.join(os.path.dirname(__file__), 'pe_correct_state.json')
with open(json_path, 'r', encoding='utf-8') as f:
    correct_state = json.load(f)

print(f"Cartas a sincronizar: {len(correct_state)}")

# Cache de tipos, razas y ediciones
types_cache = {t.name: t for t in CardType.objects.all()}
races_cache = {r.slug: r for r in Race.objects.all()}
editions_cache = {e.slug: e for e in Edition.objects.all()}

fixed_type = 0
fixed_race = 0
fixed_edition = 0
not_found = 0

for myl_id, state in correct_state.items():
    try:
        card = Card.objects.get(myl_id=myl_id)
    except Card.DoesNotExist:
        not_found += 1
        continue

    correct_type = types_cache[state['type']]
    correct_race = races_cache[state['race']]
    correct_edition = editions_cache[state['edition']]

    updates = {}
    if card.card_type_id != correct_type.id:
        updates['card_type'] = correct_type
        fixed_type += 1
    if card.race_id != correct_race.id:
        updates['race'] = correct_race
        fixed_race += 1
    if card.edition_id != correct_edition.id:
        updates['edition'] = correct_edition
        fixed_edition += 1

    if updates:
        for field, value in updates.items():
            setattr(card, field, value)
        card.save(update_fields=list(updates.keys()))

print(f"\nResultado:")
print(f"  Tipo corregido: {fixed_type}")
print(f"  Raza corregida: {fixed_race}")
print(f"  Edición corregida: {fixed_edition}")
print(f"  No encontradas en producción: {not_found}")

# Verificación
pe_editions = ['el-reto', 'mundo-gotico', 'la-ira-del-nahual', 'ragnarok', 'espiritu-de-dragon']
print(f"\n=== VERIFICACIÓN ===")
bad = Card.objects.filter(
    edition__slug__in=pe_editions,
    card_type__name__in=['Oro', 'Arma', 'Talismán', 'Tótem']
).exclude(race__slug='noraza').exclude(race__isnull=True)
print(f"No-Aliado con raza específica: {bad.count()} (debe ser 0)")

for ed in pe_editions:
    noraza_allies = Card.objects.filter(edition__slug=ed, card_type__name='Aliado', race__slug='noraza').count()
    print(f"  {ed}: {noraza_allies} Aliados Sin Raza (debe ser 0)")

print("\nScript completado.")
