"""
Buscar cartas que aparecen como Aliado con MÚLTIPLES razas en la misma edición PE.
Patrón: misma habilidad + diferente raza = probablemente Oro/soporte mal clasificado.
"""
import os, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'backend.settings'
django.setup()

from cards.models import Card, CardType, Race, Edition
from django.db.models import Q
from collections import defaultdict

PE_EDITION_SLUGS = ['el-reto', 'mundo-gotico', 'la-ira-del-nahual', 'ragnarok', 'espiritu-de-dragon']

expected_races = {
    'el-reto': ['caballero', 'dragon', 'faerie'],
    'mundo-gotico': ['cazador', 'vampiro', 'licantropo'],
    'la-ira-del-nahual': ['bestia', 'chaman', 'guerrero'],
    'ragnarok': ['abominacion', 'barbaro', 'dios'],
    'espiritu-de-dragon': ['campeon', 'criaturas', 'kami', 'xian'],
}

oro_type = CardType.objects.get(slug='oro')
aliado_type = CardType.objects.get(name='Aliado')
talisman_type = CardType.objects.get(name='Talismán')
arma_type = CardType.objects.get(name='Arma')
totem_type = CardType.objects.get(name='Tótem')
noraza = Race.objects.get(slug='noraza')

print("=" * 70)
print("PATRÓN: Aliados con MISMA habilidad pero DIFERENTE raza en misma edición")
print("(Estos son probablemente Oros/soporte mal clasificados como Aliado)")
print("=" * 70)

# Group aliados by (edition, ability_normalized)
for ed_slug in PE_EDITION_SLUGS:
    ed_races = expected_races[ed_slug]
    ability_groups = defaultdict(list)
    
    aliados = Card.objects.filter(
        edition__slug=ed_slug,
        card_type=aliado_type
    ).exclude(Q(ability__isnull=True) | Q(ability=''))
    
    for c in aliados.select_related('race'):
        # Normalize ability for comparison
        ab_norm = c.ability.strip().lower()[:80] if c.ability else ''
        if ab_norm:
            ability_groups[ab_norm].append(c)
    
    # Find groups where cards have different races
    multi_race = []
    for ab, cards in ability_groups.items():
        races = set(c.race.slug if c.race else 'none' for c in cards)
        # Filter to only edition's own races
        edition_races_present = races.intersection(set(ed_races))
        if len(edition_races_present) >= 2:
            multi_race.append((ab, cards, edition_races_present))
    
    if multi_race:
        ed_obj = Edition.objects.get(slug=ed_slug)
        print(f"\n{'='*70}")
        print(f"  {ed_obj.title} ({ed_slug}) — {len(multi_race)} cartas con múltiples razas")
        print(f"{'='*70}")
        for ab, cards, races_present in sorted(multi_race, key=lambda x: x[1][0].name.lower()):
            print(f"\n  Habilidad: {ab[:90]}...")
            print(f"  Razas: {sorted(races_present)}")
            for c in sorted(cards, key=lambda x: x.race.slug if x.race else ''):
                print(f"    {c.name:40s} | race={c.race.name if c.race else 'None':15s} | myl={c.myl_id} | cost={c.cost} | dmg={c.damage}")

print(f"\n\n{'='*70}")
print("RESUMEN: Cartas a corregir")
print("=" * 70)

# Collect all cards that appear with 2+ different edition races with same ability
to_fix = []
for ed_slug in PE_EDITION_SLUGS:
    ed_races = expected_races[ed_slug]
    ability_groups = defaultdict(list)
    
    aliados = Card.objects.filter(
        edition__slug=ed_slug,
        card_type=aliado_type
    ).exclude(Q(ability__isnull=True) | Q(ability=''))
    
    for c in aliados.select_related('race', 'edition'):
        ab_norm = c.ability.strip().lower()[:80] if c.ability else ''
        if ab_norm:
            ability_groups[ab_norm].append(c)
    
    for ab, cards in ability_groups.items():
        races = set(c.race.slug if c.race else 'none' for c in cards)
        edition_races_present = races.intersection(set(ed_races))
        if len(edition_races_present) >= 2:
            to_fix.extend(cards)

print(f"\n  Total cartas a reclasificar como Oro: {len(to_fix)}")
for c in sorted(to_fix, key=lambda x: (x.edition.slug, x.name.lower())):
    print(f"    {c.name:40s} | ed={c.edition.slug:20s} | race={c.race.name if c.race else 'None':15s} | myl={c.myl_id}")
