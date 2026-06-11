"""
Health check de sincronizacion Riftcodex.

Uso:
    python manage.py riftcodex_sync_health
    python manage.py riftcodex_sync_health --warn-hours 30
    python manage.py riftcodex_sync_health --json
"""
from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from riftbound.models import RiftboundSyncState


class Command(BaseCommand):
    help = "Valida estado de la sincronizacion de cartas con Riftcodex."

    def add_arguments(self, parser):
        parser.add_argument(
            "--warn-hours",
            type=float,
            default=30.0,
            help="Maximo de horas sin sync exitosa antes de marcar stale (default: 30).",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Imprime resultado en JSON.",
        )
        parser.add_argument(
            "--soft",
            action="store_true",
            help="No retorna error aunque el estado sea unhealthy.",
        )

    def handle(self, *args, **opts):
        warn_hours = max(1.0, float(opts["warn_hours"]))
        output_json = bool(opts["json"])
        soft_mode = bool(opts["soft"])

        state = RiftboundSyncState.objects.filter(provider="riftcodex", key="cards").first()
        payload = {
            "provider": "riftcodex",
            "key": "cards",
            "healthy": True,
            "status": "ok",
            "reason": "",
            "warn_hours": warn_hours,
            "last_success_at": None,
            "last_success_age_hours": None,
            "last_cursor": None,
            "last_error": "",
            "last_stats": {},
        }

        if not state:
            payload.update(
                healthy=False,
                status="never_run",
                reason="No existe estado de sync. Ejecuta sync_riftcodex_cards.",
            )
            return self._finish(payload, output_json, soft_mode)

        payload["last_success_at"] = state.last_success_at.isoformat() if state.last_success_at else None
        payload["last_cursor"] = state.last_cursor.isoformat() if state.last_cursor else None
        payload["last_error"] = state.last_error or ""
        payload["last_stats"] = state.last_stats or {}

        if state.last_success_at:
            age_hours = round((timezone.now() - state.last_success_at).total_seconds() / 3600, 2)
            payload["last_success_age_hours"] = age_hours
            if age_hours > warn_hours:
                payload.update(
                    healthy=False,
                    status="stale",
                    reason=f"Ultima sync exitosa hace {age_hours}h (> {warn_hours}h).",
                )
        else:
            payload.update(
                healthy=False,
                status="never_success",
                reason="No hay registro de sync exitosa.",
            )

        if state.last_error:
            payload.update(
                healthy=False,
                status="error",
                reason="La ultima ejecucion registro error.",
            )

        return self._finish(payload, output_json, soft_mode)

    def _finish(self, payload: dict, output_json: bool, soft_mode: bool):
        if output_json:
            self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            marker = "OK" if payload["healthy"] else "WARN"
            self.stdout.write(
                f"[{marker}] {payload['provider']}:{payload['key']} status={payload['status']} "
                f"reason={payload['reason'] or '-'}"
            )
            self.stdout.write(
                f"last_success_at={payload['last_success_at']} "
                f"age_hours={payload['last_success_age_hours']} cursor={payload['last_cursor']}"
            )

        if not payload["healthy"] and not soft_mode:
            raise CommandError(payload["reason"] or "Riftcodex sync unhealthy")
