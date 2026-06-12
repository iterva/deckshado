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
import difflib
import json
import os
import re
import sys
import time
import unicodedata
import urllib3
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
MYL_DIRECT = "https://api.myl.cl/static/cards/{ed_myl_id}/{edid}.png"
PE_SOURCE_MAPPING_FILE = "primera_era_mapping.json"
CARD_EXPLORER_MAPPING_FILE = "card_explorer_mapping.json"
SHADOWBAN_FALLBACK_PATH = os.path.join("backend", "media", "extra_cards", "shdwbn_01.png")

_PE_SOURCE_INDEX: dict[tuple[str, str], str] | None = None
_PE_SOURCE_BY_EDITION: dict[str, list[tuple[str, str]]] | None = None
_PE_CLOUD_INDEX: dict[tuple[str, str], str] | None = None
_PE_CLOUD_BY_EDITION: dict[str, list[tuple[str, str]]] | None = None
_EXPLORER_SOURCE_INDEX: dict[tuple[str, str], str] | None = None
_EXPLORER_SOURCE_BY_EDITION: dict[str, list[tuple[str, str]]] | None = None
_EXPLORER_CLOUD_INDEX: dict[tuple[str, str], str] | None = None
_EXPLORER_CLOUD_BY_EDITION: dict[str, list[tuple[str, str]]] | None = None

# api.myl.cl has an expired certificate; direct fallback runs with verify=False.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


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
    if cloud_name:
        return value.startswith(f"https://res.cloudinary.com/{cloud_name}/")

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


