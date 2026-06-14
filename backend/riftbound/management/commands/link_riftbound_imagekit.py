from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils.text import slugify

from riftbound.models import RiftboundCard


@dataclass(slots=True)
class LinkCounters:
    scanned: int = 0
    linked: int = 0
    unchanged: int = 0
    not_found: int = 0
    errors: int = 0


class Command(BaseCommand):
    help = "Vincula cartas Riftbound a URLs ya existentes en ImageKit (sin download/upload)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Procesa todas las cartas activas (por defecto solo faltantes/no-imagekit).",
        )
        parser.add_argument("--set", default="", help="Filtra por set code (ej: SFD).")
        parser.add_argument("--limit", type=int, default=0, help="Limite de cartas a procesar (0 = sin limite).")
        parser.add_argument(
            "--start-from",
            default="",
            help="Empieza desde card_number >= valor indicado (util para reanudar lotes).",
        )
        parser.add_argument("--timeout", type=int, default=10, help="Timeout HEAD en segundos.")
        parser.add_argument("--dry-run", action="store_true", help="No guarda cambios en BD.")

    def handle(self, *args, **opts):
        endpoints = self._imagekit_endpoints()
        self.stdout.write(f"Endpoints ImageKit activos: {len(endpoints)}")
        for ep in endpoints:
            self.stdout.write(f"  - {ep}")

        qs = RiftboundCard.objects.filter(is_active=True).select_related("set").order_by("card_number")

        set_code = (opts.get("set") or "").strip().upper()
        if set_code:
            qs = qs.filter(set__code=set_code)

        start_from = (opts.get("start_from") or "").strip()
        if start_from:
            qs = qs.filter(card_number__gte=start_from)

        if not bool(opts.get("all")):
            qs = qs.filter(Q(cdn_image_url__isnull=True) | Q(cdn_image_url="") | ~Q(cdn_image_url__icontains="imagekit"))

        limit = max(0, int(opts.get("limit") or 0))
        cards = list(qs[:limit] if limit else qs)
        total = len(cards)

        if total == 0:
            self.stdout.write(self.style.WARNING("No hay cartas para procesar."))
            return

        timeout = max(3, int(opts.get("timeout") or 10))
        dry_run = bool(opts.get("dry_run"))
        counters = LinkCounters()

        self.stdout.write(f"Iniciando linkeo HEAD-only para {total} cartas...")
        if dry_run:
            self.stdout.write(self.style.WARNING("Modo dry-run activo (sin persistencia)."))

        session = requests.Session()
        session.headers.update({"User-Agent": "deckshado-riftbound-imagekit-linker/1.0"})

        misses: list[str] = []

        for idx, card in enumerate(cards, start=1):
            counters.scanned += 1
            try:
                result = self._link_one_card(card=card, endpoints=endpoints, session=session, timeout=timeout, dry_run=dry_run)
            except Exception as exc:
                counters.errors += 1
                result = f"error({exc})"

            if result == "linked":
                counters.linked += 1
            elif result == "unchanged":
                counters.unchanged += 1
            elif result == "not-found":
                counters.not_found += 1
                misses.append(card.card_number)
            else:
                counters.errors += 1

            if idx % 100 == 0:
                self.stdout.write(
                    f"  [{idx}/{total}] linked={counters.linked} unchanged={counters.unchanged} "
                    f"not_found={counters.not_found} errors={counters.errors}"
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Resumen linkeo: "
                f"scanned={counters.scanned}, linked={counters.linked}, unchanged={counters.unchanged}, "
                f"not_found={counters.not_found}, errors={counters.errors}."
            )
        )

        if misses:
            preview = ", ".join(misses[:20])
            suffix = " ..." if len(misses) > 20 else ""
            self.stdout.write(self.style.WARNING(f"No encontradas ({len(misses)}): {preview}{suffix}"))

    def _link_one_card(
        self,
        card: RiftboundCard,
        endpoints: list[str],
        session: requests.Session,
        timeout: int,
        dry_run: bool,
    ) -> str:
        set_code = (card.set.code if card.set else "unknown").lower()
        safe_number = self._safe_slug(card.card_number)
        public_id = f"riftbound/cards/{set_code}/{safe_number}"

        for endpoint in endpoints:
            for ext in self._candidate_exts(card.image_url):
                candidate = f"{endpoint}/{public_id}.{ext}"
                try:
                    head = session.head(candidate, timeout=timeout, allow_redirects=True)
                except Exception:
                    continue

                if head.status_code != 200:
                    continue

                if card.cdn_image_url == candidate:
                    return "unchanged"

                if not dry_run:
                    card.cdn_image_url = candidate
                    card.save(update_fields=["cdn_image_url"])
                return "linked"

        return "not-found"

    @staticmethod
    def _safe_slug(value: str) -> str:
        result = slugify(value or "")
        return result or "card"

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

        if not out:
            raise CommandError(
                "Falta IMAGEKIT_URL_ENDPOINT (o IMAGEKIT_URL_ENDPOINTS) para ejecutar linkeo HEAD-only."
            )

        return out