"""
Descarga las imágenes de cada RiftboundCard desde piltoverarchive
y las sube a Cloudinary bajo `riftbound/cards/<set>/<card_number>`.
Luego actualiza `RiftboundCard.cdn_image_url`.

Uso:
    python migrate_riftbound_card_images.py [--limit N] [--workers 4]
"""
import argparse
import io
import os
import sys
import django
import requests
import cloudinary
import cloudinary.uploader
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from riftbound.models import RiftboundCard  # noqa: E402

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME", "dmvu6tuee"),
    api_key=os.environ.get("CLOUDINARY_API_KEY", "618467334728855"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET", "egB_Ypv0wdVVBL2oRhUaoHr8bY8"),
    secure=True,
)


def slugify(s: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in s).strip("_").lower()


def upload_card(card: RiftboundCard, session: requests.Session) -> tuple[int, str, str]:
    """Devuelve (card_id, status, mensaje)."""
    if card.cdn_image_url:
        return (card.id, "skip", "ya tiene cdn")
    if not card.image_url:
        return (card.id, "skip", "sin image_url")

    set_code = (card.set.code if card.set else "UNKNOWN").lower()
    public_id = f"riftbound/cards/{set_code}/{slugify(card.card_number)}"
    try:
        r = session.get(card.image_url, timeout=30)
        r.raise_for_status()
        buf = io.BytesIO(r.content)
        buf.name = f"{slugify(card.card_number)}.webp"
        result = cloudinary.uploader.upload(
            buf,
            public_id=public_id,
            overwrite=True,
            resource_type="image",
        )
        cdn = result["secure_url"]
        card.cdn_image_url = cdn
        card.save(update_fields=["cdn_image_url"])
        return (card.id, "ok", cdn)
    except Exception as e:
        return (card.id, "error", str(e))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="0 = todas")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--force", action="store_true",
                    help="Re-subir incluso si ya tienen cdn_image_url")
    args = ap.parse_args()

    qs = RiftboundCard.objects.select_related("set").all()
    if not args.force:
        qs = qs.filter(cdn_image_url="")
    qs = qs.exclude(image_url="")
    if args.limit:
        qs = qs[:args.limit]
    cards = list(qs)
    total = len(cards)
    print(f"[+] {total} cartas pendientes")

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 deckshado-card-migrator/1.0"})

    ok = skip = fail = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(upload_card, c, session): c for c in cards}
        for i, fut in enumerate(as_completed(futures), 1):
            card = futures[fut]
            try:
                _, status, msg = fut.result()
            except Exception as e:
                status, msg = "error", str(e)
            if status == "ok":
                ok += 1
            elif status == "skip":
                skip += 1
            else:
                fail += 1
            if i % 25 == 0 or status == "error":
                print(f"  [{i}/{total}] {card.card_number} {status} {msg if status != 'ok' else ''}")

    print(f"\n[OK] subidos={ok}  saltados={skip}  errores={fail}")


if __name__ == "__main__":
    main()