def _normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("�", "")
    text = text.strip().lower()
    # PE variants often include suffixes like "(v2)" while source mapping uses base names.
    text = re.sub(r"\s*\(v\d+\)\s*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    return " ".join(text.split())


def _iter_named_source_entries(node):
    if isinstance(node, dict):
        for key, val in node.items():
            if isinstance(val, dict):
                source_url = (val.get("source_url") or "").strip()
                cloudinary_url = (val.get("cloudinary_url") or "").strip()
                if source_url or cloudinary_url:
                    yield str(key), source_url, cloudinary_url
            yield from _iter_named_source_entries(val)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_named_source_entries(item)


def _edition_candidates(title: str) -> list[str]:
    ed = _normalize_text(title)
    if not ed:
        return []
    candidates = [ed]
    if ed.startswith("pe "):
        tail = ed[3:].strip()
        if tail:
            candidates.append(tail)
    return candidates


def _build_pe_source_index() -> dict[tuple[str, str], str]:
    path = os.path.join(os.path.dirname(__file__), PE_SOURCE_MAPPING_FILE)
    if not os.path.exists(path):
        return {}

    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    global _PE_SOURCE_BY_EDITION, _PE_CLOUD_INDEX, _PE_CLOUD_BY_EDITION
    index: dict[tuple[str, str], str] = {}
    by_edition: dict[str, list[tuple[str, str]]] = {}
    cloud_index: dict[tuple[str, str], str] = {}
    cloud_by_edition: dict[str, list[tuple[str, str]]] = {}
    if not isinstance(raw, dict):
        _PE_CLOUD_INDEX = cloud_index
        _PE_CLOUD_BY_EDITION = cloud_by_edition
        return index

    for edition_title, subtree in raw.items():
        ed_keys = _edition_candidates(edition_title)
        for card_name, source_url, cloudinary_url in _iter_named_source_entries(subtree):
            ck = _normalize_text(card_name)
            if not ck:
                continue
            for ek in ed_keys:
                if source_url:
                    index[(ek, ck)] = source_url
                    by_edition.setdefault(ek, []).append((ck, source_url))
                if cloudinary_url:
                    cloud_index[(ek, ck)] = cloudinary_url
                    cloud_by_edition.setdefault(ek, []).append((ck, cloudinary_url))

    _PE_SOURCE_BY_EDITION = by_edition
    _PE_CLOUD_INDEX = cloud_index
    _PE_CLOUD_BY_EDITION = cloud_by_edition
    return index


def _build_card_explorer_index() -> dict[tuple[str, str], str]:
    path = os.path.join(os.path.dirname(__file__), CARD_EXPLORER_MAPPING_FILE)
    if not os.path.exists(path):
        return {}

    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    global _EXPLORER_SOURCE_BY_EDITION, _EXPLORER_CLOUD_INDEX, _EXPLORER_CLOUD_BY_EDITION
    index: dict[tuple[str, str], str] = {}
    by_edition: dict[str, list[tuple[str, str]]] = {}
    cloud_index: dict[tuple[str, str], str] = {}
    cloud_by_edition: dict[str, list[tuple[str, str]]] = {}
    if not isinstance(raw, dict):
        _EXPLORER_CLOUD_INDEX = cloud_index
        _EXPLORER_CLOUD_BY_EDITION = cloud_by_edition
        return index

    for edition_key, cards in raw.items():
        ed_keys = _edition_candidates(edition_key)
        if not ed_keys or not isinstance(cards, dict):
            continue
        for card_name, payload in cards.items():
            if not isinstance(payload, dict):
                continue
            source_url = (payload.get("source_url") or "").strip()
            cloudinary_url = (payload.get("cloudinary_url") or "").strip()
            ck = _normalize_text(card_name)
            if not ck:
                continue
            for ek in ed_keys:
                if source_url:
                    index[(ek, ck)] = source_url
                    by_edition.setdefault(ek, []).append((ck, source_url))
                if cloudinary_url:
                    cloud_index[(ek, ck)] = cloudinary_url
                    cloud_by_edition.setdefault(ek, []).append((ck, cloudinary_url))

    _EXPLORER_SOURCE_BY_EDITION = by_edition
    _EXPLORER_CLOUD_INDEX = cloud_index
    _EXPLORER_CLOUD_BY_EDITION = cloud_by_edition
    return index


def _get_pe_source_url(edition_title: str, card_name: str, edition_slug: str = "") -> str:
    global _PE_SOURCE_INDEX, _PE_SOURCE_BY_EDITION, _PE_CLOUD_INDEX, _PE_CLOUD_BY_EDITION
    global _EXPLORER_SOURCE_INDEX, _EXPLORER_SOURCE_BY_EDITION, _EXPLORER_CLOUD_INDEX, _EXPLORER_CLOUD_BY_EDITION
    if _PE_SOURCE_INDEX is None:
        _PE_SOURCE_INDEX = _build_pe_source_index()
    if _EXPLORER_SOURCE_INDEX is None:
        _EXPLORER_SOURCE_INDEX = _build_card_explorer_index()

    name = _normalize_text(card_name)
    ed_candidates: list[str] = []
    for raw_value in [edition_title, edition_slug]:
        for ek in _edition_candidates(raw_value):
            if ek and ek not in ed_candidates:
                ed_candidates.append(ek)
    if not ed_candidates or not name:
        return ""

    def _lookup(
        source_index: dict[tuple[str, str], str],
        source_by_edition: dict[str, list[tuple[str, str]]],
    ) -> str:
        for ek in ed_candidates:
            exact = source_index.get((ek, name), "")
            if exact:
                return exact

        best_ratio = 0.0
        best_url = ""
        for ek in ed_candidates:
            for candidate_name, candidate_url in source_by_edition.get(ek, []):
                ratio = difflib.SequenceMatcher(a=name, b=candidate_name).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_url = candidate_url
        if best_ratio >= 0.78:
            return best_url
        return ""

    if _PE_SOURCE_INDEX:
        url = _lookup(_PE_SOURCE_INDEX, _PE_SOURCE_BY_EDITION or {})
        if url:
            return url

    if _EXPLORER_SOURCE_INDEX:
        url = _lookup(_EXPLORER_SOURCE_INDEX, _EXPLORER_SOURCE_BY_EDITION or {})
        if url:
            return url

    # Last resort: old Cloudinary URLs from the PE mapping.
    cloud_index = _PE_CLOUD_INDEX or {}
    cloud_by_edition = _PE_CLOUD_BY_EDITION or {}
    cloud_url = _lookup(cloud_index, cloud_by_edition)
    if cloud_url:
        return cloud_url

    explorer_cloud_index = _EXPLORER_CLOUD_INDEX or {}
    explorer_cloud_by_edition = _EXPLORER_CLOUD_BY_EDITION or {}
    cloud_url = _lookup(explorer_cloud_index, explorer_cloud_by_edition)
    if cloud_url:
        return cloud_url
    return ""


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
        qs.values(
            "id",
            "myl_id",
            "edid",
            "edition__slug",
            "edition__myl_id",
            "edition__title",
            "name",
            "custom_image_url",
        )
    )


