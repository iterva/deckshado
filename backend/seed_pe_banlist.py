"""
Seed BanlistEntry for Primera Era – Formato Racial Edición (Junio 2026).
Source: https://blog.myl.cl/ban-list-primera-era-formato-racial-edicion/

Usage:
    python manage.py shell < seed_pe_banlist.py
    # Or on PythonAnywhere:
    python manage.py shell < seed_pe_banlist.py
"""
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from cards.models import BanlistEntry

FORMAT = 'pe'
SUB_FORMAT = 'racial'

# ── Prohibidas (0 copias) ──────────────────────────────────────────────
BANNED = [
    # El Reto
    "Orejona", "Oráculo de Delfos", "Vishnu", "Zeus", "Walkirias", "Shenlong",
    # Mundo Gótico
    "Salome", "Magnus", "Anima Negra", "Ataque Suicida", "Lucha de Gólems",
    # La Ira del Nahual
    "Inti", "Tsachila", "Cuchivilu", "Grifo", "Tótem de Guanaco",
    "Tótem de Jaguar", "Kanillu", "Trauko", "Tesoro de Guayacán",
    "Rito del Dorado", "Cuero", "Killa",
    # Ragnarok
    "Drakkar", "Naglfar", "Draupnir", "Gyallarhorn", "Cuernos de Adumla",
    # Espíritu de Dragón
    "Han Xiang Zi", "Ken Nage", "Niten Ichi Ryu", "Bushido",
    "Yingzhao Chuan Fa", "Kayakujutsu", "Dispositivo Espinoso",
    "Dokuenjutsu", "Tui", "Li", "Yoroi", "Kabuto", "Go",
    "Sello Imperial de Jade", "Shen Yi", "Yasakani", "47 Ronin",
]

# ── Limitadas a 1 copia ───────────────────────────────────────────────
LIMITED_1 = [
    # El Reto
    "Grootslang",
    # Mundo Gótico
    "Manada Mortífera", "Exorcista", "Mosquete Puritano", "Tótem del Bosque",
    "Cazadores Implacables",
    # La Ira del Nahual
    "Machitún", "Puchao", "Sacrificio Humano", "Flechero",
    "Tótem de Serpiente", "Puerta del Sol", "Arco y Flechas",
    # Ragnarok
    "Ataúd de Marfil", "Halatafl", "Galdar", "Arco de Ullr", "Nott",
    # Espíritu de Dragón
    "Guan Yu", "Kyudo", "Saimin no Jutsu", "Feng Shui", "Teatro Kabuki",
    "Dinastía Imperial", "Niú Kánzhe Cáodí", "Zhang Guo La", "Sakura",
    "Monte del Buitre", "Monte Wudang", "Kun", "Horóscopo Chino",
    "Hwandudaedo", "Yanhua", "I Ching",
]

# ── Limitadas a 2 copias ──────────────────────────────────────────────
LIMITED_2 = [
    # El Reto
    "Hades", "Knochen", "Kordrag", "Quetzalcoátl", "Persival",
    "Caballo de Mar", "Titania", "Sir Gwain",
    # Mundo Gótico
    "Dycom el Recaudador", "Niamh", "Stribog", "Zara", "Enjambre",
    # La Ira del Nahual
    "Pihuchén", "Sisiutl", "Shuar", "Bestias Furiosas",
    "Tótem del Águila", "Forma Voladora",
    # Ragnarok
    "Bjorn Ragnarsson", "Horda Bárbara", "Hidromiel", "Fuerza Abominable",
    # Espíritu de Dragón
    "Fenghuang", "Yoritomo", "Changquan", "Geon Si", "Xi You Ji",
    "Campeones de Oriente", "Fu", "Nodachi", "Sai",
]


def seed():
    # Delete existing PE racial entries to avoid duplicates
    deleted, _ = BanlistEntry.objects.filter(format_code=FORMAT, sub_format=SUB_FORMAT).delete()
    if deleted:
        print(f"  Eliminadas {deleted} entradas anteriores de PE/racial.")

    entries = []
    for name in BANNED:
        entries.append(BanlistEntry(
            card_name=name, format_code=FORMAT, sub_format=SUB_FORMAT,
            status=BanlistEntry.BANNED, max_copies=0,
        ))
    for name in LIMITED_1:
        entries.append(BanlistEntry(
            card_name=name, format_code=FORMAT, sub_format=SUB_FORMAT,
            status=BanlistEntry.LIMITED_1, max_copies=1,
        ))
    for name in LIMITED_2:
        entries.append(BanlistEntry(
            card_name=name, format_code=FORMAT, sub_format=SUB_FORMAT,
            status=BanlistEntry.LIMITED_2, max_copies=2,
        ))

    BanlistEntry.objects.bulk_create(entries)
    print(f"  ✓ Creadas {len(entries)} entradas de banlist PE/racial:")
    print(f"    - Prohibidas: {len(BANNED)}")
    print(f"    - Limitadas a 1: {len(LIMITED_1)}")
    print(f"    - Limitadas a 2: {len(LIMITED_2)}")


seed()
