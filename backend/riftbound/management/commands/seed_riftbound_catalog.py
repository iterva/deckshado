"""
Seed completo de catalogo Riftbound desde Riftcodex y subida opcional de imagenes al CDN.

Objetivo:
- Poblar/actualizar cartas en la DB local.
- Subir imagenes a ImageKit (u otro proveedor soportado por cdn_uploader.py).
- Evitar dependencia del cache cliente para cargar el catalogo.

Uso recomendado:
  python manage.py seed_riftbound_catalog --provider imagekit

Ejemplo con credenciales por argumento (solo para ejecucion puntual):
  python manage.py seed_riftbound_catalog \
      --provider imagekit \
      --imagekit-url-endpoint https://ik.imagekit.io/xxxx \
      --imagekit-private-key private_xxx
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID

import requests
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from riftbound.integrations.riftcodex import (
    RiftcodexClient,
    map_card_rarity,
    map_card_type,
    normalize_riftbound_card_number,
)
from riftbound.models import RiftboundCard, RiftboundSet


@dataclass(slots=True)
class SyncCounters:
    scanned: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    invalid_number: int = 0
    sets_created: int = 0
    sets_renamed: int = 0
    upload_ok: int = 0
    upload_linked: int = 0
    upload_skipped: int = 0
    upload_failed: int = 0


class Command(BaseCommand):
    help = "Seed completo Riftbound (DB + subida CDN opcional)."

    def add_arguments(self, parser):
        parser.add_argument("--size", type=int, default=100, help="Tamano de pagina Riftcodex (1..100).")
        parser.add_argument("--pause", type=float, default=0.0, help="Pausa entre requests al API.")
        parser.add_argument("--dry-run", action="store_true", help="No persiste cambios en DB ni CDN.")

        parser.add_argument("--skip-upload", action="store_true", help="No subir imagenes al CDN.")
        parser.add_argument("--provider", default="imagekit", help="Proveedor CDN para upload_bytes().")
        parser.add_argument(
            "--respect-existing-provider",
            action="store_true",
            help="Respeta CDN_PROVIDER actual en entorno (por defecto este seed lo fuerza para aislar Riftbound).",
        )
        parser.add_argument("--upload-only-missing-cdn", action="store_true", help="Solo cartas sin cdn_image_url.")
        parser.add_argument("--force-upload", action="store_true", help="Re-subir aunque ya exista cdn_image_url.")
        parser.add_argument("--upload-limit", type=int, default=0, help="Limite de uploads (0 = sin limite).")
        parser.add_argument("--image-timeout", type=int, default=30, help="Timeout en segundos para descarga imagen.")

        parser.add_argument(
            "--imagekit-url-endpoint",
            default="",
            help="Opcional: setea IMAGEKIT_URL_ENDPOINT solo para esta corrida.",
        )
        parser.add_argument(
            "--imagekit-private-key",
            default="",
            help="Opcional: setea IMAGEKIT_PRIVATE_KEY solo para esta corrida.",
        )

    def handle(self, *args, **opts):
        dry_run = bool(opts["dry_run"])
        page_size = max(1, min(100, int(opts["size"])))
        pause_seconds = max(0.0, float(opts["pause"]))

        counters = SyncCounters()
        set_cache: dict[str, RiftboundSet | None] = {}

        self.stdout.write("Iniciando seed Riftbound desde Riftcodex...")
        if dry_run:
            self.stdout.write(self.style.WARNING("Modo dry-run activo (sin persistencia)."))

        client = RiftcodexClient()

        for payload in client.iter_all_cards(size=page_size, request_pause_seconds=pause_seconds):
            counters.scanned += 1

            card_number = normalize_riftbound_card_number(
                payload.get("riftbound_id") or "",
                signature=bool((payload.get("metadata") or {}).get("signature")),
            )
            if not card_number:
                counters.invalid_number += 1
                continue

            set_obj = self._resolve_set(payload.get("set") or {}, set_cache, counters, dry_run)
            defaults = self._build_card_defaults(payload, set_obj)

            changed = self._upsert_card(
                card_number=card_number,
                defaults=defaults,
                payload=payload,
                counters=counters,
                dry_run=dry_run,
            )

            if changed and counters.scanned % 250 == 0:
                self.stdout.write(
                    f"  Procesadas {counters.scanned} cartas "
                    f"(create={counters.created}, update={counters.updated}, same={counters.unchanged})"
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Seed DB completado: "
                f"scanned={counters.scanned}, created={counters.created}, updated={counters.updated}, "
                f"unchanged={counters.unchanged}, invalid={counters.invalid_number}."
            )
        )

        if dry_run or opts["skip_upload"]:
            if opts["skip_upload"]:
                self.stdout.write("Upload CDN omitido por --skip-upload.")
            self._print_upload_summary(counters)
            return

        provider = self._prepare_cdn_env(opts)
        self._upload_card_images(counters, opts, provider)
        self._print_upload_summary(counters)

    def _resolve_set(
        self,
        set_info: dict,
        cache: dict[str, RiftboundSet | None],
        counters: SyncCounters,
        dry_run: bool,
    ) -> RiftboundSet | None:
        set_code = str(set_info.get("set_id") or "").upper().strip()
        if not set_code:
            return None

        if set_code in cache:
            return cache[set_code]

        set_name = str(set_info.get("label") or set_code).strip()[:120]
        obj = RiftboundSet.objects.filter(code=set_code).first()

        if not obj:
            counters.sets_created += 1
            if dry_run:
                cache[set_code] = None
                return None
            obj = RiftboundSet.objects.create(code=set_code, name=set_name)
        elif set_name and obj.name != set_name:
            counters.sets_renamed += 1
            if not dry_run:
                obj.name = set_name
                obj.save(update_fields=["name"])

        cache[set_code] = obj
        return obj

    def _build_card_defaults(self, payload: dict, set_obj: RiftboundSet | None) -> dict:
        cls = payload.get("classification") or {}
        attrs = payload.get("attributes") or {}
        text = payload.get("text") or {}
        media = payload.get("media") or {}
        meta = payload.get("metadata") or {}

        card_name = str(payload.get("name") or "").strip() or "Sin nombre"
        slug_base = str(meta.get("clean_name") or card_name)

        colors = [str(c).lower() for c in (cls.get("domain") or []) if c]
        subtype_list = [str(s).strip() for s in (payload.get("tags") or []) if str(s).strip()]

        variant_flags: list[str] = []
        if meta.get("alternate_art"):
            variant_flags.append("Alt-art")
        if meta.get("overnumbered"):
            variant_flags.append("Overnumbered")
        if meta.get("signature"):
            variant_flags.append("Signature")

        return {
            "name": card_name,
            "slug": slugify(slug_base)[:220],
            "set": set_obj,
            "card_type": map_card_type(cls.get("type")),
            "supertype": str(cls.get("supertype") or "")[:50],
            "subtypes": subtype_list,
            "rarity": map_card_rarity(cls.get("rarity")),
            "variant": ", ".join(variant_flags)[:40],
            "colors": colors,
            "energy": self._to_int(attrs.get("energy")),
            "power": self._to_int(attrs.get("power")),
            "might": self._to_int(attrs.get("might")),
            "description": str(text.get("plain") or ""),
            "flavor": str(text.get("flavour") or ""),
            "image_url": str(media.get("image_url") or ""),
            "image_url_small": "",
            "source_url": "",
            "raw": {},
            "is_active": True,
        }

    def _upsert_card(
        self,
        card_number: str,
        defaults: dict,
        payload: dict,
        counters: SyncCounters,
        dry_run: bool,
    ) -> bool:
        remote_uuid = self._parse_uuid(payload.get("id"))

        existing = RiftboundCard.objects.filter(card_number=card_number).first()
        if existing is None and remote_uuid:
            existing = RiftboundCard.objects.filter(external_id=remote_uuid).first()

        if existing is None:
            counters.created += 1
            if not dry_run:
                create_defaults = dict(defaults)
                if remote_uuid:
                    create_defaults["external_id"] = remote_uuid
                RiftboundCard.objects.create(card_number=card_number, **create_defaults)
            return True

        changed_fields: list[str] = []

        if existing.card_number != card_number:
            existing.card_number = card_number
            changed_fields.append("card_number")

        if remote_uuid and existing.external_id != remote_uuid:
            existing.external_id = remote_uuid
            changed_fields.append("external_id")

        for field, value in defaults.items():
            if getattr(existing, field) != value:
                setattr(existing, field, value)
                changed_fields.append(field)

        if changed_fields:
            counters.updated += 1
            if not dry_run:
                existing.save(update_fields=changed_fields)
            return True

        counters.unchanged += 1
        return False

    def _prepare_cdn_env(self, opts: dict) -> str:
        provider = (opts.get("provider") or "imagekit").strip().lower()
        current_provider = (os.environ.get("CDN_PROVIDER") or "").strip().lower()
        respect_existing = bool(opts.get("respect_existing_provider"))

        if respect_existing and current_provider and current_provider != provider:
            self.stdout.write(
                self.style.WARNING(
                    f"CDN_PROVIDER actual '{current_provider}' se respeta por --respect-existing-provider "
                    f"(provider solicitado: '{provider}')."
                )
            )
            active_provider = current_provider
        else:
            os.environ["CDN_PROVIDER"] = provider
            active_provider = provider

        self.stdout.write(f"Proveedor CDN activo para Riftbound: {active_provider}")

        endpoint_arg = (opts.get("imagekit_url_endpoint") or "").strip()
        private_key_arg = (opts.get("imagekit_private_key") or "").strip()

        if endpoint_arg:
            os.environ["IMAGEKIT_URL_ENDPOINT"] = endpoint_arg.rstrip("/")
        if private_key_arg:
            os.environ["IMAGEKIT_PRIVATE_KEY"] = private_key_arg

        if active_provider == "imagekit":
            has_pair = bool(os.environ.get("IMAGEKIT_PRIVATE_KEY") and os.environ.get("IMAGEKIT_URL_ENDPOINT"))
            has_csv = bool(os.environ.get("IMAGEKIT_PRIVATE_KEYS") and os.environ.get("IMAGEKIT_URL_ENDPOINTS"))
            if not (has_pair or has_csv):
                raise CommandError(
                    "Faltan credenciales de ImageKit. Define IMAGEKIT_PRIVATE_KEY + IMAGEKIT_URL_ENDPOINT "
                    "(o IMAGEKIT_PRIVATE_KEYS + IMAGEKIT_URL_ENDPOINTS)."
                )

        return active_provider

    def _upload_card_images(self, counters: SyncCounters, opts: dict, provider: str) -> None:
        candidate_public_urls, upload_bytes = self._load_cdn_helpers()

        force_upload = bool(opts.get("force_upload"))
        only_missing = bool(opts.get("upload_only_missing_cdn"))
        upload_limit = max(0, int(opts.get("upload_limit") or 0))
        image_timeout = max(5, int(opts.get("image_timeout") or 30))

        qs = RiftboundCard.objects.filter(is_active=True).exclude(image_url="").select_related("set")
        cards = list(qs)

        if only_missing and not force_upload:
            if provider == "imagekit":
                cards = [c for c in cards if not self._is_imagekit_url(c.cdn_image_url)]
            else:
                cards = [c for c in cards if not (c.cdn_image_url or "").strip()]

        if upload_limit:
            cards = cards[:upload_limit]

        total = len(cards)
        self.stdout.write(f"Iniciando upload CDN para {total} cartas...")

        session = requests.Session()
        session.headers.update({"User-Agent": "deckshado-riftbound-seeder/1.0"})

        for idx, card in enumerate(cards, start=1):
            status, message = self._upload_one_card(
                card=card,
                session=session,
                candidate_public_urls=candidate_public_urls,
                upload_bytes=upload_bytes,
                force_upload=force_upload,
                image_timeout=image_timeout,
                provider=provider,
            )

            if status == "ok":
                counters.upload_ok += 1
            elif status == "linked":
                counters.upload_linked += 1
            elif status == "skip":
                counters.upload_skipped += 1
            else:
                counters.upload_failed += 1

            if idx % 50 == 0 or status == "error":
                tail = f" ({message})" if status == "error" else ""
                self.stdout.write(f"  [{idx}/{total}] {card.card_number}: {status}{tail}")

    def _upload_one_card(
        self,
        card: RiftboundCard,
        session: requests.Session,
        candidate_public_urls,
        upload_bytes,
        force_upload: bool,
        image_timeout: int,
        provider: str,
    ) -> tuple[str, str]:
        if card.cdn_image_url and not force_upload:
            if provider != "imagekit" or self._is_imagekit_url(card.cdn_image_url):
                return "skip", "already-has-cdn"

        source_url = (card.image_url or "").strip()
        if not source_url:
            return "skip", "missing-image-url"

        set_code = (card.set.code if card.set else "unknown").lower()
        safe_number = self._safe_slug(card.card_number)
        public_id = f"riftbound/cards/{set_code}/{safe_number}"

        # Fast-path: if already present in CDN, only link URL in DB.
        for existing in candidate_public_urls(public_id, ("webp", "png", "jpg", "jpeg")):
            try:
                head = session.head(existing, timeout=10)
                if head.status_code == 200:
                    if card.cdn_image_url != existing:
                        card.cdn_image_url = existing
                        card.save(update_fields=["cdn_image_url"])
                    return "linked", existing
            except Exception:
                continue

        try:
            resp = session.get(source_url, timeout=image_timeout)
            resp.raise_for_status()
        except Exception as exc:
            return "error", f"download-failed: {exc}"

        ext = self._guess_ext(source_url, resp.headers.get("Content-Type", ""))

        try:
            cdn_url = upload_bytes(
                resp.content,
                public_id=public_id,
                default_ext=ext,
                mime_type=resp.headers.get("Content-Type", "application/octet-stream"),
                overwrite=True,
            )
        except Exception as exc:
            return "error", f"upload-failed: {exc}"

        if card.cdn_image_url != cdn_url:
            card.cdn_image_url = cdn_url
            card.save(update_fields=["cdn_image_url"])

        return "ok", cdn_url

    def _load_cdn_helpers(self):
        try:
            from cdn_uploader import candidate_public_urls, upload_bytes
            return candidate_public_urls, upload_bytes
        except Exception:
            project_root = Path(__file__).resolve().parents[4]
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))

        try:
            from cdn_uploader import candidate_public_urls, upload_bytes
            return candidate_public_urls, upload_bytes
        except Exception as exc:
            raise CommandError(
                f"No se pudo importar cdn_uploader.py: {exc}. Ejecuta desde el workspace Proyecto-deckshado."
            ) from exc

    def _print_upload_summary(self, counters: SyncCounters) -> None:
        self.stdout.write(
            self.style.SUCCESS(
                "Resumen uploads: "
                f"ok={counters.upload_ok}, linked={counters.upload_linked}, "
                f"skip={counters.upload_skipped}, error={counters.upload_failed}."
            )
        )

    @staticmethod
    def _to_int(value):
        try:
            if value is None or value == "":
                return None
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_uuid(value):
        if not value:
            return None
        try:
            return UUID(str(value))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_slug(value: str) -> str:
        result = slugify(value or "")
        return result or "card"

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

    @staticmethod
    def _is_imagekit_url(url: str) -> bool:
        value = (url or "").strip()
        if not value:
            return False

        if "ik.imagekit.io/" in value:
            return True

        primary = (os.environ.get("IMAGEKIT_URL_ENDPOINT") or "").strip().rstrip("/")
        if primary and (value == primary or value.startswith(primary + "/")):
            return True

        csv_endpoints = (os.environ.get("IMAGEKIT_URL_ENDPOINTS") or "").strip()
        if csv_endpoints:
            for endpoint in csv_endpoints.split(","):
                clean = endpoint.strip().rstrip("/")
                if clean and (value == clean or value.startswith(clean + "/")):
                    return True

        return False
