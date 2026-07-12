"""
Seed para sincronizar Angeles y Demonios Vigilantes (AYDV) desde la API oficial de MYL.

Objetivo:
- Reemplazar imagenes por las oficiales de API (custom_image_url),
  respetando un set de exclusiones de imagen.
- Actualizar habilidad, tipo de carta, coste y ataque (damage).
- Crear cartas faltantes de la API dentro de la edicion local `aydv`.

Uso:
  python manage.py seed_aydv_from_myl_api
  python manage.py seed_aydv_from_myl_api --dry-run
  python manage.py seed_aydv_from_myl_api --report-file ../aydv_api_seed_report.json
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from django.core.management.base import BaseCommand, CommandError

from cards.models import Card, CardType, Edition, Format, Race, Rarity


API_URL = "https://api.myl.cl/cards/edition/ayd_vigilantes"
API_CDN_BASE = "https://api.myl.cl/static/cards"
DEFAULT_REPORT_FILE = Path(__file__).resolve().parents[4] / "aydv_api_seed_report.json"
DEFAULT_SNAPSHOT_FILE = Path(__file__).resolve().parents[2] / "data" / "ayd_vigilantes_api_snapshot.json"


PROTECTED_IMAGE_NAMES = {
    "serpiente del eden",
    "la serpiente del eden",
    "acabar esperanza",
    "acabar la esperanza",
    "agabar esperanza",
    "agabar la esperanza",
    "guerrillero rodriguez",
    "el oro",
    "infernum vox",
}

STOPWORDS = {
    "de", "del", "la", "las", "los", "el", "y", "en", "al", "a", "un", "una",
}


@dataclass
class ApiCard:
    api_id: str
    edid: str
    slug: str
    name: str
    norm_name: str
    rarity_slug: str
    race_id: str | None
    type_id: str | None
    cost: str | None
    damage: str | None
    ability: str
    flavour: str
    image_url: str


def _norm(text: str | None) -> str:
    value = (text or "").strip().replace("�", "")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()

    # Reparaciones comunes de mojibake observadas en API/datos locales.
    if value.startswith("ngel "):
        value = f"angel {value[5:]}"
    value = value.replace("bretaa", "bretana")
    value = value.replace("sealados", "senalados")
    value = value.replace("martires", "martires")
    return value


def _token_set(value: str) -> set[str]:
    return {tok for tok in value.split() if tok and tok not in STOPWORDS and len(tok) > 2}


def _sim_ratio(a: str, b: str) -> float:
    # Similaridad simple sin dependencia externa.
    if not a or not b:
        return 0.0
    # Dice coefficient por bigramas.
    def _bigrams(s: str) -> set[str]:
        if len(s) < 2:
            return {s}
        return {s[i : i + 2] for i in range(len(s) - 1)}

    a2 = _bigrams(a)
    b2 = _bigrams(b)
    inter = len(a2 & b2)
    return (2.0 * inter) / (len(a2) + len(b2)) if (a2 or b2) else 0.0


def _best_match(local_card: Card, api_cards: list[ApiCard]) -> tuple[ApiCard | None, float]:
    local_norm = _norm(local_card.name)
    local_tokens = _token_set(local_norm)
    local_rarity = local_card.rarity.slug if local_card.rarity else ""

    exact_same_rarity = [a for a in api_cards if a.norm_name == local_norm and a.rarity_slug == local_rarity]
    if exact_same_rarity:
        return exact_same_rarity[0], 1.0

    exact_any_rarity = [a for a in api_cards if a.norm_name == local_norm]
    if exact_any_rarity:
        return exact_any_rarity[0], 0.97

    best: ApiCard | None = None
    best_score = 0.0
    for candidate in api_cards:
        cand_tokens = _token_set(candidate.norm_name)
        token_inter = len(local_tokens & cand_tokens)
        if token_inter == 0:
            continue

        ratio = _sim_ratio(local_norm, candidate.norm_name)
        jaccard = token_inter / max(1, len(local_tokens | cand_tokens))
        score = (ratio * 0.75) + (jaccard * 0.25)
        if local_rarity and local_rarity == candidate.rarity_slug:
            score += 0.06

        if score > best_score:
            best = candidate
            best_score = score

    # Threshold conservador para evitar matches incorrectos.
    if best is not None and best_score >= 0.82:
        return best, best_score
    return None, best_score


def _best_match_aggressive(local_card: Card, api_cards: list[ApiCard]) -> tuple[ApiCard | None, float]:
    """Fallback mas permisivo para reducir unmatched en cartas legacy/custom."""
    local_norm = _norm(local_card.name)
    local_tokens = _token_set(local_norm)
    local_rarity = local_card.rarity.slug if local_card.rarity else ""

    best: ApiCard | None = None
    best_score = 0.0
    for candidate in api_cards:
        cand_tokens = _token_set(candidate.norm_name)
        ratio = _sim_ratio(local_norm, candidate.norm_name)
        jaccard = 0.0
        if local_tokens or cand_tokens:
            jaccard = len(local_tokens & cand_tokens) / max(1, len(local_tokens | cand_tokens))

        score = (ratio * 0.85) + (jaccard * 0.15)
        if local_rarity and local_rarity == candidate.rarity_slug:
            score += 0.05
        if local_norm and (local_norm in candidate.norm_name or candidate.norm_name in local_norm):
            score += 0.05

        if score > best_score:
            best = candidate
            best_score = score

    if best is not None and best_score >= 0.62:
        return best, best_score
    return None, best_score


def _extract_api_edid_candidate(local_edid: str | None) -> str | None:
    """Extrae edid de API (3 digitos) solo para patrones AYDV numericos seguros."""
    value = (local_edid or "").strip().upper()
    if re.fullmatch(r"\d{3}", value):
        return value

    # Ej: AYDV-123 o AYDV-243-P
    m = re.fullmatch(r"AYDV-(\d{3})(?:-[A-Z])?", value)
    if m:
        return m.group(1)

    return None


class Command(BaseCommand):
    help = "Sincroniza AYDV desde API MYL: imagenes + datos + crea faltantes"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="No guarda cambios en BD",
        )
        parser.add_argument(
            "--report-file",
            default=str(DEFAULT_REPORT_FILE),
            help="Ruta para guardar reporte JSON",
        )
        parser.add_argument(
            "--source",
            type=str,
            default="auto",
            choices=["auto", "web", "snapshot"],
            help="Fuente de datos: auto (intenta web y cae a snapshot), web, snapshot",
        )
        parser.add_argument(
            "--source-file",
            default=str(DEFAULT_SNAPSHOT_FILE),
            help="Ruta del snapshot JSON usado en modo snapshot/auto",
        )
        parser.add_argument(
            "--aggressive-unmatched",
            action="store_true",
            help="Aplica un fallback fuzzy mas agresivo para reducir unmatched",
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

    def _fetch_api(self) -> dict[str, Any]:
        try:
            response = requests.get(API_URL, timeout=60)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise CommandError(f"No se pudo consultar API MYL: {exc}") from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise CommandError("Respuesta API no es JSON valido") from exc

        if data.get("status") != "OK":
            raise CommandError(f"API devolvio status no OK: {data.get('status')}")
        return data

    def _load_snapshot(self, source_file: Path) -> dict[str, Any]:
        if not source_file.exists():
            raise CommandError(f"No existe snapshot local: {source_file}")

        try:
            data = json.loads(source_file.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise CommandError(f"Snapshot JSON invalido: {source_file}") from exc

        if data.get("status") != "OK":
            raise CommandError(f"Snapshot con status no OK: {data.get('status')}")
        return data

    def _load_source_data(self, source: str, source_file: Path) -> tuple[dict[str, Any], str]:
        if source == "web":
            return self._fetch_api(), "web"

        if source == "snapshot":
            return self._load_snapshot(source_file), "snapshot"

        # auto
        try:
            return self._fetch_api(), "web"
        except CommandError as exc:
            self.stdout.write(
                self.style.WARNING(
                    f"No se pudo consultar API ({exc}). Se usara snapshot local."
                )
            )
            return self._load_snapshot(source_file), "snapshot"

    def _sync_catalog_tables(self, data: dict[str, Any], dry_run: bool) -> None:
        if dry_run:
            return

        for race in data.get("races", []):
            Race.objects.update_or_create(
                myl_id=str(race.get("id")),
                defaults={
                    "slug": str(race.get("slug") or "").strip(),
                    "name": str(race.get("name") or "").strip(),
                },
            )

        for ctype in data.get("types", []):
            CardType.objects.update_or_create(
                myl_id=str(ctype.get("id")),
                defaults={
                    "slug": str(ctype.get("slug") or "").strip(),
                    "name": str(ctype.get("name") or "").strip(),
                },
            )

        for rarity in data.get("rarities", []):
            Rarity.objects.update_or_create(
                myl_id=str(rarity.get("id")),
                defaults={
                    "slug": str(rarity.get("slug") or "").strip(),
                    "name": str(rarity.get("name") or "").strip(),
                },
            )

    def _build_api_cards(self, data: dict[str, Any]) -> list[ApiCard]:
        edition_info = data.get("edition", {})
        edition_slug = str(edition_info.get("slug") or "ayd_vigilantes").strip() or "ayd_vigilantes"

        rarity_by_id = {
            str(item.get("id")): str(item.get("slug") or "").strip()
            for item in data.get("rarities", [])
        }

        out: list[ApiCard] = []
        for raw in data.get("cards", []):
            edid = str(raw.get("edid") or "").strip()
            edid = edid.zfill(3) if edid.isdigit() else edid
            image_url = f"{API_CDN_BASE}/{edition_slug}/{edid}.png"

            out.append(
                ApiCard(
                    api_id=str(raw.get("id") or "").strip(),
                    edid=edid,
                    slug=str(raw.get("slug") or "").strip(),
                    name=str(raw.get("name") or "").strip(),
                    norm_name=_norm(raw.get("name")),
                    rarity_slug=rarity_by_id.get(str(raw.get("rarity")), ""),
                    race_id=(str(raw.get("race")) if raw.get("race") is not None else None),
                    type_id=(str(raw.get("type")) if raw.get("type") is not None else None),
                    cost=(str(raw.get("cost")) if raw.get("cost") is not None else None),
                    damage=(str(raw.get("damage")) if raw.get("damage") is not None else None),
                    ability=str(raw.get("ability") or "").strip(),
                    flavour=str(raw.get("flavour") or "").strip(),
                    image_url=image_url,
                )
            )
        return out

    def _is_image_protected(self, card: Card) -> bool:
        if (card.myl_id or "").startswith("cbg"):
            return True
        name_norm = _norm(card.name)
        return name_norm in PROTECTED_IMAGE_NAMES

    def _resolve_fk(self, api_card: ApiCard) -> tuple[Rarity | None, Race | None, CardType | None]:
        rarity = Rarity.objects.filter(slug=api_card.rarity_slug).first()
        race = Race.objects.filter(myl_id=api_card.race_id).first() if api_card.race_id else None
        card_type = CardType.objects.filter(myl_id=api_card.type_id).first() if api_card.type_id else None
        return rarity, race, card_type

    def _match_by_edid(self, card: Card, api_by_edid: dict[str, ApiCard]) -> tuple[ApiCard | None, float]:
        candidate = _extract_api_edid_candidate(card.edid)
        if not candidate:
            return None, 0.0
        api_card = api_by_edid.get(candidate)
        if not api_card:
            return None, 0.0
        local_norm = _norm(card.name)
        api_norm = api_card.norm_name
        score = _sim_ratio(local_norm, api_norm)
        # Bonificacion por edid exacto (deterministico).
        score = max(score, 0.93)
        return api_card, score

    def _update_card_from_api(
        self,
        card: Card,
        api_card: ApiCard,
        dry_run: bool,
    ) -> tuple[bool, bool, list[str]]:
        rarity, race, card_type = self._resolve_fk(api_card)

        changed_fields: list[str] = []

        target_pairs: list[tuple[str, Any]] = [
            ("rarity", rarity),
            ("race", race),
            ("card_type", card_type),
            ("cost", api_card.cost),
            ("damage", api_card.damage),
            ("ability", api_card.ability),
            ("flavour", api_card.flavour),
        ]

        image_changed = False
        protected = self._is_image_protected(card)
        if not protected and card.custom_image_url != api_card.image_url:
            target_pairs.append(("custom_image_url", api_card.image_url))
            image_changed = True

        for field, target in target_pairs:
            current = getattr(card, field)
            if current != target:
                setattr(card, field, target)
                changed_fields.append(field)

        if changed_fields and not dry_run:
            card.save(update_fields=changed_fields)

        return bool(changed_fields), image_changed, changed_fields

    def _create_card_from_api(self, edition: Edition, api_card: ApiCard, dry_run: bool) -> str:
        rarity, race, card_type = self._resolve_fk(api_card)

        # myl_id API primero; fallback custom si faltara.
        preferred_myl_id = api_card.api_id or f"custom_aydv_api_{api_card.edid}"
        final_myl_id = preferred_myl_id
        if Card.objects.filter(myl_id=preferred_myl_id).exists():
            final_myl_id = f"custom_aydv_api_{api_card.edid}_{preferred_myl_id}"

        defaults = {
            "myl_id": final_myl_id,
            "edid": api_card.edid,
            "slug": api_card.slug or f"aydv-{api_card.edid}",
            "name": api_card.name or f"AYDV {api_card.edid}",
            "edition": edition,
            "rarity": rarity,
            "race": race,
            "card_type": card_type,
            "cost": api_card.cost,
            "damage": api_card.damage,
            "ability": api_card.ability,
            "flavour": api_card.flavour,
            "custom_image_url": api_card.image_url,
        }

        if dry_run:
            return final_myl_id

        Card.objects.create(**defaults)
        return final_myl_id

    def handle(self, *args, **options):
        dry_run = bool(options["dry_run"])
        report_file = Path(options["report_file"]).expanduser().resolve()
        source = str(options["source"])
        source_file = Path(options["source_file"]).expanduser().resolve()
        aggressive_unmatched = bool(options["aggressive_unmatched"])

        edition = self._ensure_edition()
        data, source_used = self._load_source_data(source=source, source_file=source_file)
        self._sync_catalog_tables(data, dry_run=dry_run)
        api_cards = self._build_api_cards(data)

        local_cards = list(
            Card.objects.filter(edition=edition)
            .select_related("rarity", "race", "card_type")
            .order_by("id")
        )

        api_by_id = {api_card.api_id: api_card for api_card in api_cards}
        api_by_edid = {api_card.edid: api_card for api_card in api_cards}
        matched_api_ids: set[str] = set()

        updated_cards = 0
        updated_images = 0
        protected_images = 0
        unmatched_local = 0
        created_cards = 0

        details_updates: list[dict[str, Any]] = []
        details_unmatched_local: list[dict[str, Any]] = []
        details_created: list[dict[str, Any]] = []

        self.stdout.write(self.style.MIGRATE_HEADING("Sincronizando cartas AYDV con API oficial..."))

        for card in local_cards:
            api_match, score = self._match_by_edid(card, api_by_edid)
            if api_match is None:
                api_match, score = _best_match(card, api_cards)
            if api_match is None and aggressive_unmatched:
                api_match, score = _best_match_aggressive(card, api_cards)

            if api_match is None:
                unmatched_local += 1
                details_unmatched_local.append(
                    {
                        "card_id": card.id,
                        "myl_id": card.myl_id,
                        "edid": card.edid,
                        "name": card.name,
                        "reason": "no_confident_match",
                        "best_score": round(score, 4),
                    }
                )
                continue

            changed, image_changed, changed_fields = self._update_card_from_api(
                card=card,
                api_card=api_match,
                dry_run=dry_run,
            )
            matched_api_ids.add(api_match.api_id)

            if self._is_image_protected(card):
                protected_images += 1

            if changed:
                updated_cards += 1
                if image_changed:
                    updated_images += 1
                details_updates.append(
                    {
                        "card_id": card.id,
                        "myl_id": card.myl_id,
                        "edid": card.edid,
                        "name": card.name,
                        "api_id": api_match.api_id,
                        "api_edid": api_match.edid,
                        "api_name": api_match.name,
                        "score": round(score, 4),
                        "changed_fields": changed_fields,
                    }
                )

        # Crear faltantes de API que no quedaron representadas por ninguna carta local.
        for api_card in api_cards:
            if api_card.api_id in matched_api_ids:
                continue

            created_myl_id = self._create_card_from_api(
                edition=edition,
                api_card=api_card,
                dry_run=dry_run,
            )
            created_cards += 1
            details_created.append(
                {
                    "api_id": api_card.api_id,
                    "api_edid": api_card.edid,
                    "api_name": api_card.name,
                    "created_myl_id": created_myl_id,
                    "image_url": api_card.image_url,
                }
            )

        report = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "dry_run": dry_run,
            "source": {
                "requested": source,
                "used": source_used,
                "snapshot_file": str(source_file),
                "aggressive_unmatched": aggressive_unmatched,
            },
            "edition": {
                "id": edition.id,
                "slug": edition.slug,
                "myl_id": edition.myl_id,
            },
            "api": {
                "url": API_URL,
                "cards": len(api_cards),
            },
            "summary": {
                "local_cards": len(local_cards),
                "updated_cards": updated_cards,
                "updated_images": updated_images,
                "protected_images_seen": protected_images,
                "unmatched_local": unmatched_local,
                "created_cards": created_cards,
            },
            "updated": details_updates,
            "created": details_created,
            "unmatched_local": details_unmatched_local,
        }

        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        self.stdout.write(
            self.style.SUCCESS(
                "Done. "
                f"Updated={updated_cards} "
                f"(images={updated_images}) | "
                f"Created={created_cards} | "
                f"UnmatchedLocal={unmatched_local}"
            )
        )
        self.stdout.write(f"Reporte: {report_file}")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: no se guardaron cambios en BD."))