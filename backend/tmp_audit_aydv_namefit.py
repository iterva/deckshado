import os
import re
import django
import unicodedata
from difflib import SequenceMatcher
from urllib.parse import urlparse

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from cards.models import Edition, Card

def norm(t):
    t = (t or "").strip()
    t = unicodedata.normalize("NFKD", t)
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    t = t.lower()
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def file_name_from_url(url):
    path = urlparse(url).path
    base = path.rsplit("/", 1)[-1]
    base = re.sub(r"\.[a-z0-9]+$", "", base.lower())
    base = re.sub(r"^\d+_", "", base)
    return norm(base.replace("-", " "))

e = Edition.objects.get(slug="aydv")
suspects = []
for c in Card.objects.filter(edition=e):
    url = (c.custom_image_url or "").strip()
    if not url:
        continue
    fname = file_name_from_url(url)
    cname = norm(c.name)
    score = SequenceMatcher(None, cname, fname).ratio()
    if score < 0.78:
        suspects.append((score, c.edid, c.name, fname, url))

suspects.sort(key=lambda x: x[0])
print("suspect_count=", len(suspects))
for s in suspects[:40]:
    print(f"{s[0]:.3f} | {s[1]} | {s[2]} | url_name={s[3]}")
