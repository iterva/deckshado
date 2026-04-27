import requests
import re
from collections import defaultdict

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

base = "https://blog.myl.cl"

# Fetch ALL media - no date filter, paginate through everything
all_media = []

# Strategy 1: All media from 2026 (broad)
print("Fetching all media from WP API...")
page = 1
while page <= 100:
    url = f"{base}/wp-json/wp/v2/media?per_page=100&page={page}"
    resp = session.get(url, timeout=15)
    if resp.status_code != 200:
        break
    data = resp.json()
    if not data:
        break
    for item in data:
        all_media.append({
            'url': item.get('source_url', ''),
            'date': item.get('date', ''),
            'title': item.get('title', {}).get('rendered', ''),
        })
    total_pages = int(resp.headers.get('X-WP-TotalPages', 1))
    total_items = resp.headers.get('X-WP-Total', '?')
    print(f"  Page {page}/{total_pages} ({len(data)} items, total: {total_items})")
    if page >= total_pages:
        break
    page += 1

print(f"\nTotal media items: {len(all_media)}")

# Dedup
seen = set()
unique = []
for m in all_media:
    if m['url'] not in seen:
        seen.add(m['url'])
        unique.append(m)

print(f"Unique URLs: {len(unique)}")

# Group by pattern prefix
groups = defaultdict(list)
for m in unique:
    fname = m['url'].split('/')[-1]
    # Extract base pattern (remove number suffix and extension)
    # Try to identify the "family" name
    # Remove -1, -2 suffixes and .png/.jpg
    clean = re.sub(r'\.(png|jpg|jpeg|webp|gif)$', '', fname, flags=re.IGNORECASE)
    
    # Try common patterns
    # Pattern: name_NUMBER or name-NUMBER or nameNUMBER
    match = re.match(r'^(.+?)[-_]?\d+(?:-\d+)?$', clean)
    if match:
        prefix = match.group(1).rstrip('-_')
    else:
        prefix = clean
    
    groups[prefix].append(m)

# Sort groups by size
print(f"\n{'='*80}")
print(f"ALL PATTERN GROUPS ({len(groups)} groups)")
print(f"{'='*80}")

for prefix in sorted(groups.keys(), key=lambda k: (-len(groups[k]), k)):
    items = groups[prefix]
    if len(items) >= 2:  # Only show groups with 2+ files
        print(f"\n--- {prefix} ({len(items)} files) ---")
        for m in sorted(items, key=lambda x: x['url']):
            fname = m['url'].split('/')[-1]
            date = m['date'][:10] if m['date'] else ''
            print(f"  {fname:<55} {date}")

# Also show single files that look like cards/toolkits
print(f"\n{'='*80}")
print("SINGLE FILES (potential card patterns)")
print(f"{'='*80}")
for prefix in sorted(groups.keys()):
    items = groups[prefix]
    if len(items) == 1:
        fname = items[0]['url'].split('/')[-1]
        date = items[0]['date'][:10] if items[0]['date'] else ''
        # Only show if looks like it could be a card
        if any(kw in fname.lower() for kw in ['toolkit', 'carta', 'card', 'imperio', 'chile', 'oscuro', 'reprint', 'deck', 'myl', 'pack', 'mockup', 'lootbox']):
            print(f"  {fname:<55} {date}")
