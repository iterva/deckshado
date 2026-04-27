import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

def check_url(url):
    try:
        resp = requests.head(url, timeout=10, allow_redirects=True)
        return url, resp.status_code, resp.headers.get('Content-Type', ''), resp.headers.get('Content-Length', '0')
    except requests.RequestException as e:
        return url, None, '', str(e)

# Check 2-digit variants for chile-oscuro
print("=" * 70)
print("VARIANT: chile-oscuro-2_XX.png (2 digits, 01 to 50)")
print("=" * 70)

urls = []
for i in range(1, 51):
    num = f"{i:02d}"
    urls.append(f"https://blog.myl.cl/wp-content/uploads/2026/03/chile-oscuro-2_{num}.png")

with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(check_url, url): url for url in urls}
    results = []
    for future in as_completed(futures):
        results.append(future.result())

results.sort(key=lambda x: x[0])
for url, status, ctype, size in results:
    if status == 200 and 'image' in ctype.lower():
        print(f"  [OK]  {url.split('/')[-1]} - {ctype} ({size} bytes)")

# Check variant without underscore
print()
print("=" * 70)
print("VARIANT: chile-oscuro-2-XXX.png (dash instead of underscore)")
print("=" * 70)

urls = []
for i in range(1, 51):
    for fmt in [f"{i:02d}", f"{i:03d}"]:
        urls.append(f"https://blog.myl.cl/wp-content/uploads/2026/03/chile-oscuro-2-{fmt}.png")

with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(check_url, url): url for url in urls}
    results = []
    for future in as_completed(futures):
        results.append(future.result())

results.sort(key=lambda x: x[0])
for url, status, ctype, size in results:
    if status == 200 and 'image' in ctype.lower():
        print(f"  [OK]  {url.split('/')[-1]} - {ctype} ({size} bytes)")

# Check Imperio with 3 digits
print()
print("=" * 70)
print("VARIANT: Toolkit-26-ImperioXXX.png (3 digits)")
print("=" * 70)

urls = []
for i in range(1, 51):
    num = f"{i:03d}"
    urls.append(f"https://blog.myl.cl/wp-content/uploads/2026/03/Toolkit-26-Imperio{num}.png")

with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(check_url, url): url for url in urls}
    results = []
    for future in as_completed(futures):
        results.append(future.result())

results.sort(key=lambda x: x[0])
for url, status, ctype, size in results:
    if status == 200 and 'image' in ctype.lower():
        print(f"  [OK]  {url.split('/')[-1]} - {ctype} ({size} bytes)")

# Check lowercase/other variants
print()
print("=" * 70)
print("VARIANT: Toolkit-26-imperio (lowercase)")
print("=" * 70)

urls = []
for i in range(1, 51):
    for fmt in [f"{i:02d}", f"{i:03d}"]:
        urls.append(f"https://blog.myl.cl/wp-content/uploads/2026/03/Toolkit-26-imperio{fmt}.png")

with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(check_url, url): url for url in urls}
    results = []
    for future in as_completed(futures):
        results.append(future.result())

results.sort(key=lambda x: x[0])
for url, status, ctype, size in results:
    if status == 200 and 'image' in ctype.lower():
        print(f"  [OK]  {url.split('/')[-1]} - {ctype} ({size} bytes)")

# Check .jpg variants
print()
print("=" * 70)
print("VARIANT: .jpg versions")
print("=" * 70)

urls = []
for i in range(1, 51):
    urls.append(f"https://blog.myl.cl/wp-content/uploads/2026/03/chile-oscuro-2_{i:03d}.jpg")
    urls.append(f"https://blog.myl.cl/wp-content/uploads/2026/03/Toolkit-26-Imperio{i:02d}.jpg")

with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(check_url, url): url for url in urls}
    results = []
    for future in as_completed(futures):
        results.append(future.result())

results.sort(key=lambda x: x[0])
for url, status, ctype, size in results:
    if status == 200 and 'image' in ctype.lower():
        print(f"  [OK]  {url.split('/')[-1]} - {ctype} ({size} bytes)")

print("\nDone checking variants.")
