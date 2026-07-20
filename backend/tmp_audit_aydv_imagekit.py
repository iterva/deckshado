import os
import json
import django
import requests
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from cards.models import Edition, Card

edition = Edition.objects.get(slug="aydv")
cards = list(Card.objects.filter(edition=edition).values("id", "name", "edid", "myl_id", "custom_image_url"))

total = len(cards)
missing_url = [c for c in cards if not (c.get("custom_image_url") or "").strip()]
with_url = [c for c in cards if (c.get("custom_image_url") or "").strip()]
imagekit = [c for c in with_url if "ik.imagekit.io" in (c.get("custom_image_url") or "").lower()]
non_imagekit = [c for c in with_url if "ik.imagekit.io" not in (c.get("custom_image_url") or "").lower()]

def check_card(card):
    url = (card.get("custom_image_url") or "").strip()
    try:
        resp = requests.get(url, timeout=20, stream=True)
        status = resp.status_code
        ctype = (resp.headers.get("Content-Type") or "").lower()
        resp.close()
        ok = (status == 200 and ctype.startswith("image/"))
        return {
            "ok": ok,
            "status": status,
            "ctype": ctype,
            "name": card.get("name"),
            "edid": card.get("edid"),
            "url": url,
        }
    except Exception as exc:
        return {
            "ok": False,
            "status": None,
            "ctype": "",
            "name": card.get("name"),
            "edid": card.get("edid"),
            "url": url,
            "error": str(exc),
        }

results = []
with ThreadPoolExecutor(max_workers=20) as ex:
    futures = [ex.submit(check_card, c) for c in imagekit]
    for fut in as_completed(futures):
        results.append(fut.result())

ok_count = sum(1 for r in results if r["ok"])
bad = [r for r in results if not r["ok"]]
status_counter = Counter(str(r.get("status")) for r in bad)

url_counter = Counter((c.get("custom_image_url") or "").strip() for c in imagekit)
duplicates = [{"url": u, "count": n} for u, n in url_counter.items() if n > 1]
duplicates.sort(key=lambda x: x["count"], reverse=True)

summary = {
    "total_cards": total,
    "missing_url": len(missing_url),
    "with_url": len(with_url),
    "imagekit_urls": len(imagekit),
    "non_imagekit_urls": len(non_imagekit),
    "imagekit_ok_image_http200": ok_count,
    "imagekit_bad": len(bad),
    "bad_by_status": dict(status_counter),
    "duplicate_imagekit_urls": len(duplicates),
}

print("SUMMARY:")
print(json.dumps(summary, ensure_ascii=False, indent=2))

print("\nBAD_SAMPLE:")
for row in bad[:20]:
    print(json.dumps(row, ensure_ascii=False))

print("\nDUPLICATE_URL_SAMPLE:")
for row in duplicates[:20]:
    print(json.dumps(row, ensure_ascii=False))
