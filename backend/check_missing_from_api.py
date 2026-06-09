"""Compare cards from riftcodex API vs local DB and find missing ones."""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

import requests, time, csv
from riftbound.models import RiftboundCard

# Fetch all cards from API
all_api_cards = []
page = 1
while True:
    resp = requests.get(f'https://api.riftcodex.com/cards?page={page}&size=50')
    data = resp.json()
    all_api_cards.extend(data['items'])
    print(f'  Pagina {page}/{data["pages"]} - {len(data["items"])} cartas')
    if page >= data['pages']:
        break
    page += 1
    time.sleep(0.3)

print(f'\nTotal cartas en API: {len(all_api_cards)}')

# Get all local card_numbers
local_ids = set(RiftboundCard.objects.values_list('card_number', flat=True))
print(f'Total cartas en DB local: {len(local_ids)}')

# API uses riftbound_id field - extract and normalize
missing = []
for card in all_api_cards:
    api_id = card['riftbound_id']  # e.g. 'unl-060a-219'
    parts = api_id.split('-')
    if len(parts) >= 3:
        # Format: set-number[suffix]-totalinset -> SET-number[suffix]
        normalized = f'{parts[0].upper()}-{parts[1]}'
    elif len(parts) == 2:
        normalized = f'{parts[0].upper()}-{parts[1]}'
    else:
        normalized = api_id.upper()

    # Also try with * suffix for signature cards
    sig_normalized = normalized + '*' if card.get('metadata', {}).get('signature') else None

    found = normalized in local_ids
    if sig_normalized and not found:
        found = sig_normalized in local_ids
    if not found:
        missing.append({
            'riftbound_id': api_id,
            'normalized': normalized,
            'name': card['name'],
            'set': card['set']['set_id'] if card.get('set') else 'N/A',
            'set_name': card['set']['label'] if card.get('set') else 'N/A',
            'type': card['classification']['type'] if card.get('classification') else '',
            'rarity': card['classification']['rarity'] if card.get('classification') else '',
            'image_url': card.get('media', {}).get('image_url', ''),
        })

print(f'\nCartas en API que NO estan en DB local: {len(missing)}')
print('---')

# Group by set
from collections import defaultdict
by_set = defaultdict(list)
for m in missing:
    by_set[m['set']].append(m)

for set_code in sorted(by_set.keys()):
    cards = sorted(by_set[set_code], key=lambda x: x['normalized'])
    print(f'\n=== {set_code} ({cards[0]["set_name"]}) - {len(cards)} faltantes ===')
    for m in cards:
        print(f"  {m['normalized']:12} | {m['name']:40} | {m['type']:8} | {m['rarity']}")

# Export to CSV
output_path = os.path.join(os.path.dirname(__file__), '..', 'riftbound_missing_cards.csv')
with open(output_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['set_code', 'set_name', 'card_id', 'api_riftbound_id', 'name', 'type', 'rarity', 'image_url'])
    for m in sorted(missing, key=lambda x: (x['set'], x['normalized'])):
        writer.writerow([m['set'], m['set_name'], m['normalized'], m['riftbound_id'], m['name'], m['type'], m['rarity'], m['image_url']])

print(f'\nCSV exportado: riftbound_missing_cards.csv')
