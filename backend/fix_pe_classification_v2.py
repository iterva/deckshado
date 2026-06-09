"""
Script consolidado para aplicar TODAS las correcciones de clasificación PE en producción.
Ejecutar en PythonAnywhere después de git pull.
"""
import django, os, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'backend.settings'
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from cards.models import Card, Race, CardType

# Obtener tipos y razas
noraza = Race.objects.get(slug='noraza')
talisman = CardType.objects.get(name='Talismán')
totem = CardType.objects.get(name='Tótem')
arma = CardType.objects.get(name='Arma')
oro = CardType.objects.get(name='Oro')

print("=== Correcciones PE v2 ===\n")

# ============================================================
# MUNDO GÓTICO
# ============================================================
print("--- MUNDO GÓTICO ---")
ed = 'mundo-gotico'

# Vampiro
vampiro = Race.objects.get(slug='vampiro')
vamp_ids = ['pe_0407', 'pe_1737', 'pe_0412', 'pe_1738', 'pe_0425', 'pe_1739']
c = Card.objects.filter(myl_id__in=vamp_ids).update(race=vampiro)
print(f"  Vampiro (Golem Sombrío, Jacques, Mercy Brown): {c}")

# Licántropo
licantropo = Race.objects.get(slug='licantropo')
lican_names = ['Abominación', 'Abominacion', 'Wechuge', 'Yee Naaldlooshii', 'Coyote Rojo', 'Coyoto Rojo']
c = 0
for name in lican_names:
    c += Card.objects.filter(name__iexact=name, edition__slug=ed, card_type__name='Aliado').update(race=licantropo)
    c += Card.objects.filter(name__istartswith=name, edition__slug=ed, card_type__name='Aliado', race=noraza).update(race=licantropo)
print(f"  Licántropo (Abominación, Wechuge, Yee, Coyote): {c}")

# Talismán
tal_names = ['Eclipse de Dragón', 'eclipse de dragon', 'Justos por Pecadores', 'justos por pecadores',
             'Purificar Sombras', 'purificar sombras', 'Repulsion', 'repulsion']
c = 0
for name in tal_names:
    c += Card.objects.filter(name__iexact=name, edition__slug=ed, card_type__name='Aliado').update(card_type=talisman, race=noraza)
    c += Card.objects.filter(name__istartswith=name, edition__slug=ed, card_type__name='Aliado').update(card_type=talisman, race=noraza)
print(f"  Talismán: {c}")

# Arma
c = Card.objects.filter(name__icontains='kris de plata', edition__slug=ed, card_type__name='Aliado').update(card_type=arma, race=noraza)
print(f"  Arma (Kris de Plata): {c}")

# Oro
c = Card.objects.filter(name__icontains='reliquia del leon', edition__slug=ed, card_type__name='Aliado').update(card_type=oro, race=noraza)
print(f"  Oro (Reliquia del León): {c}")

# Tótem
totem_names = ['Torre de leon', 'torre de leon', 'Totem Ultimo', 'Totem ultimo']
c = 0
for name in totem_names:
    c += Card.objects.filter(name__iexact=name, edition__slug=ed, card_type__name='Aliado').update(card_type=totem, race=noraza)
    c += Card.objects.filter(name__istartswith=name, edition__slug=ed, card_type__name='Aliado').update(card_type=totem, race=noraza)
print(f"  Tótem (Torre/Tótem Último): {c}")

# ============================================================
# EL RETO
# ============================================================
print("\n--- EL RETO ---")
ed = 'el-reto'
dragon = Race.objects.get(slug='dragon')
faerie = Race.objects.get(slug='faerie')
caballero = Race.objects.get(slug='caballero')

# Dragón
c = Card.objects.filter(name__icontains='zduhac', edition__slug=ed, card_type__name='Aliado', race=noraza).update(race=dragon)
c += Card.objects.filter(name__icontains='tentevilu', edition__slug=ed, card_type__name='Aliado', race=noraza).update(race=dragon)
c += Card.objects.filter(name__icontains='tentenvilu', edition__slug=ed, card_type__name='Aliado', race=noraza).update(race=dragon)
print(f"  Dragón (Zduhac, Tentevilu): {c}")

# Faerie
c = Card.objects.filter(name__icontains='caballero verde', edition__slug=ed, card_type__name='Aliado', race=noraza).update(race=faerie)
c += Card.objects.filter(name__icontains='Caballero-Verde', edition__slug=ed, card_type__name='Aliado', race=noraza).update(race=faerie)
print(f"  Faerie (Caballero Verde): {c}")

