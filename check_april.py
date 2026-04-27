import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

base = "https://blog.myl.cl"

# 1. WP API: all April 2026 media
print("=" * 80)
print("WP API: TODO lo de abril 2026")
print("=" * 80)

april_media = []
page = 1
while page <= 20:
    url = f"{base}/wp-json/wp/v2/media?per_page=100&page={page}&after=2026-03-31T23:59:59&before=2026-05-01T00:00:00"
    resp = session.get(url, timeout=15)
    if resp.status_code != 200:
        break
    data = resp.json()
    if not data:
        break
    for item in data:
        april_media.append({
            'url': item.get('source_url', ''),
            'date': item.get('date', '')[:10],
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
for m in april_media:
    if m['url'] not in seen:
        seen.add(m['url'])
        unique.append(m)

print(f"\nTotal abril 2026: {len(unique)} archivos únicos")

# Filter toolkit and chile-oscuro
toolkit_apr = [m for m in unique if 'toolkit' in m['url'].lower() or 'imperio' in m['url'].lower()]
chile_apr = [m for m in unique if 'chile' in m['url'].lower() or 'oscuro' in m['url'].lower()]

print(f"\n--- Toolkit/Imperio en abril ({len(toolkit_apr)}) ---")
for m in sorted(toolkit_apr, key=lambda x: x['url']):
    print(f"  {m['url'].split('/')[-1]:<55} {m['date']}")

print(f"\n--- Chile-oscuro en abril ({len(chile_apr)}) ---")
for m in sorted(chile_apr, key=lambda x: x['url']):
    print(f"  {m['url'].split('/')[-1]:<55} {m['date']}")

# 2. Brute force avril: check all Imperio numbers 1-50 in 2026/04/
print(f"\n{'='*80}")
print("BRUTE FORCE: Toolkit-26-Imperio en 2026/04/")
print(f"{'='*80}")

def check_url(url):
    try:
        resp = session.head(url, timeout=10, allow_redirects=True)
        return url, resp.status_code, resp.headers.get('Content-Type', ''), resp.headers.get('Content-Length', '0')
    except:
        return url, None, '', '0'

urls = []
apr_base = "https://blog.myl.cl/wp-content/uploads/2026/04/"
for i in range(0, 50):
    for fmt in [f"{i}", f"{i:02d}", f"{i:03d}"]:
        urls.append(f"{apr_base}Toolkit-26-Imperio{fmt}.png")
        for suffix in ["-1", "-2", "-3"]:
            urls.append(f"{apr_base}Toolkit-26-Imperio{fmt}{suffix}.png")
# Also chile-oscuro in april
for i in range(0, 50):
    for fmt in [f"{i}", f"{i:02d}", f"{i:03d}"]:
        urls.append(f"{apr_base}chile-oscuro-2_{fmt}.png")
        for suffix in ["-1", "-2", "-3"]:
            urls.append(f"{apr_base}chile-oscuro-2_{fmt}{suffix}.png")
# Also reprint
for i in range(0, 20):
    for fmt in [f"{i}", f"{i:02d}"]:
        urls.append(f"{apr_base}Toolkit-26-Imperio-reprint_{fmt}.png")
        urls.append(f"{apr_base}Toolkit-26-Imperio-reprint_{fmt}-1.png")

urls = list(set(urls))
print(f"  Checking {len(urls)} URLs...")

found = []
with ThreadPoolExecutor(max_workers=20) as executor:
    futures = {executor.submit(check_url, url): url for url in urls}
    for future in as_completed(futures):
        url, status, ctype, size = future.result()
        if status == 200 and 'image' in ctype.lower():
            found.append((url.split('/')[-1], url, size))

print(f"\n  FOUND {len(found)} images in 2026/04/:\n")
for fname, url, size in sorted(found):
    print(f"  {fname:<55} ({size} bytes)")

# 3. Check what we already have vs what's new
out_dir = os.path.join(os.path.dirname(__file__), "cartas-blog")
existing = set(os.listdir(out_dir)) if os.path.exists(out_dir) else set()

new_files = [(fname, url, size) for fname, url, size in found if fname not in existing]
print(f"\n--- NUEVOS (no descargados aún): {len(new_files)} ---")
for fname, url, size in sorted(new_files):
    print(f"  {fname}")

# 4. Download missing ones
if new_files:
    print(f"\nDescargando {len(new_files)} archivos nuevos...")
    for fname, url, size in sorted(new_files):
        try:
            r = session.get(url, timeout=30)
            if r.status_code == 200:
                path = os.path.join(out_dir, fname)
                with open(path, 'wb') as f:
                    f.write(r.content)
                print(f"  [OK] {fname} ({len(r.content)//1024} KB)")
        except Exception as e:
            print(f"  [ERR] {fname}: {e}")

print("\nDone!")
