"""
Seed the Primera Era (Racial Edición) banlist — June 2026.

Source: https://blog.myl.cl/ban-list-primera-era-formato-racial-edicion/

Usage:
    python manage.py seed_pe_banlist            # apply
    python manage.py seed_pe_banlist --dry-run  # preview
"""
from django.core.management.base import BaseCommand
from cards.models import BanlistEntry, Card


FORMAT_CODE = "pe"
SUB_FORMAT = "racial_edicion"

# ──────────────────────────────────────────────────────────────────────────────
# BANNED (Prohibidas)
# ──────────────────────────────────────────────────────────────────────────────
BANNED = [
    # PE - El Reto
    ("Orejona", 14823),
    ("Oráculo de Delfos", 14822),
    ("Vishnu", 14859),
    ("Zeus", 16295),
    ("Walkirias", 14860),
    ("Shenlong", 14893),
    # PE - Mundo Gótico
    ("Salomé", 15157),
    ("Magnus", 15028),
    ("Ánima Negra", 14948),
    ("Ataque Suicida", 14953),
    ("Lucha de Golems", 15025),
    # PE - La Ira del Nahual
    ("Inti", 16749),
    ("Tsachila", 15437),
    ("Cuchivilu", 16690),
    ("Grifo", 15249),
    ("Tótem de Guanaco", 16870),
    ("Tótem de Jaguar", 16871),
    ("Kanillu", 15263),
    ("Trauko", 16720),
    ("Tesoro de Guayacán", 15320),
    ("Rito del Dorado", 15300),
    ("Cuero", 15236),
    ("Killa", 16810),
    # PE - Ragnarok
    ("Drakkar", 15468),
    ("Naglfar", 15535),
    ("Draupnir", 15470),
    ("Gyallarhorn", 15501),
    ("Cuernos de Adumla", 15467),
    # PE - Espíritu de Dragón
    ("Han Xiang Zi", 15991),
    ("Ken Nage", 15745),
    ("Niten Ichi Ryu", 15790),
    ("Bushido", 15670),
    ("Yingzhao Chuan-Fa", 15866),
    ("Kayakujutsu", 15743),
    ("Dispositivo Espinoso", 15690),
    ("Dokuenjutsu", 15691),
    ("Tui", 15847),
    ("Li", 15757),
    ("Yoroi", 15868),
    ("Kabuto", 15734),
    ("Go", 15710),
    ("Sello Imperial de Jade", 15820),
    ("Shen Yi", 16015),
    ("Yasakani", 15863),
    ("47 Ronin", 17186),
]

# ──────────────────────────────────────────────────────────────────────────────
# LIMITED 1 (Limitadas a 1 copia)
# ──────────────────────────────────────────────────────────────────────────────
LIMITED_1 = [
    # PE - El Reto
    ("Grootslang", None),  # Not in PE editions in DB
    # PE - Mundo Gótico
    ("Manada Mortífera", 16664),
    ("Exorcista", 14997),
    ("Mosquete Puritano", 15038),
    ("Tótem del Bosque", 15090),
    ("Cazadores Implacables", 16651),
    # PE - La Ira del Nahual
    ("Machitún", 16917),
    ("Puchao", 15294),
    ("Sacrificio Humano", 15303),
    ("Flechero", 16897),
    ("Tótem de Serpiente", 16875),
    ("Puerta del Sol", 15295),
    ("Arco y Flechas", 15208),
    # PE - Ragnarok
    ("Ataúd de Marfil", 15453),
    ("Halatafl", 15503),
    ("Galdar", 17139),
    ("Arco de Ullr", 15448),
    ("Nott", 15597),
    # PE - Espíritu de Dragón
    ("Guan Yu", 17197),
    ("Kyudo", 15753),
    ("Saimin No Jutsu", 15814),
    ("Feng Shui", 15703),
    ("Teatro Kabuki", 15839),
    ("Dinastía Imperial", 17519),
    ("Niu Kanzhe Caodi", 15791),
    ("Zhang Guo Lao", 16027),
    ("Sakura", 15817),
    ("Monte del Buitre", 15780),
    ("Monte Wudang", 15782),
    ("Kun", 15749),
    ("Horóscopo Chino", 17522),
    ("Hwandudaedo", 15725),
    ("Yanhua", 15862),
    ("I Ching", 15727),
]

