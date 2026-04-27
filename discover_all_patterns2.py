import requests
import re
from collections import defaultdict

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

base = "https://blog.myl.cl"

# Fetch ALL media
all_media = []
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
        })
    total_pages = int(resp.headers.get('X-WP-TotalPages', 1))
    total_items = resp.headers.get('X-WP-Total', '?')
    print(f"  Page {page}/{total_pages} (total: {total_items})")
    if page >= total_pages:
        break
    page += 1

# Dedup
seen = set()
unique = []
for m in all_media:
    if m['url'] not in seen:
        seen.add(m['url'])
        unique.append(m)

print(f"\nTotal unique: {len(unique)}")

# Now specifically search for toolkit patterns, chile-oscuro variations, and any numbered series
print(f"\n{'='*80}")
print("SERIES NUMERADAS (archivos con patron nombre+numero)")
print(f"{'='*80}")

# Better grouping: extract base name before numeric part
series = defaultdict(list)
for m in unique:
    fname = m['url'].split('/')[-1]
    # Match patterns like: Name_NNN, Name-NNN, NameNNN (where NNN is a number)
    # Also capture -1, -2 re-upload suffixes
    match = re.match(r'^(.+?)[-_]?(\d{2,3})(?:-\d+)?\.(?:png|jpg|jpeg|webp)$', fname, re.IGNORECASE)
    if match:
        base_name = match.group(1).rstrip('-_')
        num = match.group(2)
        series[base_name].append((int(num), fname, m['url'], m['date'][:10]))

# Show series with 3+ numbered files (likely card sets)
print("\nSeries with 3+ numbered files:\n")
for name in sorted(series.keys(), key=lambda k: (-len(series[k]), k)):
    items = series[name]
    if len(items) >= 3:
        nums = sorted(set(n for n, _, _, _ in items))
        print(f"  {name}")
        print(f"    Count: {len(items)} files, {len(nums)} unique numbers")
        print(f"    Numbers: {nums}")
        print(f"    Sample: {items[0][1]}")
        print()

# Now let's also search for specific additional patterns via API
print(f"\n{'='*80}")
print("BÚSQUEDA ESPECÍFICA DE PATRONES ADICIONALES")
print(f"{'='*80}")

search_terms = [
    "chile-oscuro",
    "Toolkit-26",
    "Toolkit-25",
    "IMP",
    "lootbox",
    "MOCKUP",
    "pack",
    "carta",
    "PB_",  # Pack Booster?
    "SD",   # Starter Deck?
]

for term in search_terms:
    results = []
    page = 1
    while page <= 10:
        url = f"{base}/wp-json/wp/v2/media?per_page=100&page={page}&search={term}"
        resp = session.get(url, timeout=15)
        if resp.status_code != 200:
            break
        data = resp.json()
        if not data:
            break
        for item in data:
            src = item.get('source_url', '')
            if src not in seen:
                results.append(src)
        total_pages = int(resp.headers.get('X-WP-TotalPages', 1))
        if page >= total_pages:
            break
        page += 1
    
    if results:
        print(f"\n  '{term}' - {len(results)} NEW files not in main listing:")
        for r in sorted(results)[:10]:
            print(f"    {r.split('/')[-1]}")
        if len(results) > 10:
            print(f"    ... and {len(results)-10} more")

# Also check: what other Toolkit-26 patterns exist?
print(f"\n{'='*80}")
print("TODOS LOS ARCHIVOS 'Toolkit-26' (cualquier variante)")
print(f"{'='*80}")

tk_results = []
page = 1
while page <= 10:
    url = f"{base}/wp-json/wp/v2/media?per_page=100&page={page}&search=Toolkit-26"
    resp = session.get(url, timeout=15)
    if resp.status_code != 200:
        break
    data = resp.json()
    if not data:
        break
    for item in data:
        tk_results.append({
            'url': item.get('source_url', ''),
            'date': item.get('date', '')[:10],
        })
    total_pages = int(resp.headers.get('X-WP-TotalPages', 1))
    if page >= total_pages:
        break
    page += 1

# Dedup
tk_seen = set()
tk_unique = []
for t in tk_results:
    if t['url'] not in tk_seen:
        tk_seen.add(t['url'])
        tk_unique.append(t)

for t in sorted(tk_unique, key=lambda x: x['url'].split('/')[-1]):
    print(f"  {t['url'].split('/')[-1]:<60} {t['date']}")

print(f"\nTotal Toolkit-26: {len(tk_unique)}")

# Check chile-oscuro variants (maybe chile-oscuro-1, chile-oscuro-3, etc.)
print(f"\n{'='*80}")
print("TODOS LOS ARCHIVOS 'chile-oscuro' (cualquier variante)")
print(f"{'='*80}")

co_results = []
page = 1
while page <= 10:
    url = f"{base}/wp-json/wp/v2/media?per_page=100&page={page}&search=chile-oscuro"
    resp = session.get(url, timeout=15)
    if resp.status_code != 200:
        break
    data = resp.json()
    if not data:
        break
    for item in data:
        co_results.append({
            'url': item.get('source_url', ''),
            'date': item.get('date', '')[:10],
        })
    total_pages = int(resp.headers.get('X-WP-TotalPages', 1))
    if page >= total_pages:
        break
    page += 1

co_seen = set()
co_unique = []
for c in co_results:
    if c['url'] not in co_seen:
        co_seen.add(c['url'])
        co_unique.append(c)

for c in sorted(co_unique, key=lambda x: x['url'].split('/')[-1]):
    print(f"  {c['url'].split('/')[-1]:<60} {c['date']}")

print(f"\nTotal chile-oscuro: {len(co_unique)}")

# Check "IMP" patterns (IMP1A, IMP2B etc - related to Imperio?)
print(f"\n{'='*80}")
print("ARCHIVOS 'IMP' (posibles cartas Imperio)")
print(f"{'='*80}")

imp_results = []
page = 1
while page <= 10:
    url = f"{base}/wp-json/wp/v2/media?per_page=100&page={page}&search=IMP"
    resp = session.get(url, timeout=15)
    if resp.status_code != 200:
        break
    data = resp.json()
    if not data:
        break
    for item in data:
        src = item.get('source_url', '')
        fname = src.split('/')[-1].lower()
        if 'imp' in fname:
            imp_results.append({
                'url': src,
                'date': item.get('date', '')[:10],
            })
    total_pages = int(resp.headers.get('X-WP-TotalPages', 1))
    if page >= total_pages:
        break
    page += 1

imp_seen = set()
for i in imp_results:
    if i['url'] not in imp_seen:
        imp_seen.add(i['url'])
        print(f"  {i['url'].split('/')[-1]:<60} {i['date']}")

# lootbox patterns
print(f"\n{'='*80}")
print("ARCHIVOS 'lootbox'")
print(f"{'='*80}")

lb_results = []
page = 1
while page <= 10:
    url = f"{base}/wp-json/wp/v2/media?per_page=100&page={page}&search=lootbox"
    resp = session.get(url, timeout=15)
    if resp.status_code != 200:
        break
    data = resp.json()
    if not data:
        break
    for item in data:
        lb_results.append({
            'url': item.get('source_url', ''),
            'date': item.get('date', '')[:10],
        })
    total_pages = int(resp.headers.get('X-WP-TotalPages', 1))
    if page >= total_pages:
        break
    page += 1

lb_seen = set()
for l in lb_results:
    if l['url'] not in lb_seen:
        lb_seen.add(l['url'])
        print(f"  {l['url'].split('/')[-1]:<60} {l['date']}")
