"""
Descarga las imágenes de cada RiftboundCard desde Riftcodex API
y las sube al CDN configurado bajo `riftbound/cards/<set>/<card_number>`.
Luego actualiza `RiftboundCard.cdn_image_url`.

Orden de fuentes:
1) `media.image_url` desde https://api.riftcodex.com/cards
2) Fallback a `RiftboundCard.image_url` en la BD local

Uso:
    python migrate_riftbound_card_images.py [--limit N] [--workers 4]

Variables de entorno:
    CDN_PROVIDER=imagekit | cloudinary (default: cloudinary)
"""
import argparse
import io
import os
import sys
import django
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from cdn_uploader import candidate_public_urls, upload_bytes

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from riftbound.models import RiftboundCard  # noqa: E402


def slugify(s: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in s).strip("_").lower()


def _card_number_from_api(card: dict) -> str:
    """
    Convierte riftbound_id API -> card_number local.

    Ejemplos:
    - unl-060a-219 -> UNL-060a
    - ogn-299-298 (overnumbered) -> OGN-299*
    - ogn-299*-298 (signature) -> OGN-299**
    """
    rid = (card.get("riftbound_id") or "").strip().lower()
    meta = card.get("metadata") or {}
    parts = rid.split("-")
    if len(parts) < 2:
        return ""

    set_code = parts[0].upper()
    number_part = parts[1].rstrip("*")
    base = f"{set_code}-{number_part}"

    if meta.get("signature"):
        return f"{base}**"
    if meta.get("overnumbered"):
        return f"{base}*"
    return base


def fetch_riftcodex_image_map(session: requests.Session) -> dict[str, str]:
    """Construye mapa card_number local -> media.image_url desde API Riftcodex."""
    out: dict[str, str] = {}
    page = 1
    while True:
        r = session.get(
            "https://api.riftcodex.com/cards",
            params={"page": page, "size": 100},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        items = data.get("items") or []

        for item in items:
            card_number = _card_number_from_api(item)
            image_url = ((item.get("media") or {}).get("image_url") or "").strip()
            if card_number and image_url:
                out[card_number] = image_url

        pages = int(data.get("pages") or 1)
        if page >= pages:
            break
        page += 1

    return out


def upload_card(
    card: RiftboundCard,
    session: requests.Session,
    riftcodex_images: dict[str, str],
    force: bool = False,
) -> tuple[int, str, str]:
    """Devuelve (card_id, status, mensaje)."""
    if card.cdn_image_url and not force:
        return (card.id, "skip", "ya tiene cdn")

    source_url = riftcodex_images.get(card.card_number) or card.image_url
    if not source_url:
        return (card.id, "skip", "sin image_url")

    set_code = (card.set.code if card.set else "UNKNOWN").lower()
    public_id = f"riftbound/cards/{set_code}/{slugify(card.card_number)}"
    # Fast path: si ya existe en CDN (migraciones previas),
    # solo registramos la URL sin re-descargar ni re-subir.
    for existing in candidate_public_urls(public_id, ("webp", "png", "jpg", "jpeg")):
        try:
            h = session.head(existing, timeout=10)
            if h.status_code == 200:
                card.cdn_image_url = existing
                card.save(update_fields=["cdn_image_url"])
                return (card.id, "linked", existing)
        except Exception:
            pass

    try:
        r = session.get(source_url, timeout=30)
        r.raise_for_status()
        buf = io.BytesIO(r.content)
        ext = source_url.split("?")[0].rsplit(".", 1)[-1].lower()
        if ext not in {"webp", "png", "jpg", "jpeg"}:
            ext = "webp"
        buf.name = f"{slugify(card.card_number)}.{ext}"
        cdn = upload_bytes(
            buf.getvalue(),
            public_id=public_id,
            default_ext=ext,
            mime_type=r.headers.get("Content-Type", "image/webp"),
            overwrite=True,
        )
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

    try:
        riftcodex_images = fetch_riftcodex_image_map(session)
        print(f"[+] Riftcodex map cargado: {len(riftcodex_images)} imágenes")
    except Exception as e:
        riftcodex_images = {}
        print(f"[WARN] No se pudo cargar mapa Riftcodex ({e}); usando image_url local")

    ok = skip = fail = 0
    linked = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {
            ex.submit(upload_card, c, session, riftcodex_images, args.force): c
            for c in cards
        }
        for i, fut in enumerate(as_completed(futures), 1):
            card = futures[fut]
            try:
                _, status, msg = fut.result()
            except Exception as e:
                status, msg = "error", str(e)
            if status == "ok":
                ok += 1
            elif status == "linked":
                linked += 1
            elif status == "skip":
                skip += 1
            else:
                fail += 1
            if i % 25 == 0 or status == "error":
                print(f"  [{i}/{total}] {card.card_number} {status} {msg if status != 'ok' else ''}")

    print(f"\n[OK] subidos={ok}  linkeados={linked}  saltados={skip}  errores={fail}")


if __name__ == "__main__":
    main()
