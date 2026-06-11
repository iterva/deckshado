"""
Audita diferencias entre el catalogo local y Riftcodex.

Uso:
    python manage.py audit_riftcodex_diff
    python manage.py audit_riftcodex_diff --limit 100
    python manage.py audit_riftcodex_diff --json
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from riftbound.integrations.riftcodex import (
    RiftcodexClient,
    map_card_rarity,
    map_card_type,
    normalize_riftbound_card_number,
)
from riftbound.models import RiftboundCard, RiftboundSyncState


@dataclass(slots=True)
class DiffCounters:
    remote_total: int = 0
    local_total: int = 0
    missing_in_local: int = 0
    missing_in_remote: int = 0
    type_mismatches: int = 0
    rarity_mismatches: int = 0
    set_mismatches: int = 0

    def as_dict(self) -> dict:
        return {
            "remote_total": self.remote_total,
            "local_total": self.local_total,
            "missing_in_local": self.missing_in_local,
            "missing_in_remote": self.missing_in_remote,
            "type_mismatches": self.type_mismatches,
            "rarity_mismatches": self.rarity_mismatches,
            "set_mismatches": self.set_mismatches,
        }


class Command(BaseCommand):
    help = "Audita diferencias local vs Riftcodex y guarda resumen en RiftboundSyncState(key=audit_cards)."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50, help="Maximo de ejemplos por categoria.")
        parser.add_argument("--json", action="store_true", help="Imprime salida JSON.")

    def handle(self, *args, **opts):
        limit = max(1, int(opts["limit"]))
        as_json = bool(opts["json"])

        state, _ = RiftboundSyncState.objects.get_or_create(
            provider="riftcodex",
            key="audit_cards",
            defaults={"last_stats": {}},
        )
        state.last_started_at = timezone.now()
        state.last_error = ""
        state.save(update_fields=["last_started_at", "last_error", "updated_at"])

        try:
            report = self._build_report(limit=limit)
        except Exception as exc:
            state.last_error = str(exc)[:1500]
            state.save(update_fields=["last_error", "updated_at"])
            raise CommandError(f"No se pudo auditar Riftcodex: {exc}") from exc

        state.last_success_at = timezone.now()
        state.last_stats = report
        state.last_error = ""
        state.save(update_fields=["last_success_at", "last_stats", "last_error", "updated_at"])

        if as_json:
            self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))
            return

        c = report["counters"]
        self.stdout.write(self.style.SUCCESS(
            "Auditoria lista: "
            f"remote={c['remote_total']} local={c['local_total']} "
            f"missing_local={c['missing_in_local']} missing_remote={c['missing_in_remote']} "
            f"type_mm={c['type_mismatches']} rarity_mm={c['rarity_mismatches']} set_mm={c['set_mismatches']}"
        ))

    def _build_report(self, limit: int) -> dict:
        counters = DiffCounters()
        remote_cards = list(RiftcodexClient().iter_all_cards(size=100, request_pause_seconds=0.0))
        counters.remote_total = len(remote_cards)

        local_cards = list(
            RiftboundCard.objects.select_related("set")
            .filter(is_active=True)
            .values("card_number", "card_type", "rarity", "set__code")
        )
        counters.local_total = len(local_cards)

        local_map = {str(r["card_number"]).upper(): r for r in local_cards}
        remote_map: dict[str, dict] = {}

        missing_local_examples: list[dict] = []
        type_examples: list[dict] = []
        rarity_examples: list[dict] = []
        set_examples: list[dict] = []

        for card in remote_cards:
            meta = card.get("metadata") or {}
            number = normalize_riftbound_card_number(
                card.get("riftbound_id") or "",
                signature=bool(meta.get("signature")),
            ).upper()
            if not number:
                continue

            remote_map[number] = card
            local = local_map.get(number)
            if not local:
                counters.missing_in_local += 1
                if len(missing_local_examples) < limit:
                    remote_cls = card.get("classification") or {}
                    remote_set = card.get("set") or {}
                    missing_local_examples.append(
                        {
                            "card_number": number,
                            "name": card.get("name"),
                            "type": map_card_type(remote_cls.get("type")),
                            "rarity": map_card_rarity(remote_cls.get("rarity")),
                            "set": str(remote_set.get("set_id") or "").upper(),
                        }
                    )
                continue

            remote_cls = card.get("classification") or {}
            remote_type = map_card_type(remote_cls.get("type"))
            remote_rarity = map_card_rarity(remote_cls.get("rarity"))
            remote_set = str((card.get("set") or {}).get("set_id") or "").upper()

            if (local.get("card_type") or "") != remote_type:
                counters.type_mismatches += 1
                if len(type_examples) < limit:
                    type_examples.append(
                        {
                            "card_number": number,
                            "local": local.get("card_type"),
                            "remote": remote_type,
                        }
                    )

            if (local.get("rarity") or "") != remote_rarity:
                counters.rarity_mismatches += 1
                if len(rarity_examples) < limit:
                    rarity_examples.append(
                        {
                            "card_number": number,
                            "local": local.get("rarity"),
                            "remote": remote_rarity,
                        }
                    )

            local_set = (local.get("set__code") or "").upper()
            if remote_set and local_set != remote_set:
                counters.set_mismatches += 1
                if len(set_examples) < limit:
                    set_examples.append(
                        {
                            "card_number": number,
                            "local": local_set,
                            "remote": remote_set,
                        }
                    )

        missing_remote_examples: list[dict] = []
        for number, row in local_map.items():
            if number not in remote_map:
                counters.missing_in_remote += 1
                if len(missing_remote_examples) < limit:
                    missing_remote_examples.append(
                        {
                            "card_number": number,
                            "type": row.get("card_type"),
                            "rarity": row.get("rarity"),
                            "set": (row.get("set__code") or "").upper(),
                        }
                    )

        return {
            "generated_at": timezone.now().isoformat(),
            "counters": counters.as_dict(),
            "examples": {
                "missing_in_local": missing_local_examples,
                "missing_in_remote": missing_remote_examples,
                "type_mismatches": type_examples,
                "rarity_mismatches": rarity_examples,
                "set_mismatches": set_examples,
            },
        }
