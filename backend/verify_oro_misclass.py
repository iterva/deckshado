"""
Verificar cartas que deberían ser Oro pero están clasificadas como Aliado.
Busca inconsistencias entre versiones (v1 vs v2) del mismo nombre.
"""
import os, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'backend.settings'
django.setup()

from cards.models import Card, CardType, Race
from django.db.models import Q, Count
from collections import defaultdict

PE_EDITION_SLUGS = ['el-reto', 'mundo-gotico', 'la-ira-del-nahual', 'ragnarok', 'espiritu-de-dragon']

oro_type = CardType.objects.get(slug='oro')
aliado_type = CardType.objects.get(name='Aliado')
noraza = Race.objects.get(slug='noraza')

# ============================================================
# CHECK A: Cartas con mismo nombre base pero diferente tipo
# (ej: "carta" es Oro pero "carta (v2)" es Aliado)
# ============================================================
print("=" * 70)
print("CHECK A: Cartas donde una versión es Oro y otra es Aliado")
print("=" * 70)

pe_cards = Card.objects.filter(edition__slug__in=PE_EDITION_SLUGS)

# Build lookup: base_name -> list of (card, type)
name_map = defaultdict(list)
for c in pe_cards.select_related('card_type', 'race', 'edition'):
    # Normalize name: remove (v2), (v3), (Arte Alternativo), etc.
    base = c.name.lower().strip()
    for suffix in [' (v2)', ' (v3)', ' (v4)', ' (arte alternativo)', ' (v2', ' (v3', ' (v4']:
        base = base.replace(suffix, '')
    base = base.strip().rstrip(')')
    name_map[(base, c.edition.slug)].append(c)

mismatches = []
for (base_name, ed_slug), cards in name_map.items():
    types = set(c.card_type.name if c.card_type else 'None' for c in cards)
    if len(types) > 1 and 'Oro' in types and 'Aliado' in types:
        mismatches.append((base_name, ed_slug, cards))

if mismatches:
    print(f"\n  Encontrados {len(mismatches)} nombres con tipo inconsistente:")
    for base_name, ed_slug, cards in sorted(mismatches):
        print(f"\n  '{base_name}' en {ed_slug}:")
        for c in sorted(cards, key=lambda x: x.myl_id):
            print(f"    {c.name:45s} | type={c.card_type.name:8s} | race={str(c.race):15s} | myl={c.myl_id} | cost={c.cost} | dmg={c.damage}")
else:
    print("  Ninguna inconsistencia encontrada ✓")

# ============================================================
# CHECK B: Aliados con cost=0, damage=0 que tengan la MISMA
# habilidad que un Oro existente
# ============================================================
print(f"\n{'='*70}")
print("CHECK B: Aliados con misma habilidad que un Oro existente")
print("=" * 70)

# Get all Oro abilities
oro_abilities = set()
for c in pe_cards.filter(card_type=oro_type):
    if c.ability:
        oro_abilities.add(c.ability.strip().lower()[:100])

# Find Aliados with same ability
matches_b = []
for c in pe_cards.filter(card_type=aliado_type):
    if c.ability and c.ability.strip().lower()[:100] in oro_abilities:
        matches_b.append(c)

if matches_b:
    print(f"\n  Encontrados {len(matches_b)} aliados con habilidad idéntica a un Oro:")
    for c in sorted(matches_b, key=lambda x: (x.edition.slug, x.name)):
        print(f"    {c.name:40s} | ed={c.edition.slug:20s} | race={str(c.race):15s} | myl={c.myl_id}")
        print(f"      ability: {c.ability[:80]}...")
else:
    print("  Ninguno encontrado ✓")

# ============================================================
# CHECK C: Oros que están como Aliado (comparando por nombre
# con oros conocidos de cualquier edición no-PE)
# ============================================================
print(f"\n{'='*70}")
print("CHECK C: Aliados PE con mismo nombre que un Oro en ediciones IMP/ESC/PB")
print("=" * 70)

# Get all Oro names from non-PE editions
non_pe_oro_names = set()
for c in Card.objects.exclude(edition__slug__in=PE_EDITION_SLUGS).filter(card_type=oro_type):
    non_pe_oro_names.add(c.name.lower().strip())

# Check PE aliados against this
matches_c = []
for c in pe_cards.filter(card_type=aliado_type):
    if c.name.lower().strip() in non_pe_oro_names:
        matches_c.append(c)

if matches_c:
    print(f"\n  Encontrados {len(matches_c)}:")
    for c in sorted(matches_c, key=lambda x: (x.edition.slug, x.name)):
        print(f"    {c.name:40s} | ed={c.edition.slug:20s} | type=Aliado | race={str(c.race)}")
else:
    print("  Ninguno encontrado ✓")

# ============================================================
# CHECK D: Todos los Oros de PE que comparten nombre con Aliados
# (para encontrar el caso inverso: Oros que deberían ser Aliados)
# ============================================================
print(f"\n{'='*70}")
print("CHECK D: Oros PE con nombre duplicado como Aliado en misma edición")
print("=" * 70)

for (base_name, ed_slug), cards in name_map.items():
    oros = [c for c in cards if c.card_type and c.card_type.name == 'Oro']
    aliados = [c for c in cards if c.card_type and c.card_type.name == 'Aliado']
    if oros and aliados:
        # Already caught in CHECK A, skip
        pass

# ============================================================
# CHECK E: Aliados donde el nombre contiene cosas sospechosas
# Y cost=0/vacío Y damage=0/vacío (patrón Cráneo de Dragón)
# ============================================================
print(f"\n{'='*70}")
print("CHECK E: Aliados PE con cost=0/vacío Y damage=0/vacío sin fuerza de combate")
print("(Estos son sospechosos de ser Oros mal clasificados)")
print("=" * 70)

# Get all PE Aliados with cost 0 or empty AND damage 0 or empty
suspects = pe_cards.filter(card_type=aliado_type).filter(
    Q(cost='0') | Q(cost='') | Q(cost__isnull=True)
).filter(
    Q(damage='0') | Q(damage='') | Q(damage__isnull=True)
)

# Among these, find ones whose ability is EXACTLY the same text as a known Oro
print(f"\n  Total aliados con cost=0/vacío y damage=0/vacío: {suspects.count()}")
print(f"  (Esto es normal en PE - muchos aliados legítimos tienen cost 0)")

# Let's compare: among the suspects, which ones have the ability pattern of
# "Cuando entra en juego" + something about Oros
# vs just being a regular ally ability
oro_pattern_suspects = suspects.filter(
    Q(ability__icontains='puedes generar') & Q(ability__icontains='oro') &
    ~Q(ability__icontains='ataca') & ~Q(ability__icontains='bloquea') &
    ~Q(ability__icontains='fuerza') & ~Q(ability__icontains='destruy')
)
if oro_pattern_suspects.exists():
    print(f"\n  Sospechosos fuertes (genera oro, sin mencionar ataque/fuerza/destruir):")
    for c in oro_pattern_suspects.order_by('edition__slug', 'name'):
        print(f"    {c.name:40s} | ed={c.edition.slug:20s} | race={str(c.race):15s} | myl={c.myl_id}")
        print(f"      ability: {c.ability[:100]}")
