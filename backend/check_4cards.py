import django, os, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'backend.settings'
sys.path.insert(0, os.path.dirname(__file__))
django.setup()
from cards.models import Card, Race, CardType

noraza = Race.objects.get(slug='noraza')
kami = Race.objects.get(slug='kami')
xian = Race.objects.get(slug='xian')
criaturas = Race.objects.get(slug='criaturas')
campeon = Race.objects.get(slug='campeon')
arma = CardType.objects.get(name='Arma')
oro = CardType.objects.get(name='Oro')

ed = 'espiritu-de-dragon'

# Kami: Ama No Fuchigoma, Gozu Tenno, Konpira Gongen, Ninigi No Mikoto
kami_names = ['Ama No Fuchigoma', 'Gozu Tenno', 'Konpira Gongen', 'Ninigi No Mikoto']
count = 0
for name in kami_names:
    count += Card.objects.filter(name__iexact=name, edition__slug=ed, race=noraza).update(race=kami)
    count += Card.objects.filter(name__istartswith=name, edition__slug=ed, race=noraza, card_type__name='Aliado').update(race=kami)
print(f"Kami: {count}")

# Xian: Cabeza de Buey, Cara de Caballo, Han Xiang Zi, Meng Po
xian_names = ['Cabeza de Buey', 'Cara de Caballo', 'Han Xiang Zi', 'Meng Po']
count = 0
for name in xian_names:
    count += Card.objects.filter(name__iexact=name, edition__slug=ed, race=noraza).update(race=xian)
    count += Card.objects.filter(name__istartswith=name, edition__slug=ed, race=noraza, card_type__name='Aliado').update(race=xian)
print(f"Xian: {count}")

# Criaturas: Longma, Qianlima, Shachihoko, Tianma
criaturas_names = ['Longma', 'Qianlima', 'Shachihoko', 'Tianma']
count = 0
for name in criaturas_names:
    count += Card.objects.filter(name__iexact=name, edition__slug=ed, race=noraza).update(race=criaturas)
    count += Card.objects.filter(name__istartswith=name, edition__slug=ed, race=noraza, card_type__name='Aliado').update(race=criaturas)
print(f"Criaturas: {count}")

# Campeón: Yagyu Jubei, Zhao Yun
campeon_names = ['Yagyu Jubei', 'yangyu jubei', 'Zhao Yun']
count = 0
for name in campeon_names:
    count += Card.objects.filter(name__iexact=name, edition__slug=ed, race=noraza).update(race=campeon)
    count += Card.objects.filter(name__istartswith=name, edition__slug=ed, race=noraza, card_type__name='Aliado').update(race=campeon)
print(f"Campeón: {count}")

# Oro: Calabaza del Inmortal
count = Card.objects.filter(name__icontains='calabaza', edition__slug=ed, card_type__name='Aliado').update(card_type=oro, race=noraza)
print(f"Oro (Calabaza): {count}")

# Arma: Qiang
count = Card.objects.filter(name__icontains='qiang', edition__slug=ed, card_type__name='Aliado').update(card_type=arma, race=noraza)
# Excluir Qianlima que ya es Criaturas
count = Card.objects.filter(name__iexact='Qiang', edition__slug=ed, card_type__name='Aliado').update(card_type=arma, race=noraza)
count += Card.objects.filter(name__iexact='qiang', edition__slug=ed, card_type__name='Aliado').update(card_type=arma, race=noraza)
count += Card.objects.filter(name__istartswith='Qiang ', edition__slug=ed, card_type__name='Aliado').update(card_type=arma, race=noraza)
print(f"Arma (Qiang): {count}")

# Verificar restantes
remaining = Card.objects.filter(edition__slug=ed, card_type__name='Aliado', race=noraza)
print(f"\nAliados Sin Raza restantes en espiritu-de-dragon: {remaining.count()}")
for c in remaining:
    print(f"  {c.name} | myl={c.myl_id}")
