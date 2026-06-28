"""
Sincroniza cartas de Riftcodex hacia la base local de Riftbound.

Modos:
    python manage.py sync_riftcodex_cards
    python manage.py sync_riftcodex_cards --full
    python manage.py sync_riftcodex_cards --dry-run
    python manage.py sync_riftcodex_cards --since 2026-06-01T00:00:00Z
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.text import slugify

from riftbound.integrations.riftcodex import (
    RiftcodexClient,
    map_card_rarity,
    map_card_type,
    normalize_riftbound_card_number,
    parse_riftcodex_updated_on,
)
from riftbound.models import RiftboundCard, RiftboundSet, RiftboundSyncState


SYNC_STATE_KEY = "cards"


@dataclass(slots=True)
class SyncCounters:
    scanned: int = 0
    candidates: int = 0
    skipped_by_cursor: int = 0
    invalid_number: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    sets_created: int = 0
    sets_renamed: int = 0

    def as_dict(self) -> dict:
        return {
            "scanned": self.scanned,
            "candidates": self.candidates,
            "skipped_by_cursor": self.skipped_by_cursor,
            "invalid_number": self.invalid_number,
            "created": self.created,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "sets_created": self.sets_created,
            "sets_renamed": self.sets_renamed,
        }


class Command(BaseCommand):
    help = "Sincroniza cartas desde api.riftcodex.com (incremental por updated_on)."

    def add_arguments(self, parser):
        parser.add_argument("--full", action="store_true", help="Ignora cursor y sincroniza todo")
        parser.add_argument(
            "--since",
            default=None,
            help="ISO datetime para cursor manual. Ej: 2026-06-01T00:00:00Z",
        )
        parser.add_argument("--dry-run", action="store_true", help="No persiste cambios en DB")
        parser.add_argument("--size", type=int, default=100, help="Tamano de pagina (1..100)")
        parser.add_argument(
            "--pause",
            type=float,
            default=0.0,
            help="Pausa entre requests en segundos (ej: 0.2)",
        )
        parser.add_argument(
            "--skip-fixes",
            action="store_true",
            help="No ejecutar apply_riftbound_fixes al terminar",
        )

    def handle(self, *args, **opts):
        dry_run = bool(opts["dry_run"])
        is_full = bool(opts["full"])
        page_size = max(1, min(100, int(opts["size"])))
        request_pause = max(0.0, float(opts["pause"]))

        state, _ = RiftboundSyncState.objects.get_or_create(
            key=SYNC_STATE_KEY,
            defaults={"provider": "riftcodex"},
        )

        since_dt = self._resolve_since(opts.get("since"), is_full, state)
        now = timezone.now()
        state.last_started_at = now
        state.last_error = ""
        state.save(update_fields=["last_started_at", "last_error", "updated_at"])

        self.stdout.write("Iniciando sync Riftcodex...")
        if since_dt:
            self.stdout.write(f"Cursor incremental: {since_dt.isoformat()}")
        else:
            self.stdout.write("Cursor incremental: <none> (full scan)")
        if dry_run:
            self.stdout.write(self.style.WARNING("Modo dry-run activo (sin cambios en DB)."))

        counters = SyncCounters()
        latest_seen_updated_on: datetime | None = state.last_cursor
        client = RiftcodexClient()
        set_cache: dict[str, RiftboundSet | None] = {}

        try:
            with transaction.atomic():
                for payload in client.iter_all_cards(size=page_size, request_pause_seconds=request_pause):
                    counters.scanned += 1
                    updated_on = parse_riftcodex_updated_on((payload.get("metadata") or {}).get("updated_on"))
                    if updated_on and (not latest_seen_updated_on or updated_on > latest_seen_updated_on):
                        latest_seen_updated_on = updated_on

                    if since_dt and updated_on and updated_on <= since_dt:
                        counters.skipped_by_cursor += 1
                        continue

                    counters.candidates += 1
                    card_number = normalize_riftbound_card_number(
                        payload.get("riftbound_id") or "",
                        signature=bool((payload.get("metadata") or {}).get("signature")),
                    )
                    if not card_number:
                        counters.invalid_number += 1
                        continue

                    set_obj = self._resolve_set(payload.get("set") or {}, dry_run, set_cache, counters)
                    defaults = self._build_card_defaults(payload, set_obj)

                    existing = RiftboundCard.objects.filter(card_number=card_number).first()
                    if existing is None:
                        counters.created += 1
                        if not dry_run:
                            RiftboundCard.objects.create(card_number=card_number, **defaults)
                        continue

                    changed = False
                    for field, val in defaults.items():
                        if getattr(existing, field) != val:
                            setattr(existing, field, val)
                            changed = True

                    if changed:
                        counters.updated += 1
                        if not dry_run:
                            existing.save()
                    else:
                        counters.unchanged += 1

                if dry_run:
                    transaction.set_rollback(True)

        except Exception as exc:
            state.last_error = str(exc)[:1500]
            state.last_stats = counters.as_dict()
            state.save(update_fields=["last_error", "last_stats", "updated_at"])
            raise CommandError(f"Sync fallida: {exc}") from exc

        finished_at = timezone.now()
        if not dry_run:
            state.last_cursor = latest_seen_updated_on or state.last_cursor
        state.last_success_at = finished_at
        state.last_stats = {
            **counters.as_dict(),
            "dry_run": dry_run,
            "full": is_full,
            "since": since_dt.isoformat() if since_dt else None,
            "cursor_after": state.last_cursor.isoformat() if state.last_cursor else None,
            "finished_at": finished_at.isoformat(),
        }
        state.last_error = ""
        state.save(update_fields=["last_cursor", "last_success_at", "last_stats", "last_error", "updated_at"])

        self.stdout.write(self.style.SUCCESS(
            "Sync completada: "
            f"scanned={counters.scanned}, candidates={counters.candidates}, "
            f"created={counters.created}, updated={counters.updated}, unchanged={counters.unchanged}, "
            f"skipped_by_cursor={counters.skipped_by_cursor}."
        ))

        if not dry_run and not opts["skip_fixes"]:
            self.stdout.write("Aplicando fixes locales post-sync...")
            call_command("apply_riftbound_fixes")

    def _resolve_since(self, since_value: str | None, is_full: bool, state: RiftboundSyncState) -> datetime | None:
        if is_full:
            return None
        if since_value:
            parsed = parse_datetime(since_value)
            if not parsed:
                raise CommandError("Parametro --since invalido. Usa formato ISO 8601.")
            if timezone.is_naive(parsed):
                parsed = timezone.make_aware(parsed, timezone=timezone.utc)
            return parsed
        return state.last_cursor

    def _resolve_set(
        self,
        set_info: dict,
        dry_run: bool,
        cache: dict[str, RiftboundSet | None],
        counters: SyncCounters,
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
            "energy": attrs.get("energy"),
            "power": attrs.get("power"),
            "might": attrs.get("might"),
            "description": str(text.get("plain") or ""),
            "flavor": str(text.get("flavour") or ""),
            "image_url": str(media.get("image_url") or ""),
            "image_url_small": "",
            "source_url": "",
            "raw": {},
            "is_active": True,
        }
