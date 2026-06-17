from __future__ import annotations

import uuid

from django.db import migrations
from django.utils.text import slugify


def seed_sfp_r03b(apps, schema_editor):
    RiftboundCard = apps.get_model("riftbound", "RiftboundCard")
    RiftboundSet = apps.get_model("riftbound", "RiftboundSet")

    card_number = "SFP-R03b"
    name = "Mind Rune"
    external_id = uuid.UUID("a03b5fd0-0000-4000-8000-000000000003")

    rb_set, _ = RiftboundSet.objects.get_or_create(
        code="SFP",
        defaults={"name": "Spiritforged Promos"},
    )
    if rb_set.name != "Spiritforged Promos":
        rb_set.name = "Spiritforged Promos"
        rb_set.save(update_fields=["name"])

    payload = {
        "name": name,
        "slug": slugify(f"{name}-{card_number}"),
        "set": rb_set,
        "card_type": "rune",
        "supertype": "",
        "subtypes": [],
        "rarity": "showcase",
        "variant": "Alt Art",
        "colors": ["mind"],
        "energy": 0,
        "power": 0,
        "might": 0,
        "description": ".",
        "flavor": "",
        "image_url": "https://cmsassets.rgpub.io/sanity/images/dsfx7636/game_data_live/eb4559c507f09cabc3735973a1b20d83688d2f9d-744x1039.png",
        "image_url_small": "",
        "cdn_image_url": "",
        "source_url": "https://piltoverarchive.com/cards?page=15",
        "is_active": True,
    }

    card = RiftboundCard.objects.filter(external_id=external_id).first()
    if not card:
        card = RiftboundCard.objects.filter(card_number=card_number).first()

    if card:
        card.card_number = card_number
        card.external_id = external_id
        for field, value in payload.items():
            setattr(card, field, value)
        card.save()
        return

    RiftboundCard.objects.create(
        card_number=card_number,
        external_id=external_id,
        **payload,
    )


def noop_reverse(apps, schema_editor):
    # Keep seeded card on rollback to avoid accidental catalog loss.
    return


class Migration(migrations.Migration):

    dependencies = [
        ("riftbound", "0010_collectionentry_photos"),
    ]

    operations = [
        migrations.RunPython(seed_sfp_r03b, noop_reverse),
    ]