# Caballero
c = Card.objects.filter(name__icontains='ishtar', edition__slug=ed, card_type__name='Aliado', race=noraza).update(race=caballero)
c += Card.objects.filter(name__icontains='isthar', edition__slug=ed, card_type__name='Aliado', race=noraza).update(race=caballero)
print(f"  Caballero (Ishtar): {c}")

# Oro
c = Card.objects.filter(name__icontains='nido', edition__slug=ed, card_type__name='Aliado').update(card_type=oro, race=noraza)
print(f"  Oro (Nido de Dragón): {c}")

# Arma
c = Card.objects.filter(name__icontains='montura', edition__slug=ed, card_type__name='Aliado').update(card_type=arma, race=noraza)
print(f"  Arma (Montura de Dragón): {c}")

# Talismán
tal_names = ['aliento congelante', 'apolo', 'bayard', 'bruja']
c = 0
for name in tal_names:
    c += Card.objects.filter(name__icontains=name, edition__slug=ed, card_type__name='Aliado').update(card_type=talisman, race=noraza)
print(f"  Talismán (Aliento/Apolo/Bayard/Bruja): {c}")

# Tótem
c = Card.objects.filter(name__icontains='bedd', edition__slug=ed, card_type__name='Aliado').update(card_type=totem, race=noraza)
print(f"  Tótem (Bedd y Draig): {c}")

# ============================================================
# LA IRA DEL NAHUAL
# ============================================================
print("\n--- LA IRA DEL NAHUAL ---")
ed = 'la-ira-del-nahual'
bestia = Race.objects.get(slug='bestia')
chaman = Race.objects.get(slug='chaman')
guerrero = Race.objects.get(slug='guerrero')

# Chamán
chaman_names = ['Ahayuta', 'Cuerno Rojo', 'Espiritu Gaan', 'Hombre de piedra', 'Inti', 'Inti_ixnb1i']
c = 0
for name in chaman_names:
    c += Card.objects.filter(name__iexact=name, edition__slug=ed, card_type__name='Aliado', race=noraza).update(race=chaman)
    c += Card.objects.filter(name__istartswith=name, edition__slug=ed, card_type__name='Aliado', race=noraza).update(race=chaman)
print(f"  Chamán: {c}")

# Bestia
bestia_names = ['Cortadora', 'Muut', 'Piasa', 'Sasnalkahi', 'Skoyo', 'Snallygaster']
c = 0
for name in bestia_names:
    c += Card.objects.filter(name__iexact=name, edition__slug=ed, card_type__name='Aliado', race=noraza).update(race=bestia)
    c += Card.objects.filter(name__istartswith=name, edition__slug=ed, card_type__name='Aliado', race=noraza).update(race=bestia)
print(f"  Bestia: {c}")

# Guerrero
c = Card.objects.filter(name__icontains='toki butahue', edition__slug=ed, card_type__name='Aliado', race=noraza).update(race=guerrero)
print(f"  Guerrero (Toki Butahue): {c}")

# Talismán
tal_names = ['Ah Puch', 'ahpuch', 'Ataque relampago', "K' Ak' Na", 'KAkNa', 'Rastrear']
c = 0
for name in tal_names:
    c += Card.objects.filter(name__iexact=name, edition__slug=ed, card_type__name='Aliado').update(card_type=talisman, race=noraza)
    c += Card.objects.filter(name__istartswith=name, edition__slug=ed, card_type__name='Aliado').update(card_type=talisman, race=noraza)
print(f"  Talismán: {c}")

# Tótem
c = Card.objects.filter(name__icontains='uxmal', edition__slug=ed, card_type__name='Aliado').update(card_type=totem, race=noraza)
print(f"  Tótem (Uxmal): {c}")

# ============================================================
# RAGNAROK
# ============================================================
print("\n--- RAGNAROK ---")
ed = 'ragnarok'

# Tótem
totem_names = ['altar de odin', 'Altar de Odin', 'gothiscandza', 'Gothiscandza',
               'midgard', 'Midgard', 'vinland', 'Vinland']
c = 0
for name in totem_names:
    c += Card.objects.filter(name__iexact=name, edition__slug=ed, card_type__name='Aliado').update(card_type=totem, race=noraza)
    c += Card.objects.filter(name__istartswith=name, edition__slug=ed, card_type__name='Aliado').update(card_type=totem, race=noraza)
print(f"  Tótem: {c}")

