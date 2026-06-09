"""
Fix: Corregir cartas PE con múltiples razas (son neutrales mal clasificadas).
1. Todas pasan a race=noraza (para aparecer en todos los constructores)
2. Las que mencionan "este Oro" o "Reserva de Oro" pasan a type=Oro
3. Las que mencionan "su portador" pasan a type=Arma
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
arma_type = CardType.objects.get(name='Arma')
totem_type = CardType.objects.get(name='Tótem')
talisman_type = CardType.objects.get(name='Talismán')
noraza = Race.objects.get(slug='noraza')

# Find all multi-race pattern cards
to_fix_ids = set()
for ed_slug in PE_EDITION_SLUGS:
    ed_races = expected_races[ed_slug]
    ability_groups = defaultdict(list)
    
    aliados = Card.objects.filter(
        edition__slug=ed_slug,
        card_type=aliado_type
    ).exclude(Q(ability__isnull=True) | Q(ability=''))
    
    for c in aliados.select_related('race'):
        ab_norm = c.ability.strip().lower()[:80] if c.ability else ''
        if ab_norm:
            ability_groups[ab_norm].append(c)
    
    for ab, cards in ability_groups.items():
        races = set(c.race.slug if c.race else 'none' for c in cards)
        edition_races_present = races.intersection(set(ed_races))
        if len(edition_races_present) >= 2:
            for c in cards:
                to_fix_ids.add(c.id)

cards_to_fix = Card.objects.filter(id__in=to_fix_ids).select_related('card_type', 'race', 'edition')

print(f"Total cartas a corregir: {cards_to_fix.count()}")
print("=" * 70)

# Categorize and fix
fixed_oro = 0
fixed_arma = 0
fixed_race_only = 0

for card in cards_to_fix:
    ability_lower = card.ability.lower() if card.ability else ''
    new_type = card.card_type
    new_race = noraza
    
    # Detect Oros: mentions "este oro" or "reserva de oro"
    if 'este oro' in ability_lower or 'reserva de oro' in ability_lower:
        new_type = oro_type
        fixed_oro += 1
    # Detect Armas: mentions "su portador"
    elif 'su portador' in ability_lower:
        new_type = arma_type
        fixed_arma += 1
    else:
        fixed_race_only += 1
    
    # Apply fix
    changed = False
    if card.race != noraza:
        card.race = noraza
        changed = True
    if card.card_type != new_type:
        card.card_type = new_type
        changed = True
    
    if changed:
        card.save(update_fields=['race', 'card_type'])

print(f"\nResultado:")
print(f"  Cambiados a Oro + noraza: {fixed_oro}")
print(f"  Cambiados a Arma + noraza: {fixed_arma}")
print(f"  Solo cambio de raza a noraza: {fixed_race_only}")
print(f"  Total: {fixed_oro + fixed_arma + fixed_race_only}")

# Verification
print(f"\n{'='*70}")
print("VERIFICACIÓN POST-FIX:")
print("=" * 70)

for slug, races in expected_races.items():
    ed = Edition.objects.get(slug=slug)
    total = Card.objects.filter(edition=ed).count()
    
    # Check if any aliados still have multi-race issues
    non_ally = ~Q(card_type__name="Aliado")
    any_race_q = Q()
    for r in races:
        any_race_q |= Q(race__slug__icontains=r)
    
    visible = Card.objects.filter(edition=ed).filter(
        non_ally | any_race_q | Q(race__isnull=True) | Q(race__slug='noraza')
    ).count()
    
    invisible = total - visible
    
    # Count per race
    race_counts = []
    for r in races:
        cnt = Card.objects.filter(edition=ed).filter(
            non_ally | Q(race__slug__icontains=r) | Q(race__isnull=True) | Q(race__slug='noraza')
        ).count()
        race_counts.append(f"{r}={cnt}")
    
    status = "✓" if invisible == 0 else f"⚠ {invisible} invisibles"
    print(f"  {ed.title}: {total} total, {status}")
    print(f"    Por raza: {', '.join(race_counts)}")
