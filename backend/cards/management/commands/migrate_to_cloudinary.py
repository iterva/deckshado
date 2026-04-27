"""
Management command: actualiza custom_image_url de PA local → Cloudinary.
Usa el archivo cloudinary_mapping.json del repo.
Uso: python manage.py migrate_to_cloudinary
"""
import json
import os
import re
from django.core.management.base import BaseCommand
from cards.models import Card


class Command(BaseCommand):
    help = "Reemplaza URLs de /media/extra_cards/ por URLs de Cloudinary usando cloudinary_mapping.json"

    def handle(self, *args, **options):
        mapping_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))),
            "cloudinary_mapping.json"
        )
        if not os.path.exists(mapping_path):
            self.stderr.write(f"No se encontró {mapping_path}")
            return

        with open(mapping_path) as f:
            data = json.load(f)

        extra = data.get("extra_cards", {})
        self.stdout.write(f"Mapping cargado: {len(extra)} imágenes")

        cards = Card.objects.filter(custom_image_url__icontains="/media/extra_cards/")
        self.stdout.write(f"Cartas a actualizar: {cards.count()}")

        updated = 0
        not_found = []
        for card in cards:
            url = card.custom_image_url or ""
            # Extraer filename limpio (sin ?v=1 etc)
            fname = re.sub(r'\?.*$', '', url.rsplit("/", 1)[-1])
            new_url = extra.get(fname)
            if new_url:
                card.custom_image_url = new_url
                card.save(update_fields=["custom_image_url"])
                updated += 1
                self.stdout.write(f"  ✓ {card.id} {card.name}: {fname} → Cloudinary")
            else:
                not_found.append(f"{card.id}: {fname}")
                self.stdout.write(f"  ✗ {card.id} {card.name}: {fname} NO ENCONTRADO")

        self.stdout.write(self.style.SUCCESS(f"\n{updated} cartas actualizadas."))
        if not_found:
            self.stdout.write(self.style.WARNING(f"{len(not_found)} no encontradas: {not_found}"))
