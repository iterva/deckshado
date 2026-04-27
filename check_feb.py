import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

def check_url(url):
    try:
        resp = session.head(url, timeout=10, allow_redirects=True)
        return url, resp.status_code, resp.headers.get('Content-Type', ''), resp.headers.get('Content-Length', '0')
    except:
        return url, None, '', '0'

feb_base = "https://blog.myl.cl/wp-content/uploads/2026/02/"

urls = []
for i in range(0, 50):
    for fmt in [f"{i}", f"{i:02d}", f"{i:03d}"]:
        urls.append(f"{feb_base}chile-oscuro-2_{fmt}.png")
        for suffix in ["-1", "-2", "-3"]:
            urls.append(f"{feb_base}chile-oscuro-2_{fmt}{suffix}.png")

urls = list(set(urls))
print(f"Checking {len(urls)} chile-oscuro URLs in 2026/02/...\n")

found = []
with ThreadPoolExecutor(max_workers=20) as executor:
    futures = {executor.submit(check_url, url): url for url in urls}
    for future in as_completed(futures):
        url, status, ctype, size = future.result()
        if status == 200 and 'image' in ctype.lower():
            found.append((url.split('/')[-1], url, size))

if found:
    print(f"FOUND {len(found)} chile-oscuro images:\n")
    for fname, url, size in sorted(found):
        print(f"  {fname:<50} ({size} bytes)")
else:
    print("No chile-oscuro in 2026/02/.")

# Also check Imperio in feb
urls2 = []
for i in range(0, 50):
    for fmt in [f"{i}", f"{i:02d}", f"{i:03d}"]:
        urls2.append(f"{feb_base}Toolkit-26-Imperio{fmt}.png")
        for suffix in ["-1", "-2", "-3"]:
            urls2.append(f"{feb_base}Toolkit-26-Imperio{fmt}{suffix}.png")
# reprint already known but check anyway
for i in range(0, 20):
    for fmt in [f"{i}", f"{i:02d}"]:
        urls2.append(f"{feb_base}Toolkit-26-Imperio-reprint_{fmt}.png")
        urls2.append(f"{feb_base}Toolkit-26-Imperio-reprint_{fmt}-1.png")
        urls2.append(f"{feb_base}Toolkit-26-Imperio-reprint_{fmt}-2.png")

urls2 = list(set(urls2))
print(f"\nChecking {len(urls2)} Imperio URLs in 2026/02/...\n")

found2 = []
with ThreadPoolExecutor(max_workers=20) as executor:
    futures = {executor.submit(check_url, url): url for url in urls2}
    for future in as_completed(futures):
        url, status, ctype, size = future.result()
        if status == 200 and 'image' in ctype.lower():
            found2.append((url.split('/')[-1], url, size))

if found2:
    print(f"FOUND {len(found2)} Imperio images:\n")
    for fname, url, size in sorted(found2):
        print(f"  {fname:<50} ({size} bytes)")
else:
    print("No Imperio in 2026/02/.")
