import os
import django
from collections import defaultdict

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from cards.models import Edition, Card

e = Edition.objects.get(slug="aydv")
by_url = defaultdict(list)
for c in Card.objects.filter(edition=e):
    u = (c.custom_image_url or "").strip()
    if u:
        by_url[u].append(c)

dups = {u: rows for u, rows in by_url.items() if len(rows) > 1}
print("duplicate_urls=", len(dups))
for u, rows in dups.items():
    print("URL:", u)
    for r in rows:
        print("  -", r.edid, "|", r.name, "|", r.myl_id)
