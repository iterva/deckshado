import requests
from bs4 import BeautifulSoup
import re

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

base = "https://blog.myl.cl"
upload_dir = f"{base}/wp-content/uploads/2026/03/"

# =============================================
# 1. Check directory listing (Apache/Nginx)
# =============================================
print("=" * 70)
print("1. Checking directory listing...")
print("=" * 70)
try:
    resp = session.get(upload_dir, timeout=15)
    print(f"   Status: {resp.status_code}")
    if resp.status_code == 200 and ('Index of' in resp.text or '<pre>' in resp.text):
        print("   Directory listing ENABLED!")
        soup = BeautifulSoup(resp.text, 'html.parser')
        links = soup.find_all('a')
        pngs = [a['href'] for a in links if a.get('href', '').endswith('.png')]
        print(f"   Found {len(pngs)} PNG files")
        for p in sorted(pngs)[:20]:
            print(f"     {p}")
    else:
        print("   Directory listing disabled or redirected.")
        print(f"   Content-Type: {resp.headers.get('Content-Type','')}")
        # Check if it's a 403 or redirect
        if resp.status_code in (301, 302, 403):
            print(f"   Response: {resp.status_code}")
except Exception as e:
    print(f"   Error: {e}")

# =============================================
# 2. WordPress REST API - Media endpoint
# =============================================
print()
print("=" * 70)
print("2. WordPress REST API - /wp-json/wp/v2/media")
print("=" * 70)

chile_files = []
imperio_files = []

try:
    page = 1
    total_found = 0
    while page <= 20:  # max 20 pages
        url = f"{base}/wp-json/wp/v2/media?per_page=100&page={page}&search=chile-oscuro"
        resp = session.get(url, timeout=15)
        if resp.status_code != 200:
            print(f"   Page {page}: status {resp.status_code} - stopping")
            break
        data = resp.json()
        if not data:
            break
        for item in data:
            src = item.get('source_url', '')
            title = item.get('title', {}).get('rendered', '')
            if 'chile-oscuro' in src.lower():
                chile_files.append(src)
        total_found += len(data)
        total_pages = int(resp.headers.get('X-WP-TotalPages', 1))
        print(f"   Page {page}/{total_pages}: got {len(data)} items")
        if page >= total_pages:
            break
        page += 1
    
    print(f"\n   chile-oscuro files found via API: {len(chile_files)}")
    for f in sorted(chile_files):
        print(f"     {f.split('/')[-1]}")

except Exception as e:
    print(f"   Error: {e}")

print()
try:
    page = 1
    while page <= 20:
        url = f"{base}/wp-json/wp/v2/media?per_page=100&page={page}&search=Toolkit-26-Imperio"
        resp = session.get(url, timeout=15)
        if resp.status_code != 200:
            print(f"   Page {page}: status {resp.status_code} - stopping")
            break
        data = resp.json()
        if not data:
            break
        for item in data:
            src = item.get('source_url', '')
            if 'imperio' in src.lower() or 'Imperio' in src:
                imperio_files.append(src)
        total_pages = int(resp.headers.get('X-WP-TotalPages', 1))
        print(f"   Page {page}/{total_pages}: got {len(data)} items (Imperio search)")
        if page >= total_pages:
            break
        page += 1
    
    print(f"\n   Imperio files found via API: {len(imperio_files)}")
    for f in sorted(imperio_files):
        print(f"     {f.split('/')[-1]}")
except Exception as e:
    print(f"   Error: {e}")

# =============================================
# 3. Try broader search via API (2026/03 uploads)
# =============================================
print()
print("=" * 70)
print("3. WordPress REST API - All media from 2026-03")
print("=" * 70)

