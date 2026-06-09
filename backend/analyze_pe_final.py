"""
Análisis final: Cartas PE que NO aparecen en NINGÚN constructor de su edición.
Estas son las verdaderamente "perdidas" - están subidas pero nadie las puede usar.
"""
import os, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'backend.settings'
django.setup()

from cards.models import Card, Edition, Race, CardType
from django.db.models import Q

expected_races = {
    'el-reto': ['caballero', 'dragon', 'faerie'],
    'mundo-gotico': ['cazador', 'vampiro', 'licantropo'],
    'la-ira-del-nahual': ['bestia', 'chaman', 'guerrero'],
    'ragnarok': ['abominacion', 'barbaro', 'dios'],
    'espiritu-de-dragon': ['campeon', 'criaturas', 'kami', 'xian'],
}

print("=" * 70)
print("CARTAS QUE NO APARECEN EN NINGÚN CONSTRUCTOR DE SU EDICIÓN")
print("(Aliados con raza de OTRA edición - no son neutrales ni de las 3 razas)")
print("=" * 70)

total_invisible = 0
for slug, races in expected_races.items():
    ed = Edition.objects.get(slug=slug)
    # Aliados que NO son de ninguna raza esperada NI noraza
    invisible = Card.objects.filter(
        edition=ed,
        card_type__name='Aliado'
    ).exclude(
        Q(race__slug__in=races) | Q(race__isnull=True) | Q(race__slug='noraza')
    )
    
    if invisible.exists():
        print(f"\n{'='*70}")
        print(f"  {ed.title} ({slug}) — {invisible.count()} cartas INVISIBLES")
        print(f"  Razas válidas: {races}")
        print(f"{'='*70}")
        for c in invisible.order_by('race__slug', 'name'):
            race_info = f"{c.race.name} ({c.race.slug})" if c.race else "Sin raza"
            has_img = "✓ img" if c.custom_image_url else "✗ sin img custom"
            print(f"    [{race_info:20s}] {c.name:40s} | myl_id={c.myl_id} | {has_img}")
        total_invisible += invisible.count()

print(f"\n\n{'='*70}")
print(f"TOTAL DE CARTAS INVISIBLES EN CONSTRUCTORES: {total_invisible}")
print(f"{'='*70}")

# Also check: cartas de soporte (no aliados) sin imagen
print(f"\n\n{'='*70}")
print("CARTAS DE SOPORTE SIN custom_image_url (imagen posiblemente rota)")
print("(Solo cartas con edid vacío o '0' que no tienen custom_image_url)")
print(f"{'='*70}")
for slug in expected_races.keys():
    ed = Edition.objects.get(slug=slug)
    broken_img = Card.objects.filter(
        edition=ed
    ).filter(
        Q(edid='') | Q(edid='0')
    ).filter(
        Q(custom_image_url__isnull=True) | Q(custom_image_url='')
    )
    if broken_img.exists():
        print(f"\n  {ed.title}: {broken_img.count()} cartas sin imagen")
        for c in broken_img:
            print(f"    {c.name} | myl_id={c.myl_id} | type={c.card_type}")

# Summary per edition
print(f"\n\n{'='*70}")
print("RESUMEN GENERAL POR EDICIÓN")
print(f"{'='*70}")
for slug, races in expected_races.items():
    ed = Edition.objects.get(slug=slug)
    total = Card.objects.filter(edition=ed).count()
    
    # Cards visible in at least one constructor
    non_ally = ~Q(card_type__name="Aliado")
    any_race_q = Q()
    for r in races:
        any_race_q |= Q(race__slug__icontains=r)
    
    visible_in_any = Card.objects.filter(edition=ed).filter(
        non_ally | any_race_q | Q(race__isnull=True) | Q(race__slug='noraza')
    ).count()
    
    invisible = total - visible_in_any
    
    print(f"\n  {ed.title} ({slug}):")
    print(f"    Total cartas: {total}")
    print(f"    Visibles en al menos 1 constructor: {visible_in_any}")
    print(f"    INVISIBLES (no accesibles): {invisible}")
    
    # Detail by type for visible
    for r in races:
        qs = Card.objects.filter(edition=ed)
        filtered = qs.filter(
            non_ally | Q(race__slug__icontains=r) | Q(race__isnull=True) | Q(race__slug='noraza')
        ).count()
        print(f"      Raza '{r}': {filtered} cartas disponibles")
