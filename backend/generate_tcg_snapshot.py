import json
import time
from pathlib import Path

import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from riftbound.models import RiftboundCard
from riftbound.tcgplayer import get_tcg_price


def main():
    names = sorted(set(
        RiftboundCard.objects.filter(is_active=True)
        .exclude(name__isnull=True)
        .exclude(name__exact="")
        .values_list("name", flat=True)
    ))

    out = {
        "generated_at": int(time.time()),
        "source": "tcgplayer-live",
        "count": 0,
        "prices": {},
    }

    total = len(names)
    print(f"Consultando {total} nombres unicos...")
    for idx, name in enumerate(names, start=1):
        data = get_tcg_price(name)
        if data and data.get("market_price") is not None:
            out["prices"][name.lower().strip()] = {
                "card_name": name,
                "product_name": data.get("product_name"),
                "market_price": data.get("market_price"),
                "low_price": data.get("low_price"),
                "mid_price": data.get("mid_price"),
                "high_price": data.get("high_price"),
                "product_url": data.get("product_url"),
                "image_url": data.get("image_url") or "",
            }
        if idx % 50 == 0 or idx == total:
            print(f"  {idx}/{total} procesadas")
        time.sleep(0.12)

    out["count"] = len(out["prices"])
    target = Path(__file__).parent / "riftbound" / "tcgplayer_snapshot.json"
    target.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"Snapshot guardado en: {target}")
    print(f"Precios con valor: {out['count']}")


if __name__ == "__main__":
    main()
