"""
Safe card data import that preserves existing decks.
Unlike `loaddata`, this command updates cards individually without
triggering CASCADE deletes on DeckEntry references.
"""
import json
from django.core.management.base import BaseCommand
from django.db import transaction
from cards.models import Card, Edition, Format, Race, CardType, Rarity, Keyword, BanlistEntry


MODEL_MAP = {
    "cards.format": Format,
    "cards.edition": Edition,
    "cards.race": Race,
    "cards.cardtype": CardType,
    "cards.rarity": Rarity,
    "cards.keyword": Keyword,
    "cards.card": Card,
    "cards.banlistentry": BanlistEntry,
}

# Fields that are ForeignKey references (field_name -> model)
FK_FIELDS = {
    "cards.edition": {"format": Format},
    "cards.card": {
        "edition": Edition,
        "rarity": Rarity,
        "race": Race,
        "card_type": CardType,
    },
    "cards.banlistentry": {
        "card": Card,
    },
}

# M2M fields
M2M_FIELDS = {
    "cards.card": ["keywords"],
}


class Command(BaseCommand):
    help = "Safely import cards_data.json without deleting deck entries"

    def add_arguments(self, parser):
        parser.add_argument("fixture", help="Path to the JSON fixture file")

    def handle(self, *args, **options):
        fixture_path = options["fixture"]

        with open(fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Group by model, preserving order
        grouped = {}
        for obj in data:
            model_label = obj["model"]
            grouped.setdefault(model_label, []).append(obj)

        # Process in dependency order
        order = [
            "cards.format",
            "cards.race",
            "cards.cardtype",
            "cards.rarity",
            "cards.keyword",
            "cards.edition",
            "cards.card",
            "cards.banlistentry",
        ]

        stats = {"created": 0, "updated": 0, "skipped": 0}

        with transaction.atomic():
            for model_label in order:
                objects = grouped.get(model_label, [])
                if not objects:
                    continue

                Model = MODEL_MAP.get(model_label)
                if not Model:
                    self.stdout.write(f"  Skipping unknown model: {model_label}")
                    continue

                fk_map = FK_FIELDS.get(model_label, {})
                m2m_list = M2M_FIELDS.get(model_label, [])

                self.stdout.write(f"Processing {model_label}: {len(objects)} objects...")

                for obj in objects:
                    pk = obj["pk"]
                    fields = dict(obj["fields"])

                    # Separate M2M fields
                    m2m_data = {}
                    for m2m_field in m2m_list:
                        if m2m_field in fields:
                            m2m_data[m2m_field] = fields.pop(m2m_field)

                    # Resolve FK references
                    for field_name, RelatedModel in fk_map.items():
                        val = fields.get(field_name)
                        if val is not None:
                            fields[f"{field_name}_id"] = val
                        else:
                            fields[f"{field_name}_id"] = None
                        fields.pop(field_name, None)

                    # Try update existing, or create new
                    try:
                        existing = Model.objects.filter(pk=pk).first()
                        if existing:
                            for k, v in fields.items():
                                setattr(existing, k, v)
                            existing.save()
                            stats["updated"] += 1
                        else:
                            instance = Model(pk=pk, **fields)
                            instance.save()
                            stats["created"] += 1

                        # Handle M2M
                        if m2m_data:
                            instance = Model.objects.get(pk=pk)
                            for m2m_field, ids in m2m_data.items():
                                getattr(instance, m2m_field).set(ids)

                    except Exception as e:
                        self.stderr.write(f"  Error on {model_label} pk={pk}: {e}")
                        stats["skipped"] += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nDone! Created: {stats['created']}, Updated: {stats['updated']}, Skipped: {stats['skipped']}"
        ))
