import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

base = "https://blog.myl.cl"

# Fetch ALL media from March 2026 via WP REST API
all_media = []
page = 1
while page <= 50:
    url = f"{base}/wp-json/wp/v2/media?per_page=100&page={page}&after=2026-02-28T23:59:59&before=2026-04-01T00:00:00"
    resp = session.get(url, timeout=15)
    if resp.status_code != 200:
        break
    data = resp.json()
    if not data:
        break
    for item in data:
        all_media.append({
            'url': item.get('source_url', ''),
            'title': item.get('title', {}).get('rendered', ''),
            'date': item.get('date', ''),
            'mime': item.get('mime_type', ''),
        })
    total_pages = int(resp.headers.get('X-WP-TotalPages', 1))
    if page >= total_pages:
        break
    page += 1

# Also search specifically for "reprint" which appeared
page = 1
while page <= 5:
    url = f"{base}/wp-json/wp/v2/media?per_page=100&page={page}&search=Toolkit-26-Imperio-reprint"
    resp = session.get(url, timeout=15)
    if resp.status_code != 200:
        break
    data = resp.json()
    if not data:
        break
    for item in data:
        src = item.get('source_url', '')
        if src not in [m['url'] for m in all_media]:
            all_media.append({
                'url': src,
                'title': item.get('title', {}).get('rendered', ''),
                'date': item.get('date', ''),
                'mime': item.get('mime_type', ''),
            })
    total_pages = int(resp.headers.get('X-WP-TotalPages', 1))
    if page >= total_pages:
        break
    page += 1

# Categorize
chile = []
imperio = []
imperio_reprint = []
other = []

for m in all_media:
    fname = m['url'].split('/')[-1]
    if 'chile-oscuro' in fname.lower():
        chile.append(m)
    elif 'toolkit-26-imperio-reprint' in fname.lower():
        imperio_reprint.append(m)
    elif 'toolkit-26-imperio' in fname.lower():
        imperio.append(m)

# Dedup by URL
def dedup(lst):
    seen = set()
    result = []
    for m in lst:
        if m['url'] not in seen:
            seen.add(m['url'])
            result.append(m)
    return sorted(result, key=lambda x: x['url'].split('/')[-1])

chile = dedup(chile)
imperio = dedup(imperio)
imperio_reprint = dedup(imperio_reprint)

# Print clean report
print("=" * 80)
print("LISTADO COMPLETO DE IMÁGENES - WordPress REST API")
print("=" * 80)

print(f"\n{'='*80}")
print(f"CHILE OSCURO 2 ({len(chile)} archivos)")
print(f"{'='*80}")
print(f"{'#':<4} {'Archivo':<45} {'Fecha':<20}")
print("-" * 80)
for i, m in enumerate(chile, 1):
    fname = m['url'].split('/')[-1]
    date = m['date'][:10] if m['date'] else ''
    print(f"{i:<4} {fname:<45} {date:<20}")

print(f"\n{'='*80}")
print(f"TOOLKIT-26-IMPERIO ({len(imperio)} archivos)")
print(f"{'='*80}")
print(f"{'#':<4} {'Archivo':<45} {'Fecha':<20}")
print("-" * 80)
for i, m in enumerate(imperio, 1):
    fname = m['url'].split('/')[-1]
    date = m['date'][:10] if m['date'] else ''
    print(f"{i:<4} {fname:<45} {date:<20}")

if imperio_reprint:
    print(f"\n{'='*80}")
    print(f"TOOLKIT-26-IMPERIO-REPRINT ({len(imperio_reprint)} archivos)")
    print(f"{'='*80}")
    print(f"{'#':<4} {'Archivo':<45} {'Fecha':<20}")
    print("-" * 80)
    for i, m in enumerate(imperio_reprint, 1):
        fname = m['url'].split('/')[-1]
        date = m['date'][:10] if m['date'] else ''
        print(f"{i:<4} {fname:<45} {date:<20}")

# Identify which are originals vs re-uploads (-1, -2 suffixes)
print(f"\n{'='*80}")
print("ANÁLISIS DE DUPLICADOS / RE-UPLOADS")
print(f"{'='*80}")

import re

print("\n--- Chile Oscuro: versiones con sufijo (-1, -2) ---")
for m in chile:
    fname = m['url'].split('/')[-1]
    if re.search(r'-\d+\.png$', fname) and not re.search(r'_\d+-\d+\.png$', fname) is None:
        pass
    # Better approach: identify base name
    match = re.match(r'(chile-oscuro-2_\d+)(-\d+)?\.png', fname)
    if match and match.group(2):
        print(f"  {fname} <- re-upload of {match.group(1)}.png")

print("\n--- Imperio: versiones con sufijo (-1, -2) ---")
for m in imperio:
    fname = m['url'].split('/')[-1]
    match = re.match(r'(Toolkit-26-Imperio\d+)(-\d+)?\.png', fname)
    if match and match.group(2):
        print(f"  {fname} <- re-upload of {match.group(1)}.png")

# Summary: unique card numbers
print(f"\n{'='*80}")
print("RESUMEN: NÚMEROS DE CARTA ÚNICOS")
print(f"{'='*80}")

chile_nums = set()
for m in chile:
    fname = m['url'].split('/')[-1]
    match = re.search(r'chile-oscuro-2_(\d+)', fname)
    if match:
        chile_nums.add(int(match.group(1)))

imperio_nums = set()
for m in imperio:
    fname = m['url'].split('/')[-1]
    match = re.search(r'Toolkit-26-Imperio(\d+)', fname)
    if match:
        imperio_nums.add(int(match.group(1)))

reprint_nums = set()
for m in imperio_reprint:
    fname = m['url'].split('/')[-1]
    match = re.search(r'reprint_(\d+)', fname)
    if match:
        reprint_nums.add(int(match.group(1)))

print(f"\nChile Oscuro - {len(chile_nums)} cartas únicas: {sorted(chile_nums)}")
print(f"Imperio       - {len(imperio_nums)} cartas únicas: {sorted(imperio_nums)}")
print(f"Imp. Reprint  - {len(reprint_nums)} cartas únicas: {sorted(reprint_nums)}")

# Full URLs for reference
print(f"\n{'='*80}")
print("URLs COMPLETAS (para copiar)")
print(f"{'='*80}")
print("\n--- Chile Oscuro ---")
for m in chile:
    print(m['url'])
print("\n--- Imperio ---")
for m in imperio:
    print(m['url'])
if imperio_reprint:
    print("\n--- Imperio Reprint ---")
    for m in imperio_reprint:
        print(m['url'])
