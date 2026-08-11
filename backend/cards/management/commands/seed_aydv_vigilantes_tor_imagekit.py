"""Carga cartas promocionales AYDV desde la API oficial a ImageKit y las siembra.

Uso local:
  python manage.py seed_aydv_vigilantes_tor_imagekit

Uso en PythonAnywhere, despues de versionar el mapping generado:
  python manage.py seed_aydv_vigilantes_tor_imagekit --apply-mapping-only
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import requests
from django.core.management.base import BaseCommand, CommandError

from cards.models import Card, CardType, Edition, Format, Race, Rarity


API_PROFILE_BASE = "https://api.myl.cl/cards/profile/ayd_vigilantes"
API_IMAGE_BASE = "https://api.myl.cl/static/cards/166"
UPLOAD_ENDPOINT = "https://upload.imagekit.io/api/v1/files/upload"
DEFAULT_ENV_FILE = Path(__file__).resolve().parents[5] / ".env_imagekit copy"
DEFAULT_MAPPING_FILE = Path(__file__).resolve().parents[4] / "aydv_vigilantes_tor_imagekit_mapping.json"
DEFAULT_FOLDER = "/deckshado/myl_cards/aydv_vigilantes_tor_2026_08"

REQUESTED_SLUGS = (
    "lanza_de_exorcista",
    "incensario_serafico",
    "jugando_con_el_demonio",
    "aniquilar_titanes",
    "colapso_global",
    "acabar_la_esperanza",
    "duelo_espacial",
    "activar_tenshi_z",
    "transformacion",
    "diadema_celestial",
    "guerrillero_rodriguez",
    "angelus",
    "quantum_megumi",
    "estrella_de_kirin",
    "espada_divina",
    "lucha_celestial",
    "los_olvidados",
    "sacrificio_solar",
    "canon_helios",
    "fision_nuclear",
    "paladin_de_la_luz",
    "escritura_sagrada",
    "lucifer,_el_caido",
    "angel_miguel,_el_protector",
    "tentaciones_divinas",
)

PROFILE_FALLBACKS = {
    "angel_miguel,_el_protector": {
        "myl_id": "21656",
        "edid": "AYDV-246-P",
        "name": "Ángel Miguel, el Protector",
        "rarity": "Promo",
        "race": "",
        "card_type": "Aliado",
        "cost": "2",
        "damage": "3",
        "ability": (
            "Indestructible.\n"
            "Cuando entra en juego o bloquee, Baraja y/o Destierra hasta seis cartas de los Cementerios.\n"
            "Si controlas o jugaste Tótem en tu turno anterior, los Aliados oponentes de coste 2 o menos no disparan sus habilidades al entrar en juego."
        ),
        "flavour": "Príncipe de las huestes celestes, guardián del orden y azote de los rebeldes. Su espada no vacila, y bajo sus alas se preserva la esperanza de los justos.",
        "source_image_url": "https://api.myl.cl/static/cards/166/299.png",
    },
    "lucifer,_el_caido": {
        "myl_id": "21657",
        "edid": "AYDV-247-P",
        "name": "Lucifer, el Caído",
        "rarity": "Promo",
        "race": "",
        "card_type": "Aliado",
        "cost": "3",
        "damage": "5",
        "ability": (
            "Exhumar. Indesterrable.\n"
            "Cuando entra en juego, Destierra todos los Aliados oponentes.\n"
            "Cuando un Oro o una carta de un Cementerio entre en juego bajo tu control, dos veces por turno, una carta en juego o en el Cementerio pierde su habilidad hasta tu próximo turno."
        ),
        "flavour": "Portador de luz vuelto abismo, soberano de la belleza corrompida y del orgullo sin redención. Su caída estremeció los cielos, y su nombre aún arde en la memoria del castigo.",
        "source_image_url": "https://api.myl.cl/static/cards/166/300.png",
    },
}


def _norm(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", (value or "").strip())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        raise CommandError(f"No existe env file: {path}")

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


class Command(BaseCommand):
    help = "Sube 25 cartas AYDV de TOR/MYL a ImageKit y realiza upsert en AYDV"

    def add_arguments(self, parser):
        parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
        parser.add_argument("--mapping-file", default=str(DEFAULT_MAPPING_FILE))
        parser.add_argument("--folder", default=DEFAULT_FOLDER)
        parser.add_argument("--apply-mapping-only", action="store_true")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--requested-slug",
            action="append",
            choices=REQUESTED_SLUGS,
            help="Procesa solo el slug indicado; se puede repetir.",
        )

    def _ensure_edition(self) -> Edition:
        card_format, _ = Format.objects.get_or_create(code="imp", defaults={"name": "Imperio"})
        edition, _ = Edition.objects.update_or_create(
            myl_id="custom_aydv",
            defaults={
                "slug": "aydv",
                "title": "Angeles y Demonios: Vigilantes",
                "format": card_format,
                "active": True,
            },
        )
        return edition

    def _load_mapping(self, mapping_file: Path) -> list[dict[str, Any]]:
        if not mapping_file.exists():
            raise CommandError(f"No existe mapping file: {mapping_file}")
        try:
            payload = json.loads(mapping_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CommandError(f"JSON invalido en mapping file: {exc}") from exc

        records = payload.get("records")
        if not isinstance(records, list) or not records:
            raise CommandError("El mapping no contiene una lista no vacia en 'records'.")
        return records

    def _fetch_record(self, requested_slug: str) -> tuple[dict[str, Any], bytes]:
        profile_url = f"{API_PROFILE_BASE}/{requested_slug}"
        try:
            profile_response = requests.get(profile_url, timeout=45)
            profile_response.raise_for_status()
            profile = profile_response.json()
        except (requests.RequestException, ValueError) as exc:
            raise CommandError(f"No se pudo obtener {requested_slug}: {exc}") from exc

        details = profile.get("details") if isinstance(profile, dict) else None
        if profile.get("status") != "OK" or not isinstance(details, dict):
            raise CommandError(f"Respuesta invalida para {requested_slug}")

        edid = str(details.get("edid") or "").strip()
        api_id = str(details.get("id") or "").strip()
        if not edid or not api_id:
            raise CommandError(f"Faltan id/edid para {requested_slug}")

        image_url = f"{API_IMAGE_BASE}/{edid}.png"
        try:
            image_response = requests.get(image_url, timeout=60)
            image_response.raise_for_status()
        except requests.RequestException as exc:
            raise CommandError(f"No se pudo descargar imagen {image_url}: {exc}") from exc

        image_bytes = image_response.content
        if not image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            raise CommandError(f"La imagen de {requested_slug} no es un PNG valido: {image_url}")

        return {
            "requested_slug": requested_slug,
            "myl_id": api_id,
            "edid": edid,
            "slug": str(details.get("slug") or requested_slug).strip(),
            "name": str(details.get("name") or "").strip(),
            "rarity": str(details.get("rarity") or "").strip(),
            "race": str(details.get("race") or "").strip(),
            "card_type": str(details.get("type") or "").strip(),
            "cost": details.get("cost"),
            "damage": details.get("damage"),
            "ability": details.get("ability"),
            "flavour": details.get("flavour"),
            "source_image_url": image_url,
        }, image_bytes

    def _fetch_fallback_record(self, requested_slug: str) -> tuple[dict[str, Any], bytes]:
        record = PROFILE_FALLBACKS[requested_slug].copy()
        try:
            image_response = requests.get(record["source_image_url"], timeout=60)
            image_response.raise_for_status()
        except requests.RequestException as exc:
            raise CommandError(f"No se pudo descargar imagen fallback de {requested_slug}: {exc}") from exc

        image_bytes = image_response.content
        if not image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            raise CommandError(f"La imagen fallback de {requested_slug} no es un PNG valido")

        record["requested_slug"] = requested_slug
        record["slug"] = requested_slug
        return record, image_bytes

    def _resolve_by_slug_or_name(self, model, value: str):
        if not value:
            return None
        normalized = _norm(value)
        return model.objects.filter(slug=normalized).first() or model.objects.filter(name__iexact=value).first()

    def _upsert(self, edition: Edition, record: dict[str, Any], dry_run: bool) -> str:
        required = ("myl_id", "edid", "slug", "name", "imagekit_url")
        if any(not str(record.get(key) or "").strip() for key in required):
            raise CommandError(f"Registro incompleto en mapping: {record.get('requested_slug', '<sin slug>')}")

        rarity = self._resolve_by_slug_or_name(Rarity, str(record.get("rarity") or ""))
        card_type = self._resolve_by_slug_or_name(CardType, str(record.get("card_type") or ""))
        race = self._resolve_by_slug_or_name(Race, str(record.get("race") or ""))
        if record.get("rarity") and rarity is None:
            raise CommandError(f"Rareza no encontrada: {record['rarity']} ({record['name']})")
        if record.get("card_type") and card_type is None:
            raise CommandError(f"Tipo no encontrado: {record['card_type']} ({record['name']})")

        defaults = {
            "myl_id": str(record["myl_id"]),
            "edid": str(record["edid"]),
            "slug": str(record["slug"]),
            "name": str(record["name"]),
            "edition": edition,
            "rarity": rarity,
            "race": race,
            "card_type": card_type,
            "cost": str(record["cost"]) if record.get("cost") is not None else None,
            "damage": str(record["damage"]) if record.get("damage") is not None else None,
            "ability": record.get("ability") or None,
            "flavour": record.get("flavour") or None,
            "custom_image_url": str(record["imagekit_url"]),
        }
        card = Card.objects.filter(myl_id=defaults["myl_id"]).first()
        if card is None:
            card = Card.objects.filter(edition=edition, edid=defaults["edid"]).order_by("id").first()

        if card is None:
            if not dry_run:
                Card.objects.create(**defaults)
            return "WOULD_CREATE" if dry_run else "CREATED"

        changed = [key for key, value in defaults.items() if getattr(card, key) != value]
        if not changed:
            return "KEEP"
        if not dry_run:
            for key in changed:
                setattr(card, key, defaults[key])
            card.save(update_fields=changed)
        return "WOULD_UPDATE" if dry_run else "UPDATED"

    def handle(self, *args, **options):
        mapping_file = Path(options["mapping_file"]).expanduser().resolve()
        dry_run = bool(options["dry_run"])
        edition = self._ensure_edition()

        failures: list[dict[str, str]] = []
        if options["apply_mapping_only"]:
            records = self._load_mapping(mapping_file)
        else:
            env_values = _parse_env_file(Path(options["env_file"]).expanduser().resolve())
            private_key = (env_values.get("IMAGEKIT_PRIVATE_KEY") or env_values.get("private_key") or "").strip()
            if not private_key:
                raise CommandError("No se encontro IMAGEKIT_PRIVATE_KEY/private_key en el env file")

            folder = str(options["folder"]).strip() or DEFAULT_FOLDER
            records = []
            requested_slugs = tuple(options["requested_slug"] or REQUESTED_SLUGS)
            for requested_slug in requested_slugs:
                try:
                    record, image_bytes = self._fetch_record(requested_slug)
                except CommandError as exc:
                    if requested_slug not in PROFILE_FALLBACKS:
                        failures.append({"requested_slug": requested_slug, "error": str(exc)})
                        self.stdout.write(self.style.WARNING(f"SKIP: {exc}"))
                        continue
                    self.stdout.write(self.style.WARNING(f"FALLBACK: {exc}"))
                    record, image_bytes = self._fetch_fallback_record(requested_slug)
                public_id = f"aydv_{record['edid']}_{_norm(record['name'])}"
                if dry_run:
                    record["imagekit_url"] = f"https://ik.imagekit.io/<endpoint>/{folder.strip('/')}/{public_id}.png"
                else:
                    response = requests.post(
                        UPLOAD_ENDPOINT,
                        auth=(private_key, ""),
                        files={"file": (f"{public_id}.png", image_bytes, "image/png")},
                        data={
                            "fileName": f"{public_id}.png",
                            "folder": folder,
                            "useUniqueFileName": "false",
                            "overwriteFile": "true",
                            "isPrivateFile": "false",
                        },
                        timeout=90,
                    )
                    if response.status_code >= 300:
                        raise CommandError(f"ImageKit fallo para {record['name']}: {response.text[:400]}")
                    record["imagekit_url"] = str(response.json().get("url") or "").strip()
                    if not record["imagekit_url"]:
                        raise CommandError(f"ImageKit no devolvio URL para {record['name']}")
                record["public_id"] = public_id
                records.append(record)

            if not dry_run:
                if options["requested_slug"] and mapping_file.exists():
                    existing_payload = json.loads(mapping_file.read_text(encoding="utf-8"))
                    existing_records = existing_payload.get("records") or []
                    records_by_myl_id = {
                        str(item.get("myl_id")): item
                        for item in existing_records
                        if isinstance(item, dict) and item.get("myl_id")
                    }
                    for record in records:
                        records_by_myl_id[str(record["myl_id"])] = record
                    records = list(records_by_myl_id.values())
                    failures = [
                        item for item in (existing_payload.get("failures") or [])
                        if item.get("requested_slug") not in requested_slugs
                    ] + failures
                mapping_file.write_text(
                    json.dumps(
                        {
                            "kind": "aydv_vigilantes_tor_imagekit",
                            "folder": folder,
                            "records": records,
                            "failures": failures,
                        },
                        indent=2,
                        ensure_ascii=False,
                    ) + "\n",
                    encoding="utf-8",
                )

        counters = {"CREATED": 0, "UPDATED": 0, "KEEP": 0, "WOULD_CREATE": 0, "WOULD_UPDATE": 0}
        for record in records:
            status = self._upsert(edition, record, dry_run)
            counters[status] += 1
            self.stdout.write(f"{status}: {record['name']} ({record['edid']})")

        self.stdout.write(self.style.SUCCESS(
            f"Done. Records={len(records)} Failures={len(failures)} Counters={counters} Mapping={mapping_file}"
        ))