# ──────────────────────────────────────────────────────────────────────────────
# LIMITED 2 (Limitadas a 2 copias)
# ──────────────────────────────────────────────────────────────────────────────
LIMITED_2 = [
    # PE - El Reto
    ("Hades", 16235),
    ("Knochen", 14887),
    ("Kordrag", 14802),
    ("Quetzalcóatl", 14892),
    ("Persival", 16059),
    ("Caballo de Mar", 14904),
    ("Titania", 14939),
    ("Sir Gwain", 14848),
    # PE - Mundo Gótico
    ("Dycom el Recaudador", 16585),
    ("Niamh", 15039),
    ("Stribog", 16627),
    ("Zara", 15109),
    ("Enjambre", 16405),
    # PE - La Ira del Nahual
    ("Pihuchen", 16710),
    ("Sisiutl", 16718),
    ("Shuar", 15430),
    ("Bestias Furiosas", 16945),
    ("Tótem del Águila", 15334),
    ("Forma Voladora", 15248),
    # PE - Ragnarok
    ("Bjorn Ragnarsson", 15582),
    ("Horda Bárbara", 17174),
    ("Hidromiel", 15508),
    ("Fuerza Abominable", 17171),
    # PE - Espíritu de Dragón
    ("Fenghuang", 15887),
    ("Yoritomo", 15867),
    ("Changquan", 15676),
    ("Geon Si", 15892),
    ("Xi You Ji", 15853),
    ("Campeones de Oriente", 17516),
    ("Fu", 15888),
    ("Nodachi", 17400),
    ("Sai", 15813),
]


class Command(BaseCommand):
    help = "Seed Primera Era banlist — Racial Edición (June 2026)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Solo mostrar lo que se haría, sin escribir en la BD",
        )

    def _max_copies(self, status):
        return 0 if status == "banned" else (1 if status == "limited_1" else 2)

    def _build(self, status, items):
        out = []
        for name, cid in items:
            out.append({
                "card_name": name,
                "format_code": FORMAT_CODE,
                "sub_format": SUB_FORMAT,
                "status": status,
                "max_copies": self._max_copies(status),
                "card_id": cid,
            })
        return out

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        entries = []
        entries += self._build("banned", BANNED)
        entries += self._build("limited_1", LIMITED_1)
        entries += self._build("limited_2", LIMITED_2)

        # Validate referenced card IDs
        ids = {e["card_id"] for e in entries if e["card_id"] is not None}
        existing_ids = set(Card.objects.filter(id__in=ids).values_list("id", flat=True))
        missing = ids - existing_ids
        if missing:
            self.stdout.write(self.style.WARNING(
                f"⚠ Card IDs no encontrados: {sorted(missing)} — entradas sin enlace"
            ))

        created = 0
        updated = 0

        for e in entries:
            cid = e["card_id"]
            if cid is not None and cid not in existing_ids:
                cid = None

            action = "—"
            if not dry_run:
                obj, was_created = BanlistEntry.objects.update_or_create(
                    format_code=e["format_code"],
                    sub_format=e["sub_format"],
                    card_name=e["card_name"],
                    defaults={
                        "status": e["status"],
                        "max_copies": e["max_copies"],
                        "card_id": cid,
                    },
                )
                if was_created:
                    created += 1
                    action = "NEW"
                else:
                    updated += 1
                    action = "UPD"
            else:
                exists = BanlistEntry.objects.filter(
                    format_code=e["format_code"],
                    sub_format=e["sub_format"],
                    card_name=e["card_name"],
                ).first()
                action = "UPD" if exists else "NEW"

            link = "✓" if cid and cid in existing_ids else "⚠"
            self.stdout.write(
                f"  [{action}] [{e['status']:9}] "
                f"{e['card_name']} (max {e['max_copies']}) id={e['card_id']} {link}"
            )

        if dry_run:
            self.stdout.write(f"\n(dry-run) {len(entries)} entradas procesadas")
        else:
            self.stdout.write(self.style.SUCCESS(
                f"\n✅ PE banlist Racial Edición: {created} creadas, {updated} actualizadas"
            ))
