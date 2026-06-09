"""
Fix: Reasignar cartas PE con raza incorrecta a su edición correcta.
"""
import os, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'backend.settings'
django.setup()

from cards.models import Card, Edition
from django.db.models import Q

# Mapping: race slug → correct edition slug
RACE_TO_EDITION = {
    'caballero': 'el-reto',
    'dragon': 'el-reto',
    'faerie': 'el-reto',
    'cazador': 'mundo-gotico',
    'vampiro': 'mundo-gotico',
    'licantropo': 'mundo-gotico',
    'bestia': 'la-ira-del-nahual',
    'chaman': 'la-ira-del-nahual',
    'guerrero': 'la-ira-del-nahual',
    'abominacion': 'ragnarok',
    'barbaro': 'ragnarok',
    'dios': 'ragnarok',
    'campeon': 'espiritu-de-dragon',
    'criaturas': 'espiritu-de-dragon',
    'kami': 'espiritu-de-dragon',
    'xian': 'espiritu-de-dragon',
}

PE_EDITION_SLUGS = ['el-reto', 'mundo-gotico', 'la-ira-del-nahual', 'ragnarok', 'espiritu-de-dragon']

# Find ALL misassigned cards across ALL PE editions
print("=" * 70)
print("BUSCANDO CARTAS MAL ASIGNADAS EN TODAS LAS EDICIONES PE...")
print("=" * 70)

fixes = []
for ed_slug in PE_EDITION_SLUGS:
    ed = Edition.objects.get(slug=ed_slug)
    # Get all allies in this edition that have a race belonging to another edition
    allies = Card.objects.filter(edition=ed, card_type__name='Aliado').exclude(
        Q(race__isnull=True) | Q(race__slug='noraza')
    )
    for card in allies:
        if card.race and card.race.slug in RACE_TO_EDITION:
            correct_ed_slug = RACE_TO_EDITION[card.race.slug]
            if correct_ed_slug != ed_slug:
                fixes.append((card, ed_slug, correct_ed_slug))

print(f"\nEncontradas {len(fixes)} cartas mal asignadas:\n")

# Group by current edition -> target edition
from collections import defaultdict
grouped = defaultdict(list)
for card, from_ed, to_ed in fixes:
    grouped[(from_ed, to_ed)].append(card)

for (from_ed, to_ed), cards in sorted(grouped.items()):
    print(f"\n  {from_ed} → {to_ed} ({len(cards)} cartas):")
    for c in sorted(cards, key=lambda x: x.name):
        print(f"    {c.name} (myl_id={c.myl_id}, race={c.race.slug})")

# Apply fixes
print(f"\n{'='*70}")
print("APLICANDO CORRECCIONES...")
print(f"{'='*70}")

moved = 0
for card, from_ed, to_ed in fixes:
    target_edition = Edition.objects.get(slug=to_ed)
    card.edition = target_edition
    card.save(update_fields=['edition'])
    moved += 1

print(f"\n✓ {moved} cartas reasignadas correctamente.")

# Verify: check again
print(f"\n{'='*70}")
print("VERIFICACIÓN POST-FIX:")
print(f"{'='*70}")

expected_races = {
    'el-reto': ['caballero', 'dragon', 'faerie'],
    'mundo-gotico': ['cazador', 'vampiro', 'licantropo'],
    'la-ira-del-nahual': ['bestia', 'chaman', 'guerrero'],
    'ragnarok': ['abominacion', 'barbaro', 'dios'],
    'espiritu-de-dragon': ['campeon', 'criaturas', 'kami', 'xian'],
}

total_invisible = 0
for slug, races in expected_races.items():
    ed = Edition.objects.get(slug=slug)
    invisible = Card.objects.filter(
        edition=ed, card_type__name='Aliado'
    ).exclude(
        Q(race__slug__in=races) | Q(race__isnull=True) | Q(race__slug='noraza')
    )
    if invisible.exists():
        print(f"  ⚠ {ed.title}: {invisible.count()} cartas aún invisibles")
        for c in invisible:
            print(f"    {c.name} | race={c.race.slug if c.race else 'None'}")
        total_invisible += invisible.count()
    else:
        total = Card.objects.filter(edition=ed).count()
        print(f"  ✓ {ed.title}: OK ({total} cartas, todas accesibles)")

if total_invisible == 0:
    print(f"\n✓ TODAS las cartas PE son ahora accesibles en sus constructores.")
else:
    print(f"\n⚠ Aún quedan {total_invisible} cartas invisibles.")
