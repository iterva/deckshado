import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

def check_url(url):
    try:
        resp = requests.head(url, timeout=10, allow_redirects=True)
        return url, resp.status_code, resp.headers.get('Content-Type', ''), resp.headers.get('Content-Length', '0')
    except requests.RequestException as e:
        return url, None, '', str(e)

# Pattern 1: chile-oscuro-2_XXX.png (01 to 100)
urls_chile = []
for i in range(1, 101):
    num = f"{i:03d}"
    urls_chile.append(f"https://blog.myl.cl/wp-content/uploads/2026/03/chile-oscuro-2_{num}.png")

# Pattern 2: Toolkit-26-ImperioXX.png (01 to 100)
urls_imperio = []
for i in range(1, 101):
    num = f"{i:02d}"
    urls_imperio.append(f"https://blog.myl.cl/wp-content/uploads/2026/03/Toolkit-26-Imperio{num}.png")

print("=" * 70)
print("CHECKING: chile-oscuro-2_XXX.png (001 to 100)")
print("=" * 70)

found_chile = []
not_found_chile = []

with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(check_url, url): url for url in urls_chile}
    results = []
    for future in as_completed(futures):
        results.append(future.result())

results.sort(key=lambda x: x[0])

for url, status, ctype, size in results:
    num = url.split("_")[-1].replace(".png", "")
    if status == 200 and 'image' in ctype.lower():
        found_chile.append(num)
        print(f"  [OK]  {num} - {ctype} ({size} bytes)")
    else:
        not_found_chile.append(num)

print(f"\nFound: {len(found_chile)} images")
print(f"Missing: {len(not_found_chile)} images")
if not_found_chile:
    print(f"Missing numbers: {', '.join(not_found_chile)}")

print()
print("=" * 70)
print("CHECKING: Toolkit-26-ImperioXX.png (01 to 100)")
print("=" * 70)

found_imperio = []
not_found_imperio = []

with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(check_url, url): url for url in urls_imperio}
    results = []
    for future in as_completed(futures):
        results.append(future.result())

results.sort(key=lambda x: x[0])

for url, status, ctype, size in results:
    num = url.split("Imperio")[-1].replace(".png", "")
    if status == 200 and 'image' in ctype.lower():
        found_imperio.append(num)
        print(f"  [OK]  Imperio{num} - {ctype} ({size} bytes)")
    else:
        not_found_imperio.append(num)

print(f"\nFound: {len(found_imperio)} images")
print(f"Missing: {len(not_found_imperio)} images")
if not_found_imperio:
    print(f"Missing numbers: {', '.join(not_found_imperio)}")

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"chile-oscuro-2: {len(found_chile)}/100 available")
print(f"Toolkit-26-Imperio: {len(found_imperio)}/100 available")
