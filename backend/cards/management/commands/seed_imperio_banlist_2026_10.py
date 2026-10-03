"""
Banlist Imperio completa a octubre 2026 (sincroniza sub-formatos racial y vcr).

Fuentes:
- https://blog.myl.cl/banlists-actualizadas/ (actualización 04/09/26):
  Shiji y Mariano Osorio pasan a limitadas a 1 copia; VCR sin cambios.
- "Lo prometido, lo corregido y lo que falta" (vigente desde el lunes 05/10/26):
  pasan a Única (1 copia) Jinete de la Peste, Duelo de Dragones, Espada de O'Higgins,
  Lilith, Kuchiku el Cazador y Escamas de Dragón. Acabar la Esperanza solo queda
  "en observación" (sin restricción).

La lista oficial es completa: las entradas imp/racial e imp/vcr que no aparecen se
eliminan (pasan a libres).

Uso:
  python manage.py seed_imperio_banlist_2026_10 --dry-run
  python manage.py seed_imperio_banlist_2026_10
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from cards.models import BanlistEntry

from .seed_imperio_banlist_2026_07_patch import _link_card, _normalize_key


FORMAT_CODE = "imp"
B, L1, L2 = BanlistEntry.BANNED, BanlistEntry.LIMITED_1, BanlistEntry.LIMITED_2
MAX_COPIES = {B: 0, L1: 1, L2: 2}

RACIAL = [
    # Escuadrón Mecha
    ("Tenshi X-2", B),
    # Bestiarium
    ("Perseguir el Sol", B),
    ("Paladín", L1),  # BES 017 - 161
    ("Rey de Amarillo", L1),
    ("Ryugu-Jo", L1),
    ("Sheut", L2),
    ("El Mago", L2),
    ("Ereshkigal", B),
    # Onyria
    ("Cthulhu", B),
    ("Hook", B),
    ("Septimus", B),
    ("Flechero", B),
    ("Sherlock Holmes", L2),
    ("El Rey y el Verdugo", L1),
    ("E.A. Poe", L1),
    ("Yelmo Mambrino", L1),
    ("Batallón de Ovejas", L1),
    ("León Indiferente", L1),
    # Libertadores
    ("San Bruno", B),
    ("Horda Tenebris", B),
    ("Creación de Temaukel", B),
    ("Cancha Rayada", B),
    ("Fusil Patriota", B),
    ("Manuel Bulnes", L1),
    ("Padre de la Patria", L1),
    ("Ramón Freire", L1),
    ("Mariano Osorio", L1),
    ("Legión Paladín", L1),
    ("Lucerna", L1),
    ("Levisterio", L1),
    ("Tesoro de los Césares", L1),
    ("Cueva de Xalpén", L1),
    # Kaiju vs Mecha: Titanes
    ("Liberar Esclavos", B),
    ("Akuma el Terrible", L1),
    ("Resistencia de Acero", B),
    ("Voragh el Devorador", L1),
    ("Azi Sruvara", L2),
    ("Nyssara Cautiva", L2),
    ("Crono Diamante", L1),
    ("Shiji", L1),
    # Ángeles y Demonios: Vigilantes
    ("Ángel Metatrón", L1),
    # Únicas desde el 05/10/26 (Kuchiku el Cazador antes estaba a 2 copias)
    ("Jinete de la Peste", L1),
    ("Duelo de Dragones", L1),
    ("Espada de O'Higgins", L1),
    ("Lilith", L1),
    ("Kuchiku el Cazador", L1),
    ("Escamas de Dragón", L1),
]

VCR = [
    # Set Inmortal
    ("Furia Berserker", B),
    ("Momificar", B),
    ("Escorpión de Seth", L1),
    # Bestiarium
    ("Alka", B),
    ("Libro de Thot", B),
    ("Ik'i B'alam", L1),
    ("Zmaj Depredador", L1),
    ("Laterna", L1),
    ("Azi Sruvara", L1),
    ("Ayyappan", L1),
    ("Ahriman", L1),
    ("Pirámide Roja", L1),
    # Onyria
    ("París", B),
    ("Forma de Niebla", B),
    ("Watson", L1),
    ("Gusano Blanco", L1),
    ("Prendick", L1),
    # Libertadores
    ("Sable Corto", B),
    ("Plaza de Armas", L1),
    ("Wayra Tata", L1),
    ("Monitor Araucano", L1),
    ("El Cuero", L1),
    ("Peripillán", L1),
    ("Capitán O'Brien", L1),
    ("La Lola", L1),
    ("Javiera Carrera", L1),
    ("Miguel Grau", L2),
    # Kaiju vs Mecha: Titanes
    ("Shedo Titán", B),
    ("Estela Sagrada", B),
    ("Invasión", B),
    ("Quantum Megumi", L1),
    ("Muro de los Caídos", L1),
    ("Lupus B7", L1),
    ("Misiles de Rastreo", L1),
    ("Tumulto Voraz", L1),
    ("Colaborador Titán", L1),
]

LISTS = {"racial": RACIAL, "vcr": VCR}


class Command(BaseCommand):
    help = "Sincroniza la banlist Imperio (racial + vcr) a octubre 2026"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Solo muestra cambios")

    def handle(self, *args, **options):
        dry_run = bool(options["dry_run"])
        tag = "DRY " if dry_run else ""
        totals = {"new": 0, "upd": 0, "del": 0, "keep": 0}

        with transaction.atomic():
            for sub_format, wanted in LISTS.items():
                self.stdout.write(self.style.MIGRATE_HEADING(f"\n{FORMAT_CODE}/{sub_format}"))
                existing = {
                    _normalize_key(e.card_name): e
                    for e in BanlistEntry.objects.filter(format_code=FORMAT_CODE, sub_format=sub_format)
                }
                wanted_keys = set()

                for card_name, status in wanted:
                    key = _normalize_key(card_name)
                    wanted_keys.add(key)
                    max_copies = MAX_COPIES[status]
                    entry = existing.get(key)

                    if entry is None:
                        totals["new"] += 1
                        self.stdout.write(f"  [{tag}NEW] {card_name} -> {status}")
                        if not dry_run:
                            BanlistEntry.objects.create(
                                card_name=card_name, format_code=FORMAT_CODE, sub_format=sub_format,
                                status=status, max_copies=max_copies, card=_link_card(card_name),
                            )
                        continue

                    changes = []
                    if entry.status != status or entry.max_copies != max_copies:
                        changes.append(f"{entry.status} -> {status}")
                        entry.status, entry.max_copies = status, max_copies
                    if entry.card_id is None:
                        linked = _link_card(card_name)
                        if linked is not None:
                            entry.card = linked
                            changes.append("card linked")
                    if changes:
                        totals["upd"] += 1
                        self.stdout.write(f"  [{tag}UPD] {entry.card_name}: {', '.join(changes)}")
                        if not dry_run:
                            entry.save(update_fields=["status", "max_copies", "card"])
                    else:
                        totals["keep"] += 1

                for key, entry in existing.items():
                    if key in wanted_keys:
                        continue
                    totals["del"] += 1
                    self.stdout.write(f"  [{tag}DEL] {entry.card_name} ({entry.status}) -> libre")
                    if not dry_run:
                        entry.delete()

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. Created={totals['new']} Updated={totals['upd']} "
            f"Deleted={totals['del']} Kept={totals['keep']}"
        ))