def upload_one(card, session):
    """Download from wsrv.nl proxy and upload to configured CDN."""
    ed_slug = card["edition__slug"]
    ed_myl = card["edition__myl_id"]
    edid = card["edid"]
    myl_id = card["myl_id"]
    edition_title = card.get("edition__title") or ""
    card_name = card.get("name") or ""
    existing_url = (card.get("custom_image_url") or "").strip()

    card_code = (edid or "").strip() or (myl_id or "").strip()
    if not card_code:
        return myl_id, None, "missing card code (edid/myl_id)", 0

    public_id = f"deckshado/myl_cards/{ed_slug}/{card_code}"

    # Default source from MYL static endpoint (proxied via wsrv).
    src_url = ""
    direct_url = ""
    if (edid or "").strip():
        src_url = WSRV_PROXY.format(ed_myl_id=ed_myl, edid=edid)
        direct_url = MYL_DIRECT.format(ed_myl_id=ed_myl, edid=edid)
    elif (myl_id or "").strip() and not str(myl_id).startswith("pe_"):
        src_url = WSRV_PROXY.format(ed_myl_id=ed_myl, edid=myl_id)
        direct_url = MYL_DIRECT.format(ed_myl_id=ed_myl, edid=myl_id)

    def _download(url: str, verify_ssl: bool = True):
        r = session.get(url, timeout=30, verify=verify_ssl)
        if r.status_code != 200 or not r.content:
            return None, f"download failed (status {r.status_code})"
        if "image" not in r.headers.get("Content-Type", ""):
            return None, f"not an image (CT={r.headers.get('Content-Type')})"
        return r, "OK"

    try:
        r = None
        first_error = "download failed"
        if src_url:
            r, first_error = _download(src_url)

        # wsrv.nl may return Cloudflare 403; fallback to direct MYL URL.
        if r is None and direct_url:
            r, _ = _download(direct_url, verify_ssl=False)

        # PE fallback: source_url from primera_era_mapping.json by edition title + card name.
        if r is None and str(myl_id).startswith("pe_"):
            pe_source_url = _get_pe_source_url(edition_title, card_name, ed_slug)
            if pe_source_url:
                r, _ = _download(pe_source_url)

        # Last fallback: rehost the existing DB image URL if present.
        if r is None and existing_url:
            r, _ = _download(existing_url)

        # Final fallback for legacy shadow-ban placeholders: use local backup asset.
        if r is None and _normalize_text(card_name) == "shadow ban":
            local_shadowban = os.path.join(os.path.dirname(__file__), SHADOWBAN_FALLBACK_PATH)
            if os.path.exists(local_shadowban):
                with open(local_shadowban, "rb") as fh:
                    data = fh.read()
                url = upload_bytes(
                    data,
                    public_id=public_id,
                    default_ext="png",
                    mime_type="image/png",
                    overwrite=True,
                )
                return myl_id, url, "OK(local shadow-ban)", len(data)

        if r is None:
            return myl_id, None, first_error, 0

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
