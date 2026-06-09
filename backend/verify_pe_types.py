"""
Verificar y corregir cartas mal clasificadas como Aliado que deberían ser Oro u otro tipo.
Criterios para detectar Oros mal clasificados:
- cost=0 o cost vacío Y damage=0 o damage vacío
- Habilidad típica de Oro (generar oro, etc.)
- Nombre con palabras clave de Oro

También verifica otros tipos mal asignados.
"""
import os, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'backend.settings'
django.setup()

from cards.models import Card, CardType, Race, Edition
from django.db.models import Q

PE_EDITION_SLUGS = ['el-reto', 'mundo-gotico', 'la-ira-del-nahual', 'ragnarok', 'espiritu-de-dragon']

# Get reference types
oro_type = CardType.objects.get(slug='oro')
aliado_type = CardType.objects.get(name='Aliado')
talisman_type = CardType.objects.get(name='Talismán')
arma_type = CardType.objects.get(name='Arma')
totem_type = CardType.objects.get(name='Tótem')
noraza = Race.objects.get(slug='noraza')

print("=" * 70)
print("VERIFICACIÓN: Cartas potencialmente mal clasificadas en PE")
print("=" * 70)

# ============================================================
# CHECK 1: Aliados con cost=0 y damage=0 (probables Oros)
# ============================================================
print("\n--- CHECK 1: Aliados con cost='0' Y damage='0' (probables Oros) ---")
suspects = Card.objects.filter(
    edition__slug__in=PE_EDITION_SLUGS,
    card_type=aliado_type,
    cost='0',
    damage='0'
)
if suspects.exists():
    print(f"  Encontrados: {suspects.count()}")
    for c in suspects.order_by('edition__slug', 'name'):
        ability_preview = (c.ability[:80] + '...') if c.ability and len(c.ability) > 80 else (c.ability or 'None')
        print(f"  {c.name:40s} | ed={c.edition.slug:20s} | race={str(c.race):15s} | myl={c.myl_id}")
        print(f"    ability: {ability_preview}")
else:
    print("  Ninguno encontrado ✓")

# ============================================================
# CHECK 2: Aliados sin cost ni damage (vacíos/null)
# ============================================================
print("\n--- CHECK 2: Aliados sin cost NI damage (vacío/null) ---")
suspects2 = Card.objects.filter(
    edition__slug__in=PE_EDITION_SLUGS,
    card_type=aliado_type,
).filter(
    Q(cost__isnull=True) | Q(cost='') | Q(cost=' ')
).filter(
    Q(damage__isnull=True) | Q(damage='') | Q(damage=' ')
)
if suspects2.exists():
    print(f"  Encontrados: {suspects2.count()}")
    for c in suspects2.order_by('edition__slug', 'name')[:50]:
        ability_preview = (c.ability[:80] + '...') if c.ability and len(c.ability) > 80 else (c.ability or 'None')
        print(f"  {c.name:40s} | ed={c.edition.slug:20s} | race={str(c.race):15s} | myl={c.myl_id}")
        print(f"    ability: {ability_preview}")
    if suspects2.count() > 50:
        print(f"  ... y {suspects2.count() - 50} más")
else:
    print("  Ninguno encontrado ✓")

# ============================================================
# CHECK 3: Oros clasificados como Aliado (habilidad menciona generar oro)
# ============================================================
print("\n--- CHECK 3: Aliados cuya habilidad menciona 'generar' + 'oro' o 'genera' + 'oro' ---")
suspects3 = Card.objects.filter(
    edition__slug__in=PE_EDITION_SLUGS,
    card_type=aliado_type,
).filter(
    Q(ability__icontains='generar') & Q(ability__icontains='oro') |
    Q(ability__icontains='genera') & Q(ability__icontains='oro')
).filter(
    Q(cost='0') | Q(cost='') | Q(cost__isnull=True)
)
if suspects3.exists():
    print(f"  Encontrados: {suspects3.count()}")
    for c in suspects3.order_by('edition__slug', 'name'):
        ability_preview = (c.ability[:100] + '...') if c.ability and len(c.ability) > 100 else (c.ability or 'None')
        print(f"  {c.name:40s} | ed={c.edition.slug:20s} | cost={c.cost} | dmg={c.damage} | race={str(c.race):15s}")
        print(f"    ability: {ability_preview}")
