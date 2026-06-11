"""
Migra imagenes de api.myl.cl al CDN configurado por bloques (scope).

Uso:
    python migrate_myl_to_cloudinary.py [--scope imp|esc|pe|imp_r|all] [--dry-run] [--limit N] [--workers N]
                                      [--max-ok N] [--max-bytes N]
                                      [--allow-budget-overshoot] [--allow-unbounded]

- Lee la DB local (backend/db.sqlite3) para obtener cartas a migrar.
- Para cada carta, descarga via wsrv.nl (porque api.myl.cl tiene cert vencido).
- Sube al proveedor configurado (cloudinary, imagekit o r2) en deckshado/myl_cards/{edition_slug}/{edid}.
- Guarda progreso en myl_cloudinary_mapping.json (resume-safe).

Variables de entorno:
    CDN_PROVIDER=cloudinary | imagekit | r2 (default: cloudinary)
    CDN_UPLOADS_DISABLED=1  (kill-switch global para bloquear TODAS las subidas)
    CDN_MAX_UPLOAD_CALLS=N  (tope global de uploads por proceso)
    CDN_MAX_UPLOAD_BYTES=N  (tope global de bytes por proceso)

    Si CDN_PROVIDER=cloudinary:
        CLOUDINARY_CLOUD_NAME
        CLOUDINARY_API_KEY
        CLOUDINARY_API_SECRET

    Si CDN_PROVIDER=imagekit:
        IMAGEKIT_PRIVATE_KEY
        IMAGEKIT_URL_ENDPOINT
        Opcional multi-cuenta:
            IMAGEKIT_PRIVATE_KEY_2 + IMAGEKIT_URL_ENDPOINT_2
            o listas CSV: IMAGEKIT_PRIVATE_KEYS + IMAGEKIT_URL_ENDPOINTS

    Si CDN_PROVIDER=r2:
        R2_ACCOUNT_ID
        R2_ACCESS_KEY_ID
        R2_SECRET_ACCESS_KEY
        R2_BUCKET
        R2_PUBLIC_BASE_URL (ej: https://pub-xxxx.r2.dev)
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import django
import requests

from cdn_uploader import get_provider, upload_bytes

# Setup Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from django.db.models import Q  # noqa: E402
from cards.models import Card  # noqa: E402

ESC_EDITION_SLUGS = [
    "bushido",
    "sol-naciente",
    "dominio",
    "contraataque",
    "aguila-imperial",
    "steampunk",
    "axis-mundi",
    "hijos-del-sol",
    "legado-gotico",
    "escuelas_elementales",
    "heroes_de_dharma",
]

MAPPING_FILE = "myl_cloudinary_mapping.json"
WSRV_PROXY = "https://wsrv.nl/?url=api.myl.cl/static/cards/{ed_myl_id}/{edid}.png"


def _human_bytes(n: int) -> str:
    value = float(max(0, int(n)))
    units = ["B", "KB", "MB", "GB", "TB"]
    idx = 0
    while value >= 1024 and idx < len(units) - 1:
        value /= 1024
        idx += 1
    return f"{value:.2f} {units[idx]}"


def _is_r2_url(url: str) -> bool:
    value = (url or "").strip().lower()
    if not value:
        return False

    base = (os.environ.get("R2_PUBLIC_BASE_URL") or "").strip().lower().rstrip("/")
    if base and value.startswith(base + "/"):
        return True

    return (".r2.dev/" in value) or (".r2.cloudflarestorage.com/" in value)


def _is_imagekit_url(url: str) -> bool:
    value = (url or "").strip().lower()
    return "ik.imagekit.io/" in value


def _is_cloudinary_url(url: str) -> bool:
    value = (url or "").strip().lower()
    if not value:
        return False

    cloud_name = (os.environ.get("CLOUDINARY_CLOUD_NAME") or "").strip().lower()
    if cloud_name and value.startswith(f"https://res.cloudinary.com/{cloud_name}/"):
        return True

    return "res.cloudinary.com/" in value


def _is_target_url(url: str, provider: str) -> bool:
    if provider == "r2":
        return _is_r2_url(url)
    if provider == "imagekit":
        return _is_imagekit_url(url)
    if provider == "cloudinary":
        return _is_cloudinary_url(url)
    return False


def load_mapping():
    if os.path.exists(MAPPING_FILE):
        with open(MAPPING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_mapping(mapping):
    with open(MAPPING_FILE, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)


def _scope_filter(scope: str, exclude_esc_from_imp_r: bool = False):
    scope = (scope or "all").strip().lower()

    if scope == "imp":
        return Q(edition__format__code="imp")
    if scope == "esc":
        # ESC lives mostly in specific edition slugs under imp_r.
        return Q(edition__slug__in=ESC_EDITION_SLUGS) | Q(edition__format__code="esc")
    if scope == "pe":
        return Q(edition__format__code="pe")
    if scope == "imp_r":
        q = Q(edition__format__code="imp_r")
        if exclude_esc_from_imp_r:
            q &= ~Q(edition__slug__in=ESC_EDITION_SLUGS)
        return q

    # all
    return (
        Q(edition__format__code="imp")
        | Q(edition__format__code="pe")
        | Q(edition__format__code="imp_r")
        | Q(edition__format__code="esc")
        | Q(edition__slug__in=ESC_EDITION_SLUGS)
    )


def get_target_cards(scope: str, exclude_esc_from_imp_r: bool = False):
    qs = (
        Card.objects.filter(_scope_filter(scope, exclude_esc_from_imp_r))
        .exclude(edition__myl_id__startswith="custom_")
        .exclude(myl_id__startswith="custom_")
        .select_related("edition")
        .order_by("edition__slug", "edid")
    )
    return list(
        qs.values("id", "myl_id", "edid", "edition__slug", "edition__myl_id", "name")
    )


def upload_one(card, session):
    """Download from wsrv.nl proxy and upload to configured CDN."""
    ed_slug = card["edition__slug"]
    ed_myl = card["edition__myl_id"]
    edid = card["edid"]
    myl_id = card["myl_id"]

    src_url = WSRV_PROXY.format(ed_myl_id=ed_myl, edid=edid)
    public_id = f"deckshado/myl_cards/{ed_slug}/{edid}"

    try:
        r = session.get(src_url, timeout=30)
        if r.status_code != 200 or not r.content:
            return myl_id, None, f"download failed (status {r.status_code})", 0
        if "image" not in r.headers.get("Content-Type", ""):
            return (
                myl_id,
                None,
                f"not an image (CT={r.headers.get('Content-Type')})",
                0,
            )

        url = upload_bytes(
            r.content,
            public_id=public_id,
            default_ext="png",
            mime_type=r.headers.get("Content-Type", "image/png"),
            overwrite=True,
        )
        return myl_id, url, "OK", len(r.content)
    except Exception as e:
        return myl_id, None, f"ERROR: {e}", 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scope",
        choices=["all", "imp", "esc", "pe", "imp_r"],
        default="all",
        help="Bloque a migrar: imp, esc, pe, imp_r o all",
    )
    parser.add_argument(
        "--exclude-esc-from-imp-r",
        action="store_true",
        help="Cuando --scope imp_r, excluye ediciones de ESC (para migrarlas antes en bloque ESC)",
    )
    parser.add_argument("--dry-run", action="store_true", help="No subir, solo listar")
    parser.add_argument("--limit", type=int, default=None, help="Limitar a N cartas")
    parser.add_argument("--workers", type=int, default=6, help="Concurrencia (default 6)")
    parser.add_argument(
        "--max-ok",
        type=int,
        default=None,
        help="Corte duro por cantidad de subidas exitosas en esta corrida",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=None,
        help="Corte duro por bytes subidos en esta corrida (ej: 2147483648 = 2GB)",
    )
    parser.add_argument(
        "--allow-unbounded",
        action="store_true",
        help="Permite correr sin --max-ok/--max-bytes (NO recomendado)",
    )
    parser.add_argument(
        "--allow-budget-overshoot",
        action="store_true",
        help="Permite workers>1 con topes (puede pasarse levemente por concurrencia)",
    )
    parser.add_argument(
        "--refresh-non-provider",
        action="store_true",
        help="Re-subir cartas cuyo mapping actual NO apunta al proveedor activo",
    )
    parser.add_argument(
        "--refresh-non-r2",
        action="store_true",
        help="(Deprecated) Equivale a --refresh-non-provider",
    )
    parser.add_argument(
        "--refresh-non-imagekit",
        action="store_true",
        help="(Deprecated) Equivale a --refresh-non-provider",
    )
    parser.add_argument(
        "--refresh-cloudinary",
        action="store_true",
        help="(Deprecated) Equivale a --refresh-non-provider",
    )
    parser.add_argument(
        "--refresh-all-mapped",
        action="store_true",
        help="Re-subir todas las cartas del scope aunque ya esten en mapping",
    )
    args = parser.parse_args()

    provider = get_provider()
    if provider not in {"cloudinary", "imagekit", "r2"}:
        print(f"[ERROR] Proveedor no permitido: {provider}")
        print("[ERROR] Define CDN_PROVIDER=cloudinary, imagekit o r2.")
        sys.exit(2)

    cards = get_target_cards(args.scope, args.exclude_esc_from_imp_r)
    print(f"Scope: {args.scope}")
    print(f"Total cartas en scope: {len(cards)}")

    mapping = load_mapping()
    print(f"Mapping previo: {len(mapping)} entries")

    refresh_non_provider = (
        args.refresh_non_provider
        or args.refresh_non_r2
        or args.refresh_non_imagekit
        or args.refresh_cloudinary
    )

    if args.refresh_all_mapped:
        pending = list(cards)
    elif refresh_non_provider:
        pending = [
            c
            for c in cards
            if c["myl_id"] not in mapping
            or not _is_target_url(mapping.get(c["myl_id"], "") or "", provider)
        ]
    else:
        pending = [
            c
            for c in cards
            if c["myl_id"] not in mapping
            or not _is_target_url(mapping.get(c["myl_id"], "") or "", provider)
        ]
    print(f"Pendientes: {len(pending)}")

    if args.limit:
        pending = pending[: args.limit]
        print(f"Limitado a {len(pending)} (--limit)")

    if (
        not args.dry_run
        and not args.allow_unbounded
        and args.max_ok is None
        and args.max_bytes is None
    ):
        print("\n[SAFE MODE] Bloqueado: define al menos un tope para evitar cobros por uso.")
        print("  Recomendado: --max-ok 500 o --max-bytes 1073741824")
        print("  Solo si aceptas riesgo: --allow-unbounded")
        sys.exit(2)

    if (
        not args.allow_budget_overshoot
        and (args.max_ok is not None or args.max_bytes is not None)
        and args.workers != 1
    ):
        print("[SAFE MODE] Ajustando --workers a 1 para respetar topes de forma estricta.")
        args.workers = 1

    if args.dry_run:
        print("\n--- DRY RUN ---")
        for c in pending[:30]:
            print(f"  {c['edition__slug']}/{c['edid']} | {c['name']}")
        if len(pending) > 30:
            print(f"  ... y {len(pending) - 30} mas")
        return

    if not pending:
        print("Nada que hacer.")
        return

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 deckshado-migrator"})

    ok = 0
    fail = 0
    uploaded_bytes = 0
    start = time.time()
    save_every = 50

    aborted_by_limit = False
    ex = ThreadPoolExecutor(max_workers=args.workers)
    try:
        futures = {ex.submit(upload_one, c, session): c for c in pending}
        for i, fut in enumerate(as_completed(futures), 1):
            card = futures[fut]
            myl_id, url, status, bytes_sent = fut.result()
            if url:
                mapping[myl_id] = url
                ok += 1
                uploaded_bytes += bytes_sent
            else:
                fail += 1

            elapsed = time.time() - start
            rate = i / elapsed if elapsed > 0 else 0
            eta = (len(pending) - i) / rate if rate > 0 else 0
            print(
                f"[{i}/{len(pending)}] {card['edition__slug']}/{card['edid']} "
                f"({card['name'][:30]}) {status} | OK={ok} FAIL={fail} "
                f"| BYTES={_human_bytes(uploaded_bytes)} "
                f"| rate={rate:.1f}/s ETA={eta:.0f}s"
            )

            if i % save_every == 0:
                save_mapping(mapping)

            if "upload limit exceeded" in (status or "").lower():
                aborted_by_limit = True
                save_mapping(mapping)
                print("\n[ABORT] Upload limit alcanzado en el proveedor CDN.")
                print("[ABORT] Se guardo checkpoint; reintenta cuando aumente/resetee la cuota.")
                ex.shutdown(wait=False, cancel_futures=True)
                break

            if "cdn guard:" in (status or "").lower():
                aborted_by_limit = True
                save_mapping(mapping)
                print("\n[ABORT] CDN guard activado (kill-switch o presupuesto agotado).")
                print("[ABORT] Se guardo checkpoint para continuar luego sin reprocesar.")
                ex.shutdown(wait=False, cancel_futures=True)
                break

            if args.max_ok is not None and ok >= args.max_ok:
                aborted_by_limit = True
                save_mapping(mapping)
                print(f"\n[ABORT] Tope alcanzado: OK={ok}/{args.max_ok}.")
                ex.shutdown(wait=False, cancel_futures=True)
                break

            if args.max_bytes is not None and uploaded_bytes >= args.max_bytes:
                aborted_by_limit = True
                save_mapping(mapping)
                print(
                    "\n[ABORT] Tope de bytes alcanzado: "
                    f"{_human_bytes(uploaded_bytes)}/{_human_bytes(args.max_bytes)}."
                )
                ex.shutdown(wait=False, cancel_futures=True)
                break
    finally:
        if not aborted_by_limit:
            ex.shutdown(wait=True)

    save_mapping(mapping)
    print(
        f"\n=== Listo: OK={ok} FAIL={fail} "
        f"BYTES={_human_bytes(uploaded_bytes)} en {time.time()-start:.0f}s ==="
    )
    print(f"Mapping guardado en {MAPPING_FILE}")
    print("\nProximo paso: copiar el JSON a PA y correr:")
    print("  python manage.py apply_cloudinary_mapping myl_cloudinary_mapping.json")


if __name__ == "__main__":
    main()
