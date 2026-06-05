"""
Fix card_type for Primera Era cards by re-classifying from source URLs.

Uses both card_explorer_mapping.json and primera_era_mapping.json to build
a reverse lookup (cloudinary_url -> source_url), then applies classify_card
or infer_card_type_from_url logic.
"""
import json
import os
import re
from urllib.parse import unquote

from django.core.management.base import BaseCommand
from cards.models import Card, CardType, Edition

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)

PE_EDITION_IDS = [104, 105, 106, 107, 108]

TYPE_SLUGS = {
    "aliado": 1,
    "talisman": 2,
    "arma": 3,
    "totem": 4,
    "oro": 5,
}


def infer_type_from_source_url(url: str) -> int:
    """Infer card_type_id from the source URL path."""
    decoded = unquote(url).lower()

    # Support folder patterns (explicit type in path)
    if "/talismanes/" in decoded or "/talisman/" in decoded:
        return 2  # Talismán
    if "/armas/" in decoded:
        return 3  # Arma
    if "/tótems/" in decoded or "/totems/" in decoded or "/totem/" in decoded:
        return 4  # Tótem
    if "/oros/" in decoded or "/oro/" in decoded:
        return 5  # Oro

    # Race folders → Aliado
    if "/razas/" in decoded:
        return 1

    # Alt-art folders with type subfolders
    if re.search(r"artes\s*alternativos/.+?/(armas|arma)", decoded):
        return 3
    if re.search(r"artes\s*alternativos/.+?/(talismanes|talisman|talim)", decoded):
        return 2
    if re.search(r"artes\s*alternativos/.+?/(totems|totem)", decoded):
        return 4
    if re.search(r"artes\s*alternativos/.+?/(oros|oro)", decoded):
        return 5
    if re.search(r"artes\s*alternativos/.+?/(caballero|dragon|faerie|cazador|vampiro|licantropo|bestia|chaman|guerrero|abominaci|barbaro|dios|kami|xian|criaturas|campe)", decoded):
        return 1

    # Default: aliado (racial units, nuevas, faltantes without type info)
    return 1


class Command(BaseCommand):
    help = "Fix card_type_id for PE cards using source URL from mapping files"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Show changes without applying")
        parser.add_argument("--force-all", action="store_true",
                            help="Fix all types (default: only fix cards currently typed as Aliado)")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        force_all = options["force_all"]

        # Build cloudinary_url -> source_url reverse mapping
        cloud_to_source = {}

        # Load card_explorer_mapping
        explorer_path = os.path.join(PROJECT_ROOT, "card_explorer_mapping.json")
        if os.path.exists(explorer_path):
            with open(explorer_path, encoding="utf-8") as f:
                explorer_map = json.load(f)
            # Structure: {edition_slug: {card_name: {source_url, cloudinary_url}}}
            for edition_data in explorer_map.values():
                if isinstance(edition_data, dict):
                    # Could be nested (edition -> cards) or flat (card -> urls)
                    for val in edition_data.values():
                        if isinstance(val, dict) and "cloudinary_url" in val and "source_url" in val:
                            cloud_to_source[val["cloudinary_url"]] = val["source_url"]
                        elif isinstance(val, dict):
                            # Nested: edition -> {card_name: {urls}}
                            for card_data in val.values():
                                if isinstance(card_data, dict) and "cloudinary_url" in card_data:
                                    cloud_to_source[card_data["cloudinary_url"]] = card_data.get("source_url", "")
            self.stdout.write(f"Loaded {len(cloud_to_source)} entries from card_explorer_mapping.json")

        # Load primera_era_mapping
        pe_path = os.path.join(PROJECT_ROOT, "primera_era_mapping.json")
        if os.path.exists(pe_path):
            with open(pe_path, encoding="utf-8") as f:
                pe_map = json.load(f)
            count_before = len(cloud_to_source)
            for edition_data in pe_map.values():
                if isinstance(edition_data, dict):
                    for race_data in edition_data.values():
                        if isinstance(race_data, dict):
                            for card_data in race_data.values():
                                if isinstance(card_data, dict) and "cloudinary_url" in card_data:
                                    cloud_to_source[card_data["cloudinary_url"]] = card_data.get("source_url", "")
            self.stdout.write(f"Loaded {len(cloud_to_source) - count_before} entries from primera_era_mapping.json")

        self.stdout.write(f"Total reverse mappings: {len(cloud_to_source)}")

        # Process PE cards
        pe_cards = Card.objects.filter(edition_id__in=PE_EDITION_IDS)
        total = pe_cards.count()
        self.stdout.write(f"\nProcessing {total} PE cards...")

        fixed = 0
        not_found = 0
        already_correct = 0

        for card in pe_cards.iterator():
            image_url = card.custom_image_url or card.image or ""
            source_url = cloud_to_source.get(image_url, "")

            if not source_url:
                not_found += 1
                continue

            correct_type_id = infer_type_from_source_url(source_url)

            # By default, only upgrade Aliados to their correct type.
            # Don't downgrade cards that already have a specific type unless --force-all.
            if not force_all and card.card_type_id != 1 and correct_type_id == 1:
                already_correct += 1
                continue

            if card.card_type_id != correct_type_id:
                if not dry_run:
                    card.card_type_id = correct_type_id
                    card.save(update_fields=["card_type_id"])
                fixed += 1
                if fixed <= 20:
                    type_name = [k for k, v in TYPE_SLUGS.items() if v == correct_type_id][0]
                    self.stdout.write(
                        f"  {'[DRY] ' if dry_run else ''}Fixed: {card.name} → {type_name} (was type_id={card.card_type_id if dry_run else correct_type_id})"
                    )
            else:
                already_correct += 1

        action = "Would fix" if dry_run else "Fixed"
        self.stdout.write(self.style.SUCCESS(
            f"\nDone! {action}: {fixed}, Already correct: {already_correct}, "
            f"No mapping: {not_found}, Total: {total}"
        ))