else:
    print("  Ninguno encontrado ✓")

# ============================================================
# CHECK 4: Comparar Oros reales — qué cost/damage tienen
# ============================================================
print("\n--- CHECK 4: Perfil de Oros reales en PE (referencia) ---")
oros = Card.objects.filter(edition__slug__in=PE_EDITION_SLUGS, card_type=oro_type)
cost_vals = oros.values_list('cost', flat=True).distinct()
dmg_vals = oros.values_list('damage', flat=True).distinct()
print(f"  Total Oros PE: {oros.count()}")
print(f"  Valores de cost en Oros: {sorted(set(cost_vals))}")
print(f"  Valores de damage en Oros: {sorted(set(dmg_vals))}")

# ============================================================
# CHECK 5: Aliados con race=noraza — verificar que no son soporte
# misclasificado (Oros, Talismanes, Armas, Tótem)
# ============================================================
print("\n--- CHECK 5: Aliados noraza con cost=0 o sin cost (posibles Oros/soporte) ---")
suspects5 = Card.objects.filter(
    edition__slug__in=PE_EDITION_SLUGS,
    card_type=aliado_type,
    race=noraza,
).filter(
    Q(cost='0') | Q(cost='') | Q(cost__isnull=True)
)
if suspects5.exists():
    print(f"  Encontrados: {suspects5.count()}")
    for c in suspects5.order_by('edition__slug', 'name'):
        ability_preview = (c.ability[:80] + '...') if c.ability and len(c.ability) > 80 else (c.ability or 'None')
        print(f"  {c.name:40s} | ed={c.edition.slug:20s} | cost={c.cost} | dmg={c.damage} | myl={c.myl_id}")
        print(f"    ability: {ability_preview}")
else:
    print("  Ninguno encontrado ✓")

# ============================================================
# CHECK 6: Nombres que indican Oro (moneda, tesoro, mina, etc.)
# pero están como Aliado
# ============================================================
print("\n--- CHECK 6: Aliados con nombres típicos de Oro ---")
oro_keywords = ['moneda', 'tesoro', 'mina ', 'oro ', 'botín', 'riqueza', 'fortuna', 'gema', 'joya']
q_names = Q()
for kw in oro_keywords:
    q_names |= Q(name__icontains=kw)

suspects6 = Card.objects.filter(
    edition__slug__in=PE_EDITION_SLUGS,
    card_type=aliado_type,
).filter(q_names)
if suspects6.exists():
    print(f"  Encontrados: {suspects6.count()}")
    for c in suspects6.order_by('edition__slug', 'name'):
        print(f"  {c.name:40s} | ed={c.edition.slug:20s} | cost={c.cost} | dmg={c.damage} | race={str(c.race)}")
else:
    print("  Ninguno encontrado ✓")

# ============================================================
# CHECK 7: Verificar Talismanes/Armas/Tótem con race != noraza
# (soporte no debería tener raza, salvo excepciones raciales)
# ============================================================
print("\n--- CHECK 7: Soporte (Talismán/Arma/Tótem) con raza != noraza ---")
soporte_types = [talisman_type, arma_type, totem_type]
suspects7 = Card.objects.filter(
    edition__slug__in=PE_EDITION_SLUGS,
    card_type__in=soporte_types,
).exclude(
    Q(race=noraza) | Q(race__isnull=True)
)
if suspects7.exists():
    print(f"  Encontrados: {suspects7.count()}")
    for c in suspects7.order_by('edition__slug', 'card_type__name', 'name')[:40]:
        print(f"  [{c.card_type.name:10s}] {c.name:35s} | ed={c.edition.slug:20s} | race={c.race.name} ({c.race.slug})")
    if suspects7.count() > 40:
        print(f"  ... y {suspects7.count() - 40} más")
else:
    print("  Ninguno encontrado ✓")