all_march_files = []
try:
    page = 1
    while page <= 50:
        url = f"{base}/wp-json/wp/v2/media?per_page=100&page={page}&after=2026-02-28T23:59:59&before=2026-04-01T00:00:00"
        resp = session.get(url, timeout=15)
        if resp.status_code != 200:
            print(f"   Page {page}: status {resp.status_code} - stopping")
            break
        data = resp.json()
        if not data:
            break
        for item in data:
            src = item.get('source_url', '')
            all_march_files.append(src)
        total_pages = int(resp.headers.get('X-WP-TotalPages', 1))
        total_items = resp.headers.get('X-WP-Total', '?')
        print(f"   Page {page}/{total_pages}: got {len(data)} items (total: {total_items})")
        if page >= total_pages:
            break
        page += 1

    # Filter for our patterns
    chile_all = sorted([f for f in all_march_files if 'chile-oscuro' in f.lower()])
    imperio_all = sorted([f for f in all_march_files if 'imperio' in f.lower()])
    other = sorted([f for f in all_march_files if 'chile-oscuro' not in f.lower() and 'imperio' not in f.lower()])

    print(f"\n   Total March 2026 media: {len(all_march_files)}")
    
    if chile_all:
        print(f"\n   --- chile-oscuro ({len(chile_all)}) ---")
        for f in chile_all:
            print(f"     {f.split('/')[-1]}")
    
    if imperio_all:
        print(f"\n   --- Imperio ({len(imperio_all)}) ---")
        for f in imperio_all:
            print(f"     {f.split('/')[-1]}")
    
    if other:
        print(f"\n   --- Other files ({len(other)}) ---")
        for f in other[:30]:
            print(f"     {f.split('/')[-1]}")
        if len(other) > 30:
            print(f"     ... and {len(other)-30} more")

except Exception as e:
    print(f"   Error: {e}")

# =============================================
# 4. Check sitemap for media
# =============================================
print()
print("=" * 70)
print("4. Checking sitemaps for media URLs")
print("=" * 70)

sitemap_urls = [
    f"{base}/sitemap.xml",
    f"{base}/wp-sitemap.xml",
    f"{base}/sitemap_index.xml",
    f"{base}/wp-sitemap-post-attachment-1.xml",
]

for surl in sitemap_urls:
    try:
        resp = session.get(surl, timeout=10)
        if resp.status_code == 200:
            print(f"   [OK] {surl}")
            # Look for sub-sitemaps
            if 'sitemap' in resp.text.lower():
                soup = BeautifulSoup(resp.text, 'xml') if 'xml' in resp.headers.get('Content-Type','') else BeautifulSoup(resp.text, 'html.parser')
                locs = soup.find_all('loc')
                for loc in locs:
                    txt = loc.text
                    if 'attachment' in txt or 'media' in txt or 'image' in txt or 'upload' in txt:
                        print(f"        -> {txt}")
        else:
            print(f"   [{resp.status_code}] {surl}")
    except Exception as e:
        print(f"   [ERR] {surl}: {e}")

# =============================================
# 5. Now check -1, -2 suffix variants
# =============================================
print()
print("=" * 70)
print("5. Checking -1, -2 suffix variants for chile-oscuro")
print("=" * 70)

from concurrent.futures import ThreadPoolExecutor, as_completed

def check_url(url):
    try:
        resp = session.head(url, timeout=10, allow_redirects=True)
        return url, resp.status_code, resp.headers.get('Content-Type', ''), resp.headers.get('Content-Length', '0')
    except:
        return url, None, '', '0'

suffix_urls = []
for i in range(1, 51):
    for fmt in [f"{i}", f"{i:02d}", f"{i:03d}"]:
        for suffix in ["-1", "-2", "-3", "-scaled"]:
            suffix_urls.append(f"https://blog.myl.cl/wp-content/uploads/2026/03/chile-oscuro-2_{fmt}{suffix}.png")

found_suffix = []
with ThreadPoolExecutor(max_workers=15) as executor:
    futures = {executor.submit(check_url, url): url for url in suffix_urls}
    for future in as_completed(futures):
        url, status, ctype, size = future.result()
        if status == 200 and 'image' in ctype.lower():
            found_suffix.append((url.split('/')[-1], size))

for name, size in sorted(found_suffix):
    print(f"  [OK]  {name}  ({size} bytes)")
print(f"\nTotal suffix variants: {len(found_suffix)}")

# Same for Imperio
print()
print("=" * 70)
print("6. Checking -1, -2 suffix variants for Imperio")
print("=" * 70)

suffix_urls2 = []
for i in range(1, 51):
    for fmt in [f"{i}", f"{i:02d}", f"{i:03d}"]:
        for suffix in ["-1", "-2", "-3", "-scaled"]:
            suffix_urls2.append(f"https://blog.myl.cl/wp-content/uploads/2026/03/Toolkit-26-Imperio{fmt}{suffix}.png")

found_suffix2 = []
with ThreadPoolExecutor(max_workers=15) as executor:
    futures = {executor.submit(check_url, url): url for url in suffix_urls2}
    for future in as_completed(futures):
        url, status, ctype, size = future.result()
        if status == 200 and 'image' in ctype.lower():
            found_suffix2.append((url.split('/')[-1], size))

for name, size in sorted(found_suffix2):
    print(f"  [OK]  {name}  ({size} bytes)")
print(f"\nTotal suffix variants: {len(found_suffix2)}")
