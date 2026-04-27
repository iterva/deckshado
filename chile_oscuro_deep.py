import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

base = "https://blog.myl.cl"

# 1. Search WP API with broader terms
print("=" * 80)
print("1. WP API: búsqueda 'chile'")
print("=" * 80)

for term in ["chile", "oscuro", "chile-oscuro-1", "chile-oscuro-3", "chile oscuro"]:
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
            if 'chile' in src.lower() or 'oscuro' in src.lower():
                results.append(src)
        total_pages = int(resp.headers.get('X-WP-TotalPages', 1))
        if page >= total_pages:
            break
        page += 1
    
    # Dedup
    unique = sorted(set(results))
    print(f"\n  '{term}' -> {len(unique)} files:")
    for r in unique:
        print(f"    {r.split('/')[-1]}")

# 2. Brute force: try chile-oscuro with ALL possible naming patterns
print("\n" + "=" * 80)
print("2. BRUTE FORCE: todas las variantes posibles de chile-oscuro")
print("=" * 80)

def check_url(url):
    try:
        resp = session.head(url, timeout=10, allow_redirects=True)
        return url, resp.status_code, resp.headers.get('Content-Type', ''), resp.headers.get('Content-Length', '0')
    except:
        return url, None, '', '0'

urls_to_check = []
base_url = "https://blog.myl.cl/wp-content/uploads/2026/03/"

# Variants of the base name
prefixes = [
    "chile-oscuro_",
    "chile-oscuro-",
    "chile-oscuro-1_",
    "chile-oscuro-2_",
    "chile-oscuro-3_",
    "chile-oscuro-1-",
    "chile-oscuro-2-",
    "chile-oscuro-3-",
    "chile_oscuro_",
    "chile_oscuro-",
    "chile_oscuro_2_",
    "Chile-Oscuro-2_",
    "Chile-oscuro-2_",
    "CHILE-OSCURO-2_",
    "chileoscuro",
    "chileoscuro2_",
    "chile-oscuro2_",
    "chile-oscuro-2_0",  # with leading zero before 2-digit
    "chile-oscuro-2_00", # with leading zeros
]

for prefix in prefixes:
    for i in range(0, 50):
        for fmt in [f"{i}", f"{i:02d}", f"{i:03d}"]:
            url = f"{base_url}{prefix}{fmt}.png"
            urls_to_check.append(url)
            # Also check -1, -2, -3 suffixes
            for suffix in ["-1", "-2", "-3"]:
                urls_to_check.append(f"{base_url}{prefix}{fmt}{suffix}.png")

# Also try other months/years
for year_month in ["2026/01", "2026/02", "2026/04", "2025/12", "2025/11"]:
    burl = f"https://blog.myl.cl/wp-content/uploads/{year_month}/"
    for i in range(0, 30):
        for fmt in [f"{i}", f"{i:02d}", f"{i:03d}"]:
            urls_to_check.append(f"{burl}chile-oscuro-2_{fmt}.png")
            urls_to_check.append(f"{burl}chile-oscuro-2_{fmt}-1.png")
            urls_to_check.append(f"{burl}chile-oscuro-2_{fmt}-2.png")

# Dedup
urls_to_check = list(set(urls_to_check))
print(f"\n  Checking {len(urls_to_check)} URLs...")

found = []
with ThreadPoolExecutor(max_workers=20) as executor:
    futures = {executor.submit(check_url, url): url for url in urls_to_check}
    for future in as_completed(futures):
        url, status, ctype, size = future.result()
        if status == 200 and 'image' in ctype.lower():
            found.append((url, size))

found.sort(key=lambda x: x[0])
print(f"\n  FOUND {len(found)} images:\n")

# Group by base path
from collections import defaultdict
by_month = defaultdict(list)
for url, size in found:
    parts = url.split('/uploads/')[1]
    month = '/'.join(parts.split('/')[:2])
    fname = parts.split('/')[-1]
    by_month[month].append((fname, size))

for month in sorted(by_month.keys()):
    print(f"  --- {month} ---")
    for fname, size in sorted(by_month[month]):
        print(f"    {fname:<50} ({size} bytes)")

# 3. Check if there are chile-oscuro-1 or chile-oscuro (without number) series
print("\n" + "=" * 80)
print("3. WP API: búsqueda variantes sin '2' (chile-oscuro-1, chile-oscuro)")
print("=" * 80)

for term in ["chile-oscuro-1", "chile oscuro 1", "chileoscuro"]:
    page = 1
    while page <= 5:
        url = f"{base}/wp-json/wp/v2/media?per_page=100&page={page}&search={term}"
        resp = session.get(url, timeout=15)
        if resp.status_code != 200:
            break
        data = resp.json()
        if not data:
            print(f"  '{term}' -> no results")
            break
        print(f"  '{term}' -> {len(data)} results:")
        for item in data:
            src = item.get('source_url', '')
            print(f"    {src.split('/')[-1]}")
        total_pages = int(resp.headers.get('X-WP-TotalPages', 1))
        if page >= total_pages:
            break
        page += 1

# 4. Check what the _0 and _021 files actually are (new ones not previously found)
print("\n" + "=" * 80)
print("4. Verificar archivos especiales (_0, _021)")
print("=" * 80)

special = [
    f"{base_url}chile-oscuro-2_0.png",
    f"{base_url}chile-oscuro-2_0-1.png",
    f"{base_url}chile-oscuro-2_021.png",
    f"{base_url}chile-oscuro-2_021-1.png",
    f"{base_url}chile-oscuro-2_022.png",
    f"{base_url}chile-oscuro-2_023.png",
    f"{base_url}chile-oscuro-2_024.png",
    f"{base_url}chile-oscuro-2_025.png",
    f"{base_url}chile-oscuro-2_02.png",
    f"{base_url}chile-oscuro-2_01.png",
    f"{base_url}chile-oscuro-2_04.png",
    f"{base_url}chile-oscuro-2_05.png",
    f"{base_url}chile-oscuro-2_08.png",
    f"{base_url}chile-oscuro-2_012.png",
    f"{base_url}chile-oscuro-2_014.png",
    f"{base_url}chile-oscuro-2_016.png",
]

for url in special:
    _, status, ctype, size = check_url(url)
    fname = url.split('/')[-1]
    if status == 200 and 'image' in ctype.lower():
        print(f"  [OK]     {fname}  ({size} bytes)")
    else:
        print(f"  [MISS]   {fname}  (status: {status})")
