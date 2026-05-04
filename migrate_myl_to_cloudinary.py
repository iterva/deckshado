"""
Migra imágenes de api.myl.cl → Cloudinary para Escuelas Elementales + Imperio (todas las rarezas).

Uso:
    python migrate_myl_to_cloudinary.py [--dry-run] [--limit N] [--workers N]

- Lee la DB local (backend/db.sqlite3) para obtener cartas a migrar.
- Para cada carta, descarga vía wsrv.nl (porque api.myl.cl tiene cert vencido).
- Sube a Cloudinary en deckshado/myl_cards/{edition_slug}/{edid}.
- Guarda progreso en myl_cloudinary_mapping.json (resume-safe).
- Genera un JSON listo para aplicar en producción con el management command.
"""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import django
import requests
import cloudinary
import cloudinary.uploader

# Setup Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from django.db.models import Q  # noqa: E402
from cards.models import Card  # noqa: E402

cloudinary.config(
    cloud_name="dmvu6tuee",
    api_key="618467334728855",
    api_secret="egB_Ypv0wdVVBL2oRhUaoHr8bY8",
    secure=True,
)

ESC_EDITION_SLUGS = [
    "bushido", "sol-naciente", "dominio", "contraataque",
    "aguila-imperial", "steampunk", "axis-mundi", "hijos-del-sol",
    "legado-gotico", "escuelas_elementales", "heroes_de_dharma",
]

MAPPING_FILE = "myl_cloudinary_mapping.json"
WSRV_PROXY = "https://wsrv.nl/?url=api.myl.cl/static/cards/{ed_myl_id}/{edid}.png"


def load_mapping():
    if os.path.exists(MAPPING_FILE):
        with open(MAPPING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_mapping(mapping):
    with open(MAPPING_FILE, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)


def get_target_cards():
    qs = (
        Card.objects.filter(
            Q(edition__slug__in=ESC_EDITION_SLUGS) | Q(edition__format__code="imp")
        )
        .exclude(edition__myl_id__startswith="custom_")
        .select_related("edition")
        .order_by("edition__slug", "edid")
    )
    return list(qs.values("id", "myl_id", "edid", "edition__slug", "edition__myl_id", "name"))


def upload_one(card, session):
    """Download from wsrv.nl proxy and upload to Cloudinary."""
    ed_slug = card["edition__slug"]
    ed_myl = card["edition__myl_id"]
    edid = card["edid"]
    myl_id = card["myl_id"]

    src_url = WSRV_PROXY.format(ed_myl_id=ed_myl, edid=edid)
    public_id = f"deckshado/myl_cards/{ed_slug}/{edid}"

    try:
        # Download bytes via wsrv.nl
        r = session.get(src_url, timeout=30)
        if r.status_code != 200 or not r.content:
            return myl_id, None, f"download failed (status {r.status_code})"
        if "image" not in r.headers.get("Content-Type", ""):
            return myl_id, None, f"not an image (CT={r.headers.get('Content-Type')})"

        # Upload bytes directly to Cloudinary
        result = cloudinary.uploader.upload(
            r.content,
            public_id=public_id,
            overwrite=False,  # don't overwrite if already exists
            resource_type="image",
        )
        return myl_id, result["secure_url"], "OK"
    except Exception as e:
        return myl_id, None, f"ERROR: {e}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="No subir, solo listar")
    parser.add_argument("--limit", type=int, default=None, help="Limitar a N cartas")
    parser.add_argument("--workers", type=int, default=6, help="Concurrencia (default 6)")
    parser.add_argument("--skip-existing", action="store_true", default=True,
                        help="Saltar cartas ya en mapping")
    args = parser.parse_args()

    cards = get_target_cards()
    print(f"Total cartas en scope: {len(cards)}")

    mapping = load_mapping()
    print(f"Mapping previo: {len(mapping)} entries")

    pending = [c for c in cards if c["myl_id"] not in mapping]
    print(f"Pendientes: {len(pending)}")

    if args.limit:
        pending = pending[: args.limit]
        print(f"Limitado a {len(pending)} (--limit)")

    if args.dry_run:
        print("\n--- DRY RUN ---")
        for c in pending[:30]:
            print(f"  {c['edition__slug']}/{c['edid']} | {c['name']}")
        if len(pending) > 30:
            print(f"  ... y {len(pending) - 30} más")
        return

    if not pending:
        print("Nada que hacer.")
        return

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 deckshado-migrator"})

    ok = 0
    fail = 0
    start = time.time()
    save_every = 50

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(upload_one, c, session): c for c in pending}
        for i, fut in enumerate(as_completed(futures), 1):
            card = futures[fut]
            myl_id, url, status = fut.result()
            if url:
                mapping[myl_id] = url
                ok += 1
            else:
                fail += 1
            elapsed = time.time() - start
            rate = i / elapsed if elapsed > 0 else 0
            eta = (len(pending) - i) / rate if rate > 0 else 0
            print(
                f"[{i}/{len(pending)}] {card['edition__slug']}/{card['edid']} "
                f"({card['name'][:30]}) {status} | OK={ok} FAIL={fail} "
                f"| rate={rate:.1f}/s ETA={eta:.0f}s"
            )

            if i % save_every == 0:
                save_mapping(mapping)

    save_mapping(mapping)
    print(f"\n=== Listo: OK={ok} FAIL={fail} en {time.time()-start:.0f}s ===")
    print(f"Mapping guardado en {MAPPING_FILE}")
    print("\nProximo paso: copiar el JSON a PA y correr:")
    print("  python manage.py apply_cloudinary_mapping myl_cloudinary_mapping.json")


if __name__ == "__main__":
    main()
