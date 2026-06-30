from __future__ import annotations

import importlib.util
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from riftbound.models import RiftboundCard


@dataclass(slots=True)
class Counters:
    scanned: int = 0
    linked: int = 0
    uploaded: int = 0
    unchanged: int = 0
    skipped: int = 0
    errors: int = 0


class Command(BaseCommand):
    help = "Seed: migra solo Riftbound con cdn_image_url en Cloudinary hacia ImageKit usando fuente API."

    def add_arguments(self, parser):
        parser.add_argument("--set", default="", help="Filtra por set code (ej: OGN).")
        parser.add_argument("--start-from", default="", help="Empieza desde card_number >= valor.")
        parser.add_argument("--limit", type=int, default=0, help="Limite de cartas (0 = sin limite).")
        parser.add_argument(
            "--active-only",
            action="store_true",
            help="Procesa solo cartas activas (por defecto migra todas las que apunten a Cloudinary).",
        )

        parser.add_argument("--api-size", type=int, default=100, help="Tamano de pagina Riftcodex (1..100).")
        parser.add_argument("--api-timeout", type=int, default=30, help="Timeout API Riftcodex (seg).")
        parser.add_argument(
            "--skip-api",
            action="store_true",
            help="Omite consulta a Riftcodex y usa solo image_url local como fuente.",
        )
        parser.add_argument(
            "--ignore-env-proxy",
            action="store_true",
            help="Ignora variables de proxy del entorno para requests salientes.",
        )
        parser.add_argument("--head-timeout", type=int, default=10, help="Timeout HEAD (seg).")
        parser.add_argument("--download-timeout", type=int, default=40, help="Timeout descarga imagen (seg).")

        parser.add_argument(
            "--imagekit-url-endpoint",
            default="",
            help="Opcional: setea IMAGEKIT_URL_ENDPOINT para esta corrida.",
        )
        parser.add_argument(
            "--imagekit-private-key",
            default="",
            help="Opcional: setea IMAGEKIT_PRIVATE_KEY para esta corrida.",
        )

        parser.add_argument("--dry-run", action="store_true", help="No guarda en BD ni sube archivos.")

    def handle(self, *args, **opts):
        dry_run = bool(opts.get("dry_run"))
        self._prepare_imagekit_env(opts)

        endpoints = self._imagekit_endpoints()
        self.stdout.write(f"ImageKit endpoints activos: {len(endpoints)}")
        for ep in endpoints:
            self.stdout.write(f"  - {ep}")

        qs = RiftboundCard.objects.filter(cdn_image_url__icontains="cloudinary").select_related("set")
        if bool(opts.get("active_only")):
            qs = qs.filter(is_active=True)
        qs = qs.order_by("card_number")

        set_code = (opts.get("set") or "").strip().upper()
        if set_code:
            qs = qs.filter(set__code=set_code)

        start_from = (opts.get("start_from") or "").strip()
        if start_from:
            qs = qs.filter(card_number__gte=start_from)

        limit = max(0, int(opts.get("limit") or 0))
        cards = list(qs[:limit] if limit else qs)
        total = len(cards)
        if total == 0:
            self.stdout.write(self.style.WARNING("No hay cartas Cloudinary para migrar."))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING("Modo dry-run activo (sin persistencia ni upload)."))

        self.stdout.write(f"Cartas objetivo (cloudinary): {total}")

        session = requests.Session()
        session.headers.update({"User-Agent": "deckshado-riftbound-cloudinary-to-imagekit/1.0"})
        if bool(opts.get("ignore_env_proxy")):
            session.trust_env = False

        api_map: dict[str, str] = {}
        if bool(opts.get("skip_api")):
            self.stdout.write(self.style.WARNING("Riftcodex API omitida por --skip-api; usando image_url local."))
        else:
            api_size = max(1, min(100, int(opts.get("api_size") or 100)))
            api_timeout = max(5, int(opts.get("api_timeout") or 30))
            try:
                api_map = self._fetch_riftcodex_image_map(session=session, page_size=api_size, timeout=api_timeout)
                self.stdout.write(f"Mapa API cargado: {len(api_map)} entradas.")
            except Exception as exc:
                self.stdout.write(
                    self.style.WARNING(
                        "No se pudo consultar Riftcodex API; continuando con image_url local. "
                        f"Detalle: {exc}"
                    )
                )

        candidate_public_urls, upload_bytes = self._load_cdn_helpers()
        head_timeout = max(3, int(opts.get("head_timeout") or 10))
        download_timeout = max(5, int(opts.get("download_timeout") or 40))

        counters = Counters()
        for idx, card in enumerate(cards, start=1):
            counters.scanned += 1

            sources = self._source_candidates(card=card, api_map=api_map)
            if not sources:
                counters.skipped += 1
                continue

            source_url = sources[0]

            public_id = self._public_id_for_card(card)
            ext_candidates = self._candidate_exts(source_url)

            linked_url = self._find_existing_imagekit_url(
                session=session,
                candidate_public_urls=candidate_public_urls,
                public_id=public_id,
                ext_candidates=ext_candidates,
                timeout=head_timeout,
            )
            if linked_url:
                if card.cdn_image_url == linked_url:
                    counters.unchanged += 1
                else:
                    counters.linked += 1
                    if not dry_run:
                        card.cdn_image_url = linked_url
                        card.save(update_fields=["cdn_image_url"])
                if idx % 50 == 0:
                    self.stdout.write(
                        f"  [{idx}/{total}] linked={counters.linked} uploaded={counters.uploaded} "
                        f"skip={counters.skipped} errors={counters.errors}"
                    )
                continue

            if dry_run:
                counters.uploaded += 1
                if idx % 50 == 0:
                    self.stdout.write(
                        f"  [{idx}/{total}] linked={counters.linked} uploaded={counters.uploaded} "
                        f"skip={counters.skipped} errors={counters.errors}"
                    )
                continue

            last_error = None
            migrated = False
            for source_url in sources:
                try:
                    resp = session.get(source_url, timeout=download_timeout)
                    resp.raise_for_status()

                    ext = self._guess_ext(source_url, resp.headers.get("Content-Type", ""))
                    cdn_url = upload_bytes(
                        resp.content,
                        public_id=public_id,
                        default_ext=ext,
                        mime_type=resp.headers.get("Content-Type", "application/octet-stream"),
                        overwrite=True,
                    )
                    if card.cdn_image_url != cdn_url:
                        card.cdn_image_url = cdn_url
                        card.save(update_fields=["cdn_image_url"])
                    counters.uploaded += 1
                    migrated = True
                    break
                except Exception as exc:
                    last_error = exc

            if not migrated:
                counters.errors += 1
                self.stdout.write(self.style.WARNING(f"[{card.card_number}] error: {last_error}"))

            if idx % 50 == 0:
                self.stdout.write(
                    f"  [{idx}/{total}] linked={counters.linked} uploaded={counters.uploaded} "
                    f"skip={counters.skipped} errors={counters.errors}"
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Resumen: "
                f"scanned={counters.scanned}, linked={counters.linked}, uploaded={counters.uploaded}, "
                f"unchanged={counters.unchanged}, skipped={counters.skipped}, errors={counters.errors}."
            )
        )

    @staticmethod
    def _prepare_imagekit_env(opts: dict) -> None:
        os.environ["CDN_PROVIDER"] = "imagekit"

        endpoint = (opts.get("imagekit_url_endpoint") or "").strip()
        private_key = (opts.get("imagekit_private_key") or "").strip()
        if endpoint:
            os.environ["IMAGEKIT_URL_ENDPOINT"] = endpoint.rstrip("/")
        if private_key:
            os.environ["IMAGEKIT_PRIVATE_KEY"] = private_key

        has_pair = bool(os.environ.get("IMAGEKIT_PRIVATE_KEY") and os.environ.get("IMAGEKIT_URL_ENDPOINT"))
        has_csv = bool(os.environ.get("IMAGEKIT_PRIVATE_KEYS") and os.environ.get("IMAGEKIT_URL_ENDPOINTS"))
        if not (has_pair or has_csv):
            raise CommandError(
                "Faltan credenciales de ImageKit. Define IMAGEKIT_PRIVATE_KEY + IMAGEKIT_URL_ENDPOINT "
                "(o IMAGEKIT_PRIVATE_KEYS + IMAGEKIT_URL_ENDPOINTS)."
            )

    @staticmethod
    def _imagekit_endpoints() -> list[str]:
        out: list[str] = []
        primary = (os.environ.get("IMAGEKIT_URL_ENDPOINT") or "").strip().rstrip("/")
        if primary:
            out.append(primary)

        csv_values = (os.environ.get("IMAGEKIT_URL_ENDPOINTS") or "").strip()
        if csv_values:
            for value in csv_values.split(","):
                clean = value.strip().rstrip("/")
                if clean and clean not in out:
                    out.append(clean)

        return out

    def _fetch_riftcodex_image_map(self, session: requests.Session, page_size: int, timeout: int) -> dict[str, str]:
        out: dict[str, str] = {}
        page = 1
        while True:
            res = session.get(
                "https://api.riftcodex.com/cards",
                params={"page": page, "size": page_size},
                timeout=timeout,
            )
            res.raise_for_status()
            payload = res.json()

            items = payload.get("items") or []
            for item in items:
                if not isinstance(item, dict):
                    continue
                image_url = ((item.get("media") or {}).get("image_url") or "").strip()
                if not image_url:
                    continue
                for card_number in self._card_numbers_from_api(item):
                    out[card_number] = image_url

            pages = int(payload.get("pages") or 1)
            if page >= pages:
                break
            page += 1

        return out

    @staticmethod
    def _source_candidates(card: RiftboundCard, api_map: dict[str, str]) -> list[str]:
        candidates = [
            (api_map.get(card.card_number) or "").strip(),
            (card.image_url or "").strip(),
            (card.cdn_image_url or "").strip(),
        ]

        out: list[str] = []
        seen: set[str] = set()
        for url in candidates:
            if not url or url in seen:
                continue
            out.append(url)
            seen.add(url)
        return out

    @staticmethod
    def _card_numbers_from_api(card: dict) -> list[str]:
        rid = (card.get("riftbound_id") or "").strip().lower()
        meta = card.get("metadata") or {}
        parts = rid.split("-")
        if len(parts) < 2:
            return []

        set_code = parts[0].upper()
        number_part = parts[1].rstrip("*")
        base = f"{set_code}-{number_part}"

        out = [base]
        if meta.get("overnumbered"):
            out.append(f"{base}*")
        if meta.get("signature"):
            out.append(f"{base}**")
            out.append(f"{base}*")

        unique: list[str] = []
        seen: set[str] = set()
        for value in out:
            if value not in seen:
                unique.append(value)
                seen.add(value)
        return unique

    @staticmethod
    def _public_id_for_card(card: RiftboundCard) -> str:
        set_code = (card.set.code if card.set else "unknown").lower()
        safe_number = slugify(card.card_number) or "card"
        return f"riftbound/cards/{set_code}/{safe_number}"

    @staticmethod
    def _candidate_exts(source_url: str) -> list[str]:
        path = urlparse(source_url or "").path.lower()
        preferred = "webp"
        if path.endswith(".png"):
            preferred = "png"
        elif path.endswith(".jpg") or path.endswith(".jpeg"):
            preferred = "jpg"
        elif path.endswith(".webp"):
            preferred = "webp"

        ordered: list[str] = []
        for ext in [preferred, "webp", "png", "jpg", "jpeg"]:
            if ext not in ordered:
                ordered.append(ext)
        return ordered

    @staticmethod
    def _find_existing_imagekit_url(
        session: requests.Session,
        candidate_public_urls,
        public_id: str,
        ext_candidates: list[str],
        timeout: int,
    ) -> str:
        for candidate in candidate_public_urls(public_id, ext_candidates):
            try:
                head = session.head(candidate, timeout=timeout, allow_redirects=True)
            except Exception:
                continue
            if head.status_code == 200:
                return candidate
        return ""

    def _load_cdn_helpers(self):
        try:
            from cdn_uploader import candidate_public_urls, upload_bytes
            return candidate_public_urls, upload_bytes
        except Exception as exc:
            import_error = exc

        file_errors: list[str] = []
        for parent in Path(__file__).resolve().parents:
            candidate_path = parent / "cdn_uploader.py"
            if not candidate_path.exists():
                continue
            try:
                spec = importlib.util.spec_from_file_location("deckshadow_cdn_uploader", candidate_path)
                if spec is None or spec.loader is None:
                    file_errors.append(f"{candidate_path} (invalid spec)")
                    continue
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module.candidate_public_urls, module.upload_bytes
            except Exception as exc:
                file_errors.append(f"{candidate_path} ({exc})")

        tried = " | ".join(file_errors) if file_errors else "no cdn_uploader.py found"
        try:
            project_root = Path(__file__).resolve().parents[4]
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            from cdn_uploader import candidate_public_urls, upload_bytes
            return candidate_public_urls, upload_bytes
        except Exception as exc:
            raise CommandError(
                "No se pudo importar cdn_uploader.py. "
                f"Import directo: {import_error}. "
                f"Carga por archivo: {tried}. "
                f"Reintento con sys.path: {exc}."
            ) from exc

    @staticmethod
    def _guess_ext(source_url: str, content_type: str) -> str:
        path = urlparse(source_url).path.lower()
        if path.endswith(".png"):
            return "png"
        if path.endswith(".jpg") or path.endswith(".jpeg"):
            return "jpg"
        if path.endswith(".webp"):
            return "webp"

        ctype = (content_type or "").lower()
        if "png" in ctype:
            return "png"
        if "jpeg" in ctype or "jpg" in ctype:
            return "jpg"
        if "webp" in ctype:
            return "webp"
        return "webp"