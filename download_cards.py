import requests
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

base = "https://blog.myl.cl"
out_dir = os.path.join(os.path.dirname(__file__), "cartas-blog")
os.makedirs(out_dir, exist_ok=True)

# Gather all media URLs from WP REST API
all_urls = set()

# Search chile-oscuro
page = 1
while page <= 20:
    url = f"{base}/wp-json/wp/v2/media?per_page=100&page={page}&search=chile-oscuro"
    resp = session.get(url, timeout=15)
    if resp.status_code != 200:
        break
    data = resp.json()
    if not data:
        break
    for item in data:
        src = item.get('source_url', '')
        if 'chile-oscuro' in src.lower():
            all_urls.add(src)
    total_pages = int(resp.headers.get('X-WP-TotalPages', 1))
    if page >= total_pages:
        break
    page += 1

# Search Imperio
page = 1
while page <= 20:
    url = f"{base}/wp-json/wp/v2/media?per_page=100&page={page}&search=Toolkit-26-Imperio"
    resp = session.get(url, timeout=15)
    if resp.status_code != 200:
        break
    data = resp.json()
    if not data:
        break
    for item in data:
        src = item.get('source_url', '')
        if 'imperio' in src.lower():
            all_urls.add(src)
    total_pages = int(resp.headers.get('X-WP-TotalPages', 1))
    if page >= total_pages:
        break
    page += 1

print(f"Found {len(all_urls)} unique URLs to download\n")

def download(url):
    fname = url.split('/')[-1]
    path = os.path.join(out_dir, fname)
    if os.path.exists(path):
        return fname, "SKIPPED (exists)"
    try:
        r = session.get(url, timeout=30)
        if r.status_code == 200 and 'image' in r.headers.get('Content-Type', ''):
            with open(path, 'wb') as f:
                f.write(r.content)
            size_kb = len(r.content) / 1024
            return fname, f"OK ({size_kb:.0f} KB)"
        else:
            return fname, f"FAILED (status {r.status_code})"
    except Exception as e:
        return fname, f"ERROR ({e})"

downloaded = 0
failed = 0

with ThreadPoolExecutor(max_workers=8) as executor:
    futures = {executor.submit(download, url): url for url in sorted(all_urls)}
    for future in as_completed(futures):
        fname, status = future.result()
        print(f"  {status:<25} {fname}")
        if status.startswith("OK") or status.startswith("SKIPPED"):
            downloaded += 1
        else:
            failed += 1

print(f"\nDone: {downloaded} downloaded, {failed} failed")
print(f"Saved to: {out_dir}")
