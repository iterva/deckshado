"""
Seed cards from a local image folder.

Usage:
  python manage.py seed_from_folder "C:/path/to/folder" \
      --edition-slug heroes_de_dharma \
      --edition-title "ESC - Heroes de Dharma" \
      --format-code esc \
      --myl-id-prefix custom_heroes_dharma

Each image file becomes one card. The filename (minus extension) is used as
the card name. Images are copied to backend/media/extra_cards/ and served
via custom_image_url on PythonAnywhere.
"""
import os
import re
import shutil
import unicodedata

from django.conf import settings
from django.core.management.base import BaseCommand
from cards.models import Card, Edition, Format, Race, CardType, Rarity


MEDIA_BASE = "https://iterva.pythonanywhere.com/media/extra_cards"
EXTRA_CARDS_DIR = os.path.join(settings.BASE_DIR, "media", "extra_cards")
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def slugify_name(name: str) -> str:
    """Convert a card name to a slug: lowercase, accents stripped, spaces to hyphens."""
    nfkd = unicodedata.normalize("NFKD", name.lower())
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    slug = re.sub(r"[^a-z0-9]+", "-", stripped).strip("-")
    return slug


class Command(BaseCommand):
    help = "Seed cards from a folder of images"

    def add_arguments(self, parser):
        parser.add_argument("folder", help="Path to folder containing card images")
        parser.add_argument("--edition-slug", required=True, help="Slug for the edition")
        parser.add_argument("--edition-title", required=True, help="Display title for the edition")
        parser.add_argument("--format-code", default="esc", help="Format code (default: esc)")
        parser.add_argument("--myl-id-prefix", required=True, help="Prefix for myl_id (e.g. custom_heroes_dharma)")
        parser.add_argument("--rarity", default="promo", help="Rarity slug (default: promo)")

    def handle(self, *args, **options):
        folder = options["folder"]
        edition_slug = options["edition_slug"]
        edition_title = options["edition_title"]
        format_code = options["format_code"]
        myl_id_prefix = options["myl_id_prefix"]
        rarity_slug = options["rarity"]

        if not os.path.isdir(folder):
            self.stderr.write(f"Folder not found: {folder}")
            return

        # Ensure media/extra_cards/ exists
        os.makedirs(EXTRA_CARDS_DIR, exist_ok=True)

        # Get or create format and edition
        fmt = Format.objects.filter(code=format_code).first()
        if not fmt:
            self.stderr.write(f"Format '{format_code}' not found")
            return

        edition, created = Edition.objects.update_or_create(
            slug=edition_slug,
            defaults={
                "myl_id": f"custom_{edition_slug}",
                "title": edition_title,
                "format": fmt,
                "active": True,
            },
        )
        action = "Created" if created else "Updated"
        self.stdout.write(f"{action} edition: {edition.title}")

        rarity = Rarity.objects.filter(slug=rarity_slug).first()

        # List image files
        files = sorted([
            f for f in os.listdir(folder)
            if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS
        ])

        if not files:
            self.stderr.write(f"No image files found in {folder}")
            return

        self.stdout.write(f"Found {len(files)} images")

        created_count = 0
        updated_count = 0

        for idx, filename in enumerate(files, start=1):
            name_raw, ext = os.path.splitext(filename)
            # Clean up: replace underscores with spaces, strip leading numbers/prefixes
            card_name = name_raw.replace("_", " ").strip()
            # Remove trailing suffixes like _ESC, _Coleccionista
            card_name = re.sub(r"\s+(ESC|Coleccionista|SP|sp)$", "", card_name, flags=re.IGNORECASE)

            slug = slugify_name(card_name)
            edid = str(idx)
            myl_id = f"{myl_id_prefix}_{idx:03d}"

            # Copy image to media/extra_cards/ with a clean name
            dest_filename = f"{edition_slug}_{idx:03d}{ext.lower()}"
            src_path = os.path.join(folder, filename)
            dest_path = os.path.join(EXTRA_CARDS_DIR, dest_filename)
            shutil.copy2(src_path, dest_path)

            image_url = f"{MEDIA_BASE}/{dest_filename}"

            card, was_created = Card.objects.update_or_create(
                myl_id=myl_id,
                defaults={
                    "edid": edid,
                    "slug": f"{slug}-{edition_slug}",
                    "name": card_name,
                    "edition": edition,
                    "rarity": rarity,
                    "race": None,
                    "card_type": None,
                    "cost": None,
                    "damage": None,
                    "ability": None,
                    "flavour": None,
                    "custom_image_url": image_url,
                },
            )

            if was_created:
                created_count += 1
                self.stdout.write(f"  Created: {card.name} ({myl_id})")
            else:
                updated_count += 1
                self.stdout.write(f"  Updated: {card.name} ({myl_id})")

        self.stdout.write(self.style.SUCCESS(
            f"\nDone! Created: {created_count}, Updated: {updated_count}, Total: {len(files)}"
        ))
        self.stdout.write(f"Images copied to: {EXTRA_CARDS_DIR}")
        self.stdout.write(f"Remember to upload media/extra_cards/ to PythonAnywhere")
