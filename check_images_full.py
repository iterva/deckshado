import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

def check_url(url):
    try:
        resp = requests.head(url, timeout=10, allow_redirects=True)
        return url, resp.status_code, resp.headers.get('Content-Type', ''), resp.headers.get('Content-Length', '0')
    except requests.RequestException as e:
        return url, None, '', str(e)

# Full check: chile-oscuro-2 with 2-digit (01-99) 
print("=" * 70)
print("chile-oscuro-2_XX.png (2 digits, 01 to 99)")
print("=" * 70)

urls = []
for i in range(1, 100):
    num = f"{i:02d}"
    urls.append(f"https://blog.myl.cl/wp-content/uploads/2026/03/chile-oscuro-2_{num}.png")

found = []
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(check_url, url): url for url in urls}
    results = []
    for future in as_completed(futures):
        results.append(future.result())

results.sort(key=lambda x: x[0])
for url, status, ctype, size in results:
    if status == 200 and 'image' in ctype.lower():
        name = url.split('/')[-1]
        found.append(name)
        print(f"  [OK]  {name} - ({size} bytes)")

print(f"\nTotal 2-digit: {len(found)}")

# Also check single digit without leading zero
print()
print("=" * 70)
print("chile-oscuro-2_X.png (single digit, 1 to 9)")
print("=" * 70)

urls = []
for i in range(1, 10):
    urls.append(f"https://blog.myl.cl/wp-content/uploads/2026/03/chile-oscuro-2_{i}.png")

with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(check_url, url): url for url in urls}
    results = []
    for future in as_completed(futures):
        results.append(future.result())

results.sort(key=lambda x: x[0])
for url, status, ctype, size in results:
    if status == 200 and 'image' in ctype.lower():
        name = url.split('/')[-1]
        print(f"  [OK]  {name} - ({size} bytes)")

# Also check Imperio with single digit 
print()
print("=" * 70)
print("Toolkit-26-ImperioX.png (single digit, 1 to 9)")
print("=" * 70)

urls = []
for i in range(1, 10):
    urls.append(f"https://blog.myl.cl/wp-content/uploads/2026/03/Toolkit-26-Imperio{i}.png")

with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(check_url, url): url for url in urls}
    results = []
    for future in as_completed(futures):
        results.append(future.result())

results.sort(key=lambda x: x[0])
for url, status, ctype, size in results:
    if status == 200 and 'image' in ctype.lower():
        name = url.split('/')[-1]
        print(f"  [OK]  {name} - ({size} bytes)")

# Combine ALL results into a final summary
print()
print("=" * 70)
print("FINAL CONSOLIDATED LIST")
print("=" * 70)

all_urls = []
base = "https://blog.myl.cl/wp-content/uploads/2026/03/"

# chile-oscuro: try 1-digit, 2-digit, 3-digit for 1-100
for i in range(1, 101):
    all_urls.append((f"chile-oscuro-2_{i}", f"{base}chile-oscuro-2_{i}.png"))
    all_urls.append((f"chile-oscuro-2_{i:02d}", f"{base}chile-oscuro-2_{i:02d}.png"))
    all_urls.append((f"chile-oscuro-2_{i:03d}", f"{base}chile-oscuro-2_{i:03d}.png"))

# Imperio: try 1-digit, 2-digit, 3-digit for 1-100
for i in range(1, 101):
    all_urls.append((f"Imperio{i}", f"{base}Toolkit-26-Imperio{i}.png"))
    all_urls.append((f"Imperio{i:02d}", f"{base}Toolkit-26-Imperio{i:02d}.png"))
    all_urls.append((f"Imperio{i:03d}", f"{base}Toolkit-26-Imperio{i:03d}.png"))

with ThreadPoolExecutor(max_workers=15) as executor:
    futures = {executor.submit(check_url, url): (label, url) for label, url in all_urls}
    results = []
    for future in as_completed(futures):
        url_result = future.result()
        label = futures[future][0]
        results.append((label, *url_result))

# Dedup by URL
seen_urls = set()
chile_found = []
imperio_found = []

results.sort(key=lambda x: x[0])
for label, url, status, ctype, size in results:
    if url in seen_urls:
        continue
    if status == 200 and 'image' in ctype.lower():
        seen_urls.add(url)
        if 'chile' in label:
            chile_found.append((label, url, size))
        else:
            imperio_found.append((label, url, size))

print("\n--- chile-oscuro-2 (all found) ---")
for label, url, size in sorted(chile_found, key=lambda x: x[0]):
    print(f"  {url.split('/')[-1]}  ({size} bytes)")

print(f"\nTotal chile-oscuro: {len(chile_found)}")

print("\n--- Toolkit-26-Imperio (all found) ---")
for label, url, size in sorted(imperio_found, key=lambda x: x[0]):
    print(f"  {url.split('/')[-1]}  ({size} bytes)")

print(f"\nTotal Imperio: {len(imperio_found)}")