# Arma
c = Card.objects.filter(name__icontains='escudo', edition__slug=ed, card_type__name='Aliado').update(card_type=arma, race=noraza)
print(f"  Arma (Escudo): {c}")

# Talismán
c = Card.objects.filter(name__icontains='mordida abismal', edition__slug=ed, card_type__name='Aliado').update(card_type=talisman, race=noraza)
print(f"  Talismán (Mordida Abismal): {c}")

# Oro
c = Card.objects.filter(name__icontains='tesoro de troll', edition__slug=ed, card_type__name='Aliado').update(card_type=oro, race=noraza)
print(f"  Oro (Tesoro de Troll): {c}")

# ============================================================
# ESPÍRITU DE DRAGÓN
# ============================================================
print("\n--- ESPÍRITU DE DRAGÓN ---")
ed = 'espiritu-de-dragon'
kami = Race.objects.get(slug='kami')
xian = Race.objects.get(slug='xian')
criaturas = Race.objects.get(slug='criaturas')
campeon = Race.objects.get(slug='campeon')

# Kami
kami_names = ['Ama No Fuchigoma', 'Gozu Tenno', 'Konpira Gongen', 'Ninigi No Mikoto']
c = 0
for name in kami_names:
    c += Card.objects.filter(name__iexact=name, edition__slug=ed, card_type__name='Aliado', race=noraza).update(race=kami)
    c += Card.objects.filter(name__istartswith=name, edition__slug=ed, card_type__name='Aliado', race=noraza).update(race=kami)
print(f"  Kami: {c}")

# Xian
xian_names = ['Cabeza de Buey', 'Cara de Caballo', 'Han Xiang Zi', 'Meng Po']
c = 0
for name in xian_names:
    c += Card.objects.filter(name__iexact=name, edition__slug=ed, card_type__name='Aliado', race=noraza).update(race=xian)
    c += Card.objects.filter(name__istartswith=name, edition__slug=ed, card_type__name='Aliado', race=noraza).update(race=xian)
print(f"  Xian: {c}")

# Criaturas
criaturas_names = ['Longma', 'Qianlima', 'Shachihoko', 'Tianma']
c = 0
for name in criaturas_names:
    c += Card.objects.filter(name__iexact=name, edition__slug=ed, card_type__name='Aliado', race=noraza).update(race=criaturas)
    c += Card.objects.filter(name__istartswith=name, edition__slug=ed, card_type__name='Aliado', race=noraza).update(race=criaturas)
print(f"  Criaturas: {c}")

# Campeón
campeon_names = ['Yagyu Jubei', 'yangyu jubei', 'Zhao Yun']
c = 0
for name in campeon_names:
    c += Card.objects.filter(name__iexact=name, edition__slug=ed, card_type__name='Aliado', race=noraza).update(race=campeon)
    c += Card.objects.filter(name__istartswith=name, edition__slug=ed, card_type__name='Aliado', race=noraza).update(race=campeon)
print(f"  Campeón: {c}")

# Oro (Calabaza)
c = Card.objects.filter(name__icontains='calabaza', edition__slug=ed, card_type__name='Aliado').update(card_type=oro, race=noraza)
print(f"  Oro (Calabaza): {c}")

# Arma (Qiang - exacto, sin afectar Qianlima)
c = Card.objects.filter(name__iexact='Qiang', edition__slug=ed, card_type__name='Aliado').update(card_type=arma, race=noraza)
c += Card.objects.filter(name__iexact='qiang', edition__slug=ed, card_type__name='Aliado').update(card_type=arma, race=noraza)
print(f"  Arma (Qiang): {c}")

# ============================================================
# TODAS LAS NO-ALIADO → SIN RAZA
# ============================================================
print("\n--- TODAS NO-ALIADO → SIN RAZA ---")
pe_editions = ['el-reto', 'mundo-gotico', 'la-ira-del-nahual', 'ragnarok', 'espiritu-de-dragon']
total = 0
for ed in pe_editions:
    c = Card.objects.filter(
        edition__slug=ed
    ).exclude(card_type__name='Aliado').exclude(race=noraza).filter(race__isnull=False).update(race=noraza)
    if c:
        total += c
print(f"  Total no-Aliado con raza -> Sin Raza: {total}")

# ============================================================
# VERIFICACIÓN FINAL
# ============================================================
print("\n=== VERIFICACIÓN: Aliados Sin Raza por edición ===")
for ed in pe_editions:
    count = Card.objects.filter(edition__slug=ed, card_type__name='Aliado', race=noraza).count()
    print(f"  {ed}: {count} Aliados Sin Raza")
print("\nScript completado.")
