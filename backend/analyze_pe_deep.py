"""
Análisis profundo: cartas PE con problemas de datos que afectan su visibilidad en el constructor.
"""
import os, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'backend.settings'
django.setup()

from cards.models import Card, Edition, Race, CardType
from django.db.models import Q, Count

print("=" * 70)
print("ANÁLISIS PROFUNDO: PROBLEMAS DE DATOS EN CARTAS PE")
print("=" * 70)

pe_ed_slugs = ['el-reto', 'mundo-gotico', 'la-ira-del-nahual', 'ragnarok', 'espiritu-de-dragon']

# Expected races per edition (from format-select component)
expected_races = {
    'el-reto': ['caballero', 'dragon', 'faerie'],
    'mundo-gotico': ['cazador', 'vampiro', 'licantropo'],
    'la-ira-del-nahual': ['bestia', 'chaman', 'guerrero'],
    'ragnarok': ['abominacion', 'barbaro', 'dios'],
    'espiritu-de-dragon': ['campeon', 'criaturas', 'kami', 'xian'],
}

# ============================================================
# PROBLEMA 1: Cartas con edid vacío o "0"
# ============================================================
print("\n" + "=" * 70)
print("PROBLEMA 1: Cartas con edid vacío o '0' (imagen rota)")
print("=" * 70)
for slug in pe_ed_slugs:
    bad = Card.objects.filter(edition__slug=slug).filter(Q(edid='') | Q(edid='0') | Q(edid__isnull=True))
    if bad.exists():
        print(f"\n  --- {slug} ({bad.count()} cartas con edid problemático) ---")
        for c in bad:
            print(f"    {c.name} | myl_id={c.myl_id} | edid='{c.edid}' | type={c.card_type} | race={c.race}")

# ============================================================
# PROBLEMA 2: Aliados con razas que NO pertenecen a su edición
# ============================================================
print("\n" + "=" * 70)
print("PROBLEMA 2: Aliados con razas INESPERADAS para su edición")
print("(Razas de OTRAS ediciones que no deberían estar ahí)")
print("=" * 70)
for slug in pe_ed_slugs:
    exp_races = expected_races[slug]
    allies = Card.objects.filter(
        edition__slug=slug, 
        card_type__name='Aliado'
    ).exclude(
        Q(race__slug__in=exp_races) | Q(race__slug='noraza') | Q(race__isnull=True)
    )
    if allies.exists():
        print(f"\n  --- {slug} ({allies.count()} aliados con raza inesperada) ---")
        print(f"      Razas esperadas: {exp_races}")
        race_counts = allies.values_list('race__slug', 'race__name').annotate(cnt=Count('id'))
        for race_slug, race_name, cnt in race_counts:
            print(f"      Raza '{race_name}' (slug={race_slug}): {cnt} cartas")
        for c in allies[:20]:
            print(f"    {c.name} | myl_id={c.myl_id} | race={c.race} (slug={c.race.slug if c.race else 'N/A'})")

# ============================================================
# PROBLEMA 3: Cartas duplicadas (mismo nombre en misma edición)
# ============================================================
print("\n" + "=" * 70)
print("PROBLEMA 3: Cartas duplicadas (mismo nombre, misma edición)")
print("=" * 70)
for slug in pe_ed_slugs:
    dupes = (Card.objects.filter(edition__slug=slug)
             .values('name')
             .annotate(cnt=Count('id'))
             .filter(cnt__gt=1)
             .order_by('-cnt'))
    if dupes.exists():
        print(f"\n  --- {slug} ({dupes.count()} nombres duplicados) ---")
        for d in dupes[:30]:
            cards = Card.objects.filter(edition__slug=slug, name=d['name'])
            races = [(c.myl_id, c.race.slug if c.race else 'None', c.edid, c.card_type.name if c.card_type else 'None') for c in cards]
            print(f"    '{d['name']}' x{d['cnt']}: {races}")

# ============================================================
# PROBLEMA 4: Cartas sin tipo asignado
# ============================================================
print("\n" + "=" * 70)
print("PROBLEMA 4: Cartas sin card_type")
print("=" * 70)
for slug in pe_ed_slugs:
    no_type = Card.objects.filter(edition__slug=slug, card_type__isnull=True)
    if no_type.exists():
        print(f"\n  --- {slug} ({no_type.count()} cartas sin tipo) ---")
        for c in no_type:
            print(f"    {c.name} | myl_id={c.myl_id} | edid={c.edid}")

# ============================================================
# PROBLEMA 5: Resumen de disponibilidad por raza/edición
# ============================================================
print("\n" + "=" * 70)
print("RESUMEN: Cartas disponibles por raza en el constructor")
print("=" * 70)
for slug in pe_ed_slugs:
    ed = Edition.objects.get(slug=slug)
    total = Card.objects.filter(edition=ed).count()
    exp_races = expected_races[slug]
    print(f"\n  --- {ed.title} (Total: {total}) ---")
    
    for race_slug in exp_races:
        # Simulate deck_race filter
        qs = Card.objects.filter(edition=ed)
        non_ally = ~Q(card_type__name="Aliado")
        filtered = qs.filter(
            non_ally
            | Q(race__slug__icontains=race_slug)
            | Q(race__isnull=True)
            | Q(race__slug='noraza')
        )
        allies_matching = qs.filter(card_type__name='Aliado', race__slug__icontains=race_slug).count()
        non_allies = qs.filter(non_ally).count()
        noraza = qs.filter(card_type__name='Aliado').filter(Q(race__isnull=True) | Q(race__slug='noraza')).count()
        print(f"    {race_slug}: {filtered.count()} total ({allies_matching} aliados raza + {noraza} aliados noraza + {non_allies} soporte)")

# ============================================================
# PROBLEMA 6: Cartas con custom_image_url (subidas manualmente)
# que podrían no estar mostrando correctamente
# ============================================================
print("\n" + "=" * 70)
print("PROBLEMA 6: Cartas con custom_image_url en PE")
print("=" * 70)
for slug in pe_ed_slugs:
    custom = Card.objects.filter(edition__slug=slug).exclude(Q(custom_image_url__isnull=True) | Q(custom_image_url=''))
    if custom.exists():
        print(f"\n  --- {slug} ({custom.count()} cartas con imagen custom) ---")
        for c in custom[:10]:
            print(f"    {c.name} | myl_id={c.myl_id} | url={c.custom_image_url[:80]}...")
