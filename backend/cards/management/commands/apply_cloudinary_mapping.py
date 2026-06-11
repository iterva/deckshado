"""
Aplica el mapping JSON generado por scripts de migración:
    python manage.py apply_cloudinary_mapping myl_cloudinary_mapping.json

Actualiza Card.custom_image_url con la URL CDN (Cloudinary/ImageKit),
solo si la carta no tiene custom_image_url ya seteado (no pisa overrides manuales).

Use --force para sobrescribir custom_image_url existentes.
"""
import json

from django.core.management.base import BaseCommand, CommandError

from cards.models import Card


class Command(BaseCommand):
    help = "Aplica un mapping myl_id -> CDN URL a Card.custom_image_url"

    def add_arguments(self, parser):
        parser.add_argument("mapping_file", type=str, help="Ruta al JSON de mapping")
        parser.add_argument("--force", action="store_true",
                            help="Sobrescribir custom_image_url existente")
        parser.add_argument("--dry-run", action="store_true",
                            help="No guardar cambios")

    def handle(self, *args, **opts):
        path = opts["mapping_file"]
        force = opts["force"]
        dry = opts["dry_run"]

        try:
            with open(path, "r", encoding="utf-8") as f:
                mapping = json.load(f)
        except FileNotFoundError:
            raise CommandError(f"No se encuentra {path}")

        self.stdout.write(f"Mapping cargado: {len(mapping)} entries")

        myl_ids = list(mapping.keys())
        # Process in batches to avoid huge IN queries
        batch_size = 500
        updated = 0
        skipped = 0
        not_found = 0

        for i in range(0, len(myl_ids), batch_size):
            batch = myl_ids[i:i + batch_size]
            cards = {c.myl_id: c for c in Card.objects.filter(myl_id__in=batch)}

            for myl_id in batch:
                url = mapping[myl_id]
                card = cards.get(myl_id)
                if not card:
                    not_found += 1
                    continue
                if card.custom_image_url and not force:
                    skipped += 1
                    continue
                card.custom_image_url = url
                if not dry:
                    card.save(update_fields=["custom_image_url"])
                updated += 1

        verb = "actualizar" if dry else "actualizadas"
        self.stdout.write(self.style.SUCCESS(
            f"{updated} {verb} | {skipped} skipped (ya tenian) | {not_found} no encontradas"
        ))
        if dry:
            self.stdout.write(self.style.WARNING("DRY RUN: nada se guardó"))
