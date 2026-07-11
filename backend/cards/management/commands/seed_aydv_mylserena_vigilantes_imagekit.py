"""
Seed/upload de cartas AYDV desde categorias de mylserena Vigilantes.

Flujo:
1) Scrapea categorias + paginacion en mylserena.
2) Compara contra cartas de la edicion AYDV por (nombre normalizado + rareza).
3) Sube solo faltantes a ImageKit.
4) Crea cartas nuevas en BD intentando heredar coste/fuerza/descripcion desde cartas existentes.

Uso:
  python manage.py seed_aydv_mylserena_vigilantes_imagekit --dry-run
  python manage.py seed_aydv_mylserena_vigilantes_imagekit
  python manage.py seed_aydv_mylserena_vigilantes_imagekit --limit 10
    python manage.py seed_aydv_mylserena_vigilantes_imagekit --apply-mapping-only
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand, CommandError

from cards.models import Card, Edition, Format, Rarity


UPLOAD_ENDPOINT = "https://upload.imagekit.io/api/v1/files/upload"
DEFAULT_ENV_FILE = Path(__file__).resolve().parents[5] / ".env_imagekit"
DEFAULT_FOLDER = "/deckshado/myl_cards/aydv_mylserena_vigilantes_2026_07"
DEFAULT_MAPPING_FILE = Path(__file__).resolve().parents[4] / "aydv_mylserena_vigilantes_imagekit_mapping.json"


@dataclass(frozen=True)
class CategoryConfig:
    slug: str
    url: str
    rarity_slug: str
    rarity_code: str


CATEGORIES: tuple[CategoryConfig, ...] = (
    CategoryConfig("legendarias", "https://mylserena.cl/singles-imperio/vigilantes/legendarias", "legendaria", "L"),
    CategoryConfig("promocionales", "https://mylserena.cl/singles-imperio/vigilantes/promocionales", "promo", "P"),
    CategoryConfig("reales", "https://mylserena.cl/singles-imperio/vigilantes/reales", "real", "R"),
    CategoryConfig("ultra-reales", "https://mylserena.cl/singles-imperio/vigilantes/ultra-reales", "ultra-real", "U"),
    CategoryConfig("mega-reales", "https://mylserena.cl/singles-imperio/vigilantes/mega-reales", "mega-real", "M"),
    CategoryConfig("cortesanas-foil", "https://mylserena.cl/singles-imperio/vigilantes/cortesanas-foil", "cortesano", "C"),
    CategoryConfig("vasallas-foil", "https://mylserena.cl/singles-imperio/vigilantes/vasallas-foil", "vasallo", "V"),
)


def _parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        raise CommandError(f"No existe env file: {path}")

    env_map: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env_map[key.strip()] = value.strip().strip('"').strip("'")
    return env_map


def _build_auth(env_map: dict[str, str]) -> tuple[str, str]:
    private_key = (env_map.get("IMAGEKIT_PRIVATE_KEY") or env_map.get("private_key") or "").strip()
    if not private_key:
        raise CommandError("No se encontro IMAGEKIT_PRIVATE_KEY/private_key en el env file")
    return private_key, ""


def _normalize_name(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"\s*\([^)]*\)\s*$", "", text.strip())
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text).strip().lower()
    return re.sub(r"\s+", " ", text)


def _slugify(value: str) -> str:
    base = _normalize_name(value).replace(" ", "-")
    return re.sub(r"-+", "-", base).strip("-") or "carta"


def _extract_base_name(raw_name: str) -> str:
    name = (raw_name or "").strip()
    name = re.sub(r"^Ir a\s+", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()
    return name


def _image_ext_from_url(url: str) -> str:
    path = urlparse(url).path.lower()
    match = re.search(r"(\.jpe?g|\.png|\.webp|\.gif)$", path)
    return match.group(1) if match else ".jpg"


def _score_candidate(card: Card) -> int:
    score = 0
    score += 2 if card.cost else 0
    score += 2 if card.damage else 0
    score += 3 if card.ability else 0
    score += 1 if card.flavour else 0
    score += 1 if card.card_type_id else 0
    score += 1 if card.race_id else 0
    return score


class Command(BaseCommand):
    help = "Scrapea categorias Vigilantes en mylserena, sube faltantes a ImageKit y crea cartas AYDV"

    def add_arguments(self, parser):
        parser.add_argument(
            "--env-file",
            default=str(DEFAULT_ENV_FILE),
            help="Archivo con credenciales de ImageKit",
        )
        parser.add_argument(
            "--folder",
            default=DEFAULT_FOLDER,
            help="Folder destino en ImageKit",
        )
        parser.add_argument(
            "--mapping-file",
            default=str(DEFAULT_MAPPING_FILE),
            help="Ruta de salida para mapping JSON",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="No sube ni crea cartas. Solo muestra y genera mapping simulado",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Limita la cantidad de faltantes a procesar (0 = todos)",
        )
        parser.add_argument(
            "--apply-mapping-only",
            action="store_true",
            help="No scrapea ni sube: aplica cartas desde mapping JSON (ideal para PythonAnywhere)",
        )

    def _ensure_edition(self) -> Edition:
        imp_format, _ = Format.objects.get_or_create(
            code="imp",
            defaults={"name": "Imperio"},
        )

        edition, _ = Edition.objects.update_or_create(
            myl_id="custom_aydv",
            defaults={
                "slug": "aydv",
                "title": "Angeles y Demonios: Vigilantes",
                "format": imp_format,
                "active": True,
            },
        )
        return edition

    def _scrape_category(self, session: requests.Session, category: CategoryConfig) -> list[dict]:
        visited: set[str] = set()
        queue: list[str] = [category.url]
        items: list[dict] = []

        while queue:
            page_url = queue.pop(0)
            if page_url in visited:
                continue
            visited.add(page_url)

            response = session.get(page_url, timeout=45)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            for anchor in soup.select("a.product-block__anchor"):
                href = (anchor.get("href") or "").strip()
                if not href:
                    continue
                raw_name = (anchor.get("title") or "").strip()
                name = _extract_base_name(raw_name)
                if not name:
                    continue

                img = anchor.select_one("img")
                listing_img_url = ""
                if img is not None:
                    listing_img_url = (
                        (img.get("data-src") or "").strip()
                        or (img.get("src") or "").strip()
                    )

                items.append(
                    {
                        "name": name,
                        "name_normalized": _normalize_name(name),
                        "product_url": urljoin(page_url, href),
                        "listing_image_url": urljoin(page_url, listing_img_url) if listing_img_url else "",
                        "category_slug": category.slug,
                        "rarity_slug": category.rarity_slug,
                        "rarity_code": category.rarity_code,
                    }
                )

            for pagination_link in soup.select('a[href*="?page="], a[href*="&page="]'):
                href = (pagination_link.get("href") or "").strip()
                if not href:
                    continue
                target = urljoin(page_url, href)
                if "/singles-imperio/vigilantes/" not in target:
                    continue
                if category.slug not in target:
                    continue
                if target not in visited and target not in queue:
                    queue.append(target)

        dedup: dict[tuple[str, str], dict] = {}
        for item in items:
            key = (item["name_normalized"], item["product_url"])
            dedup[key] = item
        return list(dedup.values())

    def _resolve_source_image_url(self, session: requests.Session, item: dict) -> str:
        product_url = item["product_url"]
        response = session.get(product_url, timeout=45)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        meta = soup.find("meta", attrs={"property": "og:image"})
        if meta and (meta.get("content") or "").strip():
            return urljoin(product_url, meta.get("content").strip())

        if item.get("listing_image_url"):
            return item["listing_image_url"]

        raise CommandError(f"No se pudo resolver imagen para {item['name']} ({product_url})")

    def _build_existing_key_index(self, edition: Edition) -> set[tuple[str, str]]:
        key_set: set[tuple[str, str]] = set()
        cards = Card.objects.filter(edition=edition).select_related("rarity")
        for card in cards:
            rarity_slug = card.rarity.slug if card.rarity else ""
            key_set.add((_normalize_name(card.name), rarity_slug))
        return key_set

    def _build_candidate_indexes(self, edition: Edition) -> tuple[dict[str, list[Card]], dict[str, list[Card]]]:
        all_cards = list(
            Card.objects.select_related("edition", "rarity", "card_type", "race")
            .all()
            .order_by("id")
        )

        by_norm_global: dict[str, list[Card]] = {}
        by_norm_aydv: dict[str, list[Card]] = {}

        for card in all_cards:
            norm = _normalize_name(card.name)
            by_norm_global.setdefault(norm, []).append(card)
            if card.edition_id == edition.id:
                by_norm_aydv.setdefault(norm, []).append(card)

        return by_norm_aydv, by_norm_global

    def _pick_best_source(self, norm_name: str, by_norm_aydv: dict[str, list[Card]], by_norm_global: dict[str, list[Card]]) -> Card | None:
        candidates = by_norm_aydv.get(norm_name) or by_norm_global.get(norm_name) or []
        if not candidates:
            return None
        return sorted(candidates, key=_score_candidate, reverse=True)[0]

    def _next_series_indexes(self, edition: Edition) -> dict[str, int]:
        series: dict[str, int] = {cfg.rarity_code: 0 for cfg in CATEGORIES}
        pattern = re.compile(r"^AYDV-X([A-Z])(\d{3})$")

        for edid in Card.objects.filter(edition=edition).values_list("edid", flat=True):
            match = pattern.match(edid or "")
            if not match:
                continue
            code, number_text = match.groups()
            number = int(number_text)
            if code in series and number > series[code]:
                series[code] = number
        return series

    def _allocate_ids(
        self,
        rarity_code: str,
        series_index: dict[str, int],
        used_edids: set[str],
        used_myl_ids: set[str],
    ) -> tuple[str, str]:
        index = series_index.get(rarity_code, 0)
        while True:
            index += 1
            edid = f"AYDV-X{rarity_code}{index:03d}"
            myl_id = f"custom_aydv_x{rarity_code.lower()}{index:03d}"
            if edid not in used_edids and myl_id not in used_myl_ids:
                series_index[rarity_code] = index
                used_edids.add(edid)
                used_myl_ids.add(myl_id)
                return edid, myl_id

    def _upload_imagekit(
        self,
        session: requests.Session,
        auth: tuple[str, str],
        folder: str,
        file_name: str,
        source_image_url: str,
    ) -> str:
        response = session.post(
            UPLOAD_ENDPOINT,
            auth=auth,
            data={
                "file": source_image_url,
                "fileName": file_name,
                "folder": folder,
                "useUniqueFileName": "false",
                "overwriteFile": "true",
                "isPrivateFile": "false",
            },
            timeout=120,
        )
        if response.status_code >= 300:
            raise CommandError(
                f"ImageKit fallo ({response.status_code}) para {file_name}: {response.text[:500]}"
            )
        payload = response.json()
        imagekit_url = (payload.get("url") or "").strip()
        if not imagekit_url:
            raise CommandError(f"ImageKit no devolvio url para {file_name}")
        return imagekit_url

    def _load_mapping_records(self, mapping_file: Path) -> list[dict]:
        if not mapping_file.exists():
            raise CommandError(f"No existe mapping file: {mapping_file}")

        try:
            payload = json.loads(mapping_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CommandError(f"JSON invalido en mapping file: {exc}") from exc

        records = payload.get("records")
        if not isinstance(records, list):
            raise CommandError("El mapping no contiene lista valida en 'records'.")
        return records

    def _build_card_payload(
        self,
        edition: Edition,
        rarity: Rarity,
        name: str,
        myl_id: str,
        edid: str,
        imagekit_url: str,
        source_card: Card | None,
    ) -> dict:
        ability = source_card.ability if source_card else None
        flavour = source_card.flavour if source_card else None
        if not ability and not flavour:
            flavour = "Carta cargada desde mapping de mylserena Vigilantes."

        return {
            "myl_id": myl_id,
            "edid": edid,
            "slug": f"{_slugify(name)}-{edid.lower()}",
            "name": name,
            "edition": edition,
            "rarity": rarity,
            "race": source_card.race if source_card else None,
            "card_type": source_card.card_type if source_card else None,
            "cost": source_card.cost if source_card else None,
            "damage": source_card.damage if source_card else None,
            "ability": ability,
            "flavour": flavour,
            "custom_image_url": imagekit_url,
        }

    def _apply_mapping_only(
        self,
        edition: Edition,
        rarity_by_slug: dict[str, Rarity],
        mapping_file: Path,
        dry_run: bool,
    ) -> None:
        records = self._load_mapping_records(mapping_file)
        by_norm_aydv, by_norm_global = self._build_candidate_indexes(edition)

        created = 0
        updated = 0
        kept = 0
        failed = 0

        self.stdout.write(self.style.MIGRATE_HEADING("Aplicando mapping JSON en AYDV..."))

        for idx, rec in enumerate(records, start=1):
            if not isinstance(rec, dict):
                failed += 1
                self.stdout.write(self.style.ERROR(f"  [{idx}] FAIL registro invalido"))
                continue

            status = (rec.get("status") or "").strip().lower()
            if status == "error":
                failed += 1
                self.stdout.write(self.style.ERROR(f"  [{idx}] FAIL en mapping: {rec.get('name') or '<sin-nombre>'}"))
                continue

            name = (rec.get("name") or "").strip()
            rarity_slug = (rec.get("rarity_slug") or "").strip()
            imagekit_url = (rec.get("imagekit_url") or "").strip()
            myl_id = (rec.get("myl_id") or "").strip()
            edid = (rec.get("edid") or "").strip()

            if not name or not rarity_slug or not imagekit_url or not myl_id or not edid:
                failed += 1
                self.stdout.write(self.style.ERROR(f"  [{idx}] FAIL campos requeridos incompletos"))
                continue

            rarity = rarity_by_slug.get(rarity_slug)
            if rarity is None:
                failed += 1
                self.stdout.write(self.style.ERROR(f"  [{idx}] FAIL rarity inexistente: {rarity_slug}"))
                continue

            source_ref = (rec.get("source_card") or "").strip()
            source_card = Card.objects.filter(myl_id=source_ref).first() if source_ref else None
            if source_card is None:
                source_card = self._pick_best_source(_normalize_name(name), by_norm_aydv, by_norm_global)

            defaults = self._build_card_payload(
                edition=edition,
                rarity=rarity,
                name=name,
                myl_id=myl_id,
                edid=edid,
                imagekit_url=imagekit_url,
                source_card=source_card,
            )

            card = Card.objects.filter(myl_id=myl_id).first()
            if card is None:
                card = Card.objects.filter(edition=edition, edid=edid).order_by("id").first()

            if card is None:
                if dry_run:
                    created += 1
                    self.stdout.write(f"  [{idx}] DRY_CREATE {name} -> {edid}")
                else:
                    Card.objects.create(**defaults)
                    created += 1
                    self.stdout.write(f"  [{idx}] CREATE {name} -> {edid}")
                continue

            changed_fields: list[str] = []
            for key, value in defaults.items():
                current = getattr(card, key)
                if current != value:
                    setattr(card, key, value)
                    changed_fields.append(key)

            if not changed_fields:
                kept += 1
                self.stdout.write(f"  [{idx}] KEEP {name} -> {edid}")
                continue

            if dry_run:
                updated += 1
                self.stdout.write(f"  [{idx}] DRY_UPDATE {name} -> {edid}")
            else:
                card.save(update_fields=changed_fields)
                updated += 1
                self.stdout.write(f"  [{idx}] UPDATE {name} -> {edid}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Done apply-mapping-only. Created={created} Updated={updated} Kept={kept} Failed={failed}"
            )
        )

    def handle(self, *args, **options):
        env_file = Path(options["env_file"]).expanduser().resolve()
        folder = str(options["folder"]).strip() or DEFAULT_FOLDER
        mapping_file = Path(options["mapping_file"]).expanduser().resolve()
        dry_run = bool(options["dry_run"])
        apply_mapping_only = bool(options["apply_mapping_only"])
        limit = int(options["limit"] or 0)
        if limit < 0:
            raise CommandError("--limit no puede ser negativo")

        edition = self._ensure_edition()
        rarity_by_slug = {r.slug: r for r in Rarity.objects.all()}

        if apply_mapping_only:
            self._apply_mapping_only(
                edition=edition,
                rarity_by_slug=rarity_by_slug,
                mapping_file=mapping_file,
                dry_run=dry_run,
            )
            return

        session = requests.Session()
        session.headers.update({"User-Agent": "Mozilla/5.0 (DeckshadowSeed/1.0)"})

        self.stdout.write(self.style.MIGRATE_HEADING("Scrapeando categorias Vigilantes de mylserena..."))
        scraped: list[dict] = []
        for category in CATEGORIES:
            rows = self._scrape_category(session, category)
            scraped.extend(rows)
            self.stdout.write(f"  {category.slug}: {len(rows)} filas")

        dedup_by_key: dict[tuple[str, str], dict] = {}
        for item in scraped:
            key = (item["name_normalized"], item["rarity_slug"])
            dedup_by_key.setdefault(key, item)

        existing_keys = self._build_existing_key_index(edition)
        missing = [item for key, item in dedup_by_key.items() if key not in existing_keys]
        missing.sort(key=lambda x: (x["rarity_slug"], x["name_normalized"]))

        if limit:
            missing = missing[:limit]

        if not missing:
            self.stdout.write(self.style.SUCCESS("No hay cartas faltantes para crear."))
            return

        self.stdout.write(
            self.style.WARNING(
                f"Faltantes detectadas: {len(missing)} (de {len(dedup_by_key)} unicas por nombre+rareza)"
            )
        )

        by_norm_aydv, by_norm_global = self._build_candidate_indexes(edition)
        series_index = self._next_series_indexes(edition)
        used_edids = set(Card.objects.filter(edition=edition).values_list("edid", flat=True))
        used_myl_ids = set(Card.objects.values_list("myl_id", flat=True))

        if not dry_run:
            env_map = _parse_env_file(env_file)
            imagekit_auth = _build_auth(env_map)
        else:
            imagekit_auth = ("", "")

        results: list[dict] = []
        created = 0
        failed = 0

        for idx, item in enumerate(missing, start=1):
            name = item["name"]
            rarity_slug = item["rarity_slug"]
            rarity_code = item["rarity_code"]
            norm_name = item["name_normalized"]

            rarity = rarity_by_slug.get(rarity_slug)
            if rarity is None:
                self.stdout.write(self.style.WARNING(f"  SKIP sin rarity '{rarity_slug}' para {name}"))
                failed += 1
                continue

            try:
                source_image_url = self._resolve_source_image_url(session, item)
                ext = _image_ext_from_url(source_image_url)
                source_card = self._pick_best_source(norm_name, by_norm_aydv, by_norm_global)
                edid, myl_id = self._allocate_ids(rarity_code, series_index, used_edids, used_myl_ids)

                public_id = f"{_slugify(name)}_{rarity_slug}_{edid.lower()}"
                file_name = f"{public_id}{ext}"

                if dry_run:
                    imagekit_url = f"https://ik.imagekit.io/<cloud>/{folder.strip('/')}/{file_name}"
                else:
                    imagekit_url = self._upload_imagekit(
                        session=session,
                        auth=imagekit_auth,
                        folder=folder,
                        file_name=file_name,
                        source_image_url=source_image_url,
                    )

                card_payload = self._build_card_payload(
                    edition=edition,
                    rarity=rarity,
                    name=name,
                    myl_id=myl_id,
                    edid=edid,
                    imagekit_url=imagekit_url,
                    source_card=source_card,
                )

                if not dry_run:
                    Card.objects.create(**card_payload)

                created += 1
                results.append(
                    {
                        "status": "created" if not dry_run else "would_create",
                        "name": name,
                        "category_slug": item["category_slug"],
                        "rarity_slug": rarity_slug,
                        "product_url": item["product_url"],
                        "source_image_url": source_image_url,
                        "imagekit_url": imagekit_url,
                        "myl_id": myl_id,
                        "edid": edid,
                        "source_card": source_card.myl_id if source_card else None,
                        "copied_cost": source_card.cost if source_card else None,
                        "copied_damage": source_card.damage if source_card else None,
                    }
                )

                self.stdout.write(
                    f"  [{idx}/{len(missing)}] {'DRY' if dry_run else 'OK'} {name} ({rarity_slug}) -> {edid}"
                )
            except Exception as exc:  # noqa: BLE001
                failed += 1
                results.append(
                    {
                        "status": "error",
                        "name": name,
                        "category_slug": item["category_slug"],
                        "rarity_slug": rarity_slug,
                        "product_url": item["product_url"],
                        "error": str(exc),
                    }
                )
                self.stdout.write(self.style.ERROR(f"  [{idx}/{len(missing)}] FAIL {name}: {exc}"))

        output = {
            "kind": "aydv_mylserena_vigilantes_imagekit",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "folder": folder,
            "dry_run": dry_run,
            "summary": {
                "scraped_rows": len(scraped),
                "unique_name_rarity": len(dedup_by_key),
                "missing_processed": len(missing),
                "created": created,
                "failed": failed,
            },
            "records": results,
        }

        mapping_file.write_text(
            json.dumps(output, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        if failed:
            self.stdout.write(
                self.style.WARNING(
                    f"Finalizado con errores. Created={created} Failed={failed} Mapping={mapping_file}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Done. Created={created} Failed={failed} Mapping={mapping_file}"
                )
            )
