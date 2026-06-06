"""
Apply PE ability text extracted via OCR.
Reads pe_abilities.json (card_id -> ability_text mapping).

Usage on PythonAnywhere:
  cd ~/deckshado/backend
  python manage.py load_pe_abilities
"""
import json
import os
from django.core.management.base import BaseCommand
from cards.models import Card


class Command(BaseCommand):
    help = "Load PE ability text from pe_abilities.json"

    def handle(self, *args, **options):
        json_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'pe_abilities.json')
        json_path = os.path.abspath(json_path)

        if not os.path.exists(json_path):
            self.stderr.write(f"File not found: {json_path}")
            return

        with open(json_path, 'r', encoding='utf-8') as f:
            abilities = json.load(f)

        self.stdout.write(f"Loaded {len(abilities)} abilities from JSON")

        updated = 0
        for card_id, ability_text in abilities.items():
            rows = Card.objects.filter(id=int(card_id)).update(ability=ability_text)
            updated += rows

        self.stdout.write(self.style.SUCCESS(f"Updated {updated} cards with ability text"))
