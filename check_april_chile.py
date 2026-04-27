import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

apr_base = "https://blog.myl.cl/wp-content/uploads/2026/04/"

def check_url(url):
    try:
        resp = session.head(url, timeout=10, allow_redirects=True)
        return url, resp.status_code, resp.headers.get('Content-Type', ''), resp.headers.get('Content-Length', '0')
    except:
        return url, None, '', '0'

urls = []
for i in range(0, 50):
    for fmt in [f"{i}", f"{i:02d}", f"{i:03d}"]:
        urls.append(f"{apr_base}chile-oscuro-2_{fmt}.png")
        for suffix in ["-1", "-2", "-3"]:
            urls.append(f"{apr_base}chile-oscuro-2_{fmt}{suffix}.png")

urls = list(set(urls))
print(f"Checking {len(urls)} URLs in 2026/04/...\n")

found = []
with ThreadPoolExecutor(max_workers=20) as executor:
    futures = {executor.submit(check_url, url): url for url in urls}
    for future in as_completed(futures):
        url, status, ctype, size = future.result()
        if status == 200 and 'image' in ctype.lower():
            found.append((url.split('/')[-1], url, size))

if found:
    print(f"FOUND {len(found)} images:\n")
    for fname, url, size in sorted(found):
        print(f"  {fname:<50} ({size} bytes)")
else:
    print("No chile-oscuro images found in 2026/04/.")
