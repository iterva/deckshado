import os
import django
import requests

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from cards.models import Edition, Card

targets = [
    "Semyazza",
    "El Arca",
    "El Gran Descenso",
    "Gran Diluvio",
    "Guerra Celestial",
    "Trono del Cielo",
    "Trono del Dragon",
    "Trono del Dragón",
    "Fuego Purificador",
]

e = Edition.objects.get(slug="aydv")
qs = Card.objects.filter(edition=e)

rows = []
for t in targets:
    for c in qs.filter(name__iexact=t):
        url = (c.custom_image_url or "").strip()
        status = None
        ctype = ""
        try:
            r = requests.get(url, timeout=20, stream=True)
            status = r.status_code
            ctype = r.headers.get("Content-Type", "")
            r.close()
        except Exception as exc:
            status = f"ERR:{exc}"
        rows.append((c.edid, c.name, c.myl_id, url, status, ctype))

for row in sorted(rows, key=lambda x: x[0]):
    print(" | ".join(str(x) for x in row))
