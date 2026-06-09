"""
Análisis de cartas Primera Era - verificar cuáles aparecen en el constructor y cuáles no.
"""
import os, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'backend.settings'
django.setup()

from cards.models import Card, Edition, Race, CardType
from django.db.models import Q

print("=" * 60)
print("ANÁLISIS DE CARTAS PRIMERA ERA")
print("=" * 60)

# 1. Listar ediciones PE
pe_editions = Edition.objects.filter(format__code='pe')
print("\n=== Ediciones PE en la DB ===")
for e in pe_editions:
    count = Card.objects.filter(edition=e).count()
    print(f"  {e.slug} ({e.title}) - {count} cartas - myl_id={e.myl_id}")

# 2. Buscar "craneo" en cualquier edición
print("\n=== Cartas con 'craneo' o 'cráneo' en el nombre ===")
cards = Card.objects.filter(Q(name__icontains='craneo') | Q(name__icontains='cráneo'))
for c in cards:
    print(f"  {c.name} | edition={c.edition.slug} | type={c.card_type} | race={c.race} | race_slug={c.race.slug if c.race else 'None'} | edid={c.edid} | myl_id={c.myl_id}")

# 3. Todas las ediciones en la DB (no solo PE)
print("\n=== Todas las ediciones ===")
all_editions = Edition.objects.all()
for e in all_editions:
    count = Card.objects.filter(edition=e).count()
    fmt = e.format.code if e.format else 'sin-formato'
    print(f"  {e.slug} ({e.title}) - formato={fmt} - {count} cartas")

# 4. Para cada edición PE, verificar qué razas tienen sus cartas
print("\n=== Razas por edición PE ===")
pe_ed_slugs = ['el-reto', 'mundo-gotico', 'la-ira-del-nahual', 'ragnarok', 'espiritu-de-dragon']
for slug in pe_ed_slugs:
    ed = Edition.objects.filter(slug=slug).first()
    if not ed:
        print(f"\n  !! Edición '{slug}' NO ENCONTRADA en DB !!")
        continue
    print(f"\n  --- {ed.title} ({slug}) ---")
    cards = Card.objects.filter(edition=ed)
    types = cards.values_list('card_type__name', flat=True).distinct()
    print(f"  Tipos: {list(types)}")
    races = cards.values_list('race__name', 'race__slug', flat=False).distinct()
    print(f"  Razas: {list(races)}")
    
    # Count by type
    for t in types:
        cnt = cards.filter(card_type__name=t).count()
        print(f"    {t}: {cnt}")

# 5. Simular el filtro deck_race=dragon para el-reto
print("\n=== Simulación: deck_race=dragon + edition=el-reto ===")
qs = Card.objects.filter(edition__slug='el-reto')
non_ally = ~Q(card_type__name="Aliado")
filtered = qs.filter(
    non_ally
    | Q(race__slug__icontains='dragon')
    | Q(race__isnull=True)
    | Q(race__slug='noraza')
)
print(f"  Total cartas el-reto: {qs.count()}")
print(f"  Después de filtro deck_race=dragon: {filtered.count()}")
print(f"  Excluidas: {qs.count() - filtered.count()}")

# Mostrar las excluidas
excluded = qs.exclude(
    non_ally
    | Q(race__slug__icontains='dragon')
    | Q(race__isnull=True)
    | Q(race__slug='noraza')
)
if excluded.exists():
    print("  Cartas excluidas:")
    for c in excluded:
        print(f"    {c.name} | type={c.card_type} | race={c.race} (slug={c.race.slug if c.race else 'None'})")

# 6. Verificar formato PE
print("\n=== Verificar formato PE ===")
from cards.models import Format
pe_fmt = Format.objects.filter(code='pe').first()
if pe_fmt:
    print(f"  Formato PE: {pe_fmt.name} (code={pe_fmt.code})")
    pe_eds = Edition.objects.filter(format=pe_fmt)
    print(f"  Ediciones asociadas: {[e.slug for e in pe_eds]}")
else:
    print("  !! FORMATO 'pe' NO EXISTE EN DB !!")

# 7. Ediciones que tienen slug de PE pero no tienen formato asignado o diferente
print("\n=== Ediciones con slug PE sin formato correcto ===")
for slug in pe_ed_slugs:
    ed = Edition.objects.filter(slug=slug).first()
    if ed:
        fmt_code = ed.format.code if ed.format else 'NINGUNO'
        print(f"  {slug}: formato={fmt_code}")
