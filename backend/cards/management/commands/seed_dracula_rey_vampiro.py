"""
Seed Drácula: Rey Vampiro (edición completa publicada en el blog de MyL, punto 8 de
"Lo prometido, lo corregido y lo que falta: balance del formato Imperio").

  - Edición "Drácula: Rey Vampiro" (slug drac): DRAC-001..134 + legendarias alternativas
    (DRAC-110A..118A) + promos (DRAC-002P..063P).
  - Edición "Drácula: Set Inmortal" (slug inmdrac): INM-001..050.
  - Datos transcritos de las imágenes: data/dracula_rey_vampiro.json
  - Imágenes en ImageKit: dracula_imagekit_mapping.json (key -> url)

Uso:
    # Local (con cartas-dracula/ descargado y .env.imagekit): sube imágenes y siembra
    python manage.py seed_dracula_rey_vampiro --upload

    # Servidor (mapping ya commiteado): solo siembra
    python manage.py seed_dracula_rey_vampiro
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import requests
from django.core.management.base import BaseCommand, CommandError

from cards.models import Card, CardType, Edition, Format, Race, Rarity

from ._mapping_health import validate_mapping_urls
from .seed_mazo_guerreros import _load_upload_file


REPO_DIR = Path(__file__).resolve().parents[4]
DATA_FILE = Path(__file__).resolve().parent / "data" / "dracula_rey_vampiro.json"
DEFAULT_MAPPING_FILE = REPO_DIR / "dracula_imagekit_mapping.json"
DEFAULT_SOURCE_DIR = REPO_DIR / "cartas-dracula"
CDN_FOLDER = "deckshado/myl_cards/drac"
BLOG_UPLOADS = "https://blog.myl.cl/wp-content/uploads/2026/10/"

EDITIONS = {
    "drac": {
        "myl_id": "custom_drac",
        "title": "Drácula: Rey Vampiro",
        "cover_key": "drac_124",
    },
    "inmdrac": {
        "myl_id": "custom_inmdrac",
        "title": "Drácula: Set Inmortal",
        "cover_key": "inmdrac_001",
    },
}

# Algunas BDs tienen las rarezas con o sin guion; se usa la primera que exista.
RARITY_ALIASES = {
    "ultra-real": ["ultra-real", "ultrareal"],
    "mega-real": ["mega-real", "megareal"],
    "set-inmortal": ["set-inmortal", "inmortal"],
}

RACE_NAMES = {
    "bestia": "Bestia", "caballero": "Caballero", "dragon": "Dragón",
    "eterno": "Eterno", "faerie": "Faerie", "guerrero": "Guerrero",
    "heroe": "Héroe", "sacerdote": "Sacerdote", "sombra": "Sombra",
}


class Command(BaseCommand):
    help = "Seed Drácula: Rey Vampiro + Set Inmortal (255 cartas) con imágenes en ImageKit"

    def add_arguments(self, parser):
        parser.add_argument(
            "--upload",
            action="store_true",
            help="Sube a ImageKit las imágenes que falten en el mapping (requiere cartas-dracula/)",
        )
        parser.add_argument("--source-dir", default=str(DEFAULT_SOURCE_DIR))
        parser.add_argument("--mapping-file", default=str(DEFAULT_MAPPING_FILE))
        parser.add_argument(
            "--date-release",
            default=None,
            help="Fecha de lanzamiento (YYYY-MM-DD) para ambas ediciones",
        )
        parser.add_argument("--skip-url-check", action="store_true")
        parser.add_argument("--url-check-timeout", type=int, default=10)

    def handle(self, *args, **options):
        cards = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        mapping_file = Path(options["mapping_file"]).expanduser().resolve()
        mapping: dict[str, str] = {}
        if mapping_file.exists():
            mapping = json.loads(mapping_file.read_text(encoding="utf-8"))

        if options["upload"]:
            self._upload_missing(cards, mapping, Path(options["source_dir"]), mapping_file)

        missing = sorted(c["key"] for c in cards if not mapping.get(c["key"]))
        if missing:
            raise CommandError(
                f"Faltan {len(missing)} imágenes en {mapping_file.name}: "
                + ", ".join(missing[:10])
                + (" ..." if len(missing) > 10 else "")
                + ". Corre con --upload donde esté cartas-dracula/."
            )

        validate_mapping_urls(
            {c["key"]: mapping[c["key"]] for c in cards},
            self,
            "Drácula: Rey Vampiro",
            skip_check=options["skip_url_check"],
            timeout=max(1, options["url_check_timeout"]),
        )

        imp_format = Format.objects.get(code="imp")
        editions = {}
        for slug, spec in EDITIONS.items():
            defaults = {
                "slug": slug,
                "title": spec["title"],
                "image": mapping.get(spec["cover_key"], ""),
                "format": imp_format,
                "active": True,
            }
            if options["date_release"]:
                defaults["date_release"] = options["date_release"]
            edition, created = Edition.objects.update_or_create(
                myl_id=spec["myl_id"], defaults=defaults,
            )
            editions[slug] = edition
            self.stdout.write(self.style.SUCCESS(
                f"{'Created' if created else 'Updated'} edition: {edition.title}"
            ))

        types = {t.slug: t for t in CardType.objects.all()}
        rarities = {}
        for slug in {c["rarity_slug"] for c in cards}:
            rarities[slug] = self._resolve_rarity(slug)

        created_count = 0
        updated_count = 0
        for c in cards:
            card_type = types.get(c["type_slug"])
            if card_type is None:
                raise CommandError(f"No existe CardType '{c['type_slug']}' ({c['edid']})")

            card, was_created = Card.objects.update_or_create(
                myl_id=c["myl_id"],
                defaults={
                    "edid": c["edid"],
                    "slug": c["slug"],
                    "name": c["name"],
                    "edition": editions[c["edition"]],
                    "rarity": rarities[c["rarity_slug"]],
                    "race": self._resolve_race(c["race_slug"]),
                    "card_type": card_type,
                    "cost": c["cost"],
                    "damage": c["damage"],
                    "ability": c["ability"],
                    "flavour": "",
                    "imagekit_image_url": mapping[c["key"]],
                    "custom_image_url": mapping[c["key"]],
                },
            )
            if was_created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nDone! Created: {created_count}, Updated: {updated_count} ({len(cards)} total)"
        ))

    def _upload_missing(self, cards, mapping, source_dir: Path, mapping_file: Path):
        upload_file = _load_upload_file()
        os.environ["CDN_PROVIDER"] = "imagekit"
        source_dir.mkdir(parents=True, exist_ok=True)
        pending = [c for c in cards if not mapping.get(c["key"])]
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"Subiendo {len(pending)} imágenes a {os.environ['CDN_PROVIDER']} ({CDN_FOLDER})..."
        ))
        errors = 0
        for i, c in enumerate(pending, 1):
            path = source_dir / c["image_file"]
            try:
                if path.exists():
                    url = upload_file(str(path), public_id=f"{CDN_FOLDER}/{c['key']}", overwrite=True)
                else:
                    # Sin copia local (p. ej. PythonAnywhere, que bloquea blog.myl.cl):
                    # ImageKit descarga la imagen desde el blog por su cuenta.
                    url = self._imagekit_upload_from_url(BLOG_UPLOADS + c["image_file"], c["key"])
            except Exception as exc:  # noqa: BLE001 - seguir con el resto y guardar progreso
                self.stderr.write(f"  [{i}/{len(pending)}] ERROR {c['key']}: {exc}")
                errors += 1
                continue
            mapping[c["key"]] = url
            self.stdout.write(f"  [{i}/{len(pending)}] {c['key']} -> {url}")
            # Guardar tras cada subida: si se corta, la próxima corrida retoma.
            mapping_file.write_text(
                json.dumps(dict(sorted(mapping.items())), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        if errors:
            self.stderr.write(self.style.WARNING(f"{errors} imágenes no se pudieron subir."))

    def _imagekit_upload_from_url(self, source_url: str, key: str) -> str:
        from cdn_uploader import _collect_imagekit_accounts  # ya en sys.path vía _load_upload_file

        last_error = None
        for private_key, _endpoint in _collect_imagekit_accounts():
            resp = requests.post(
                "https://upload.imagekit.io/api/v1/files/upload",
                auth=(private_key, ""),
                data={
                    "file": source_url,
                    "fileName": f"{key}.png",
                    "folder": f"/{CDN_FOLDER}",
                    "useUniqueFileName": "false",
                    "overwriteFile": "true",
                },
                timeout=120,
            )
            if resp.status_code < 300 and resp.json().get("url"):
                return resp.json()["url"]
            last_error = f"ImageKit {resp.status_code}: {resp.text[:200]}"
            if "upload limit exceeded" not in resp.text.lower():
                break
        raise RuntimeError(last_error)

    def _resolve_rarity(self, slug: str):
        for candidate in RARITY_ALIASES.get(slug, [slug]):
            rarity = Rarity.objects.filter(slug=candidate).first()
            if rarity:
                return rarity
        self.stderr.write(self.style.WARNING(f"Rareza '{slug}' no existe; cartas quedan sin rareza."))
        return None

    def _resolve_race(self, slug: str | None):
        if not slug:
            return None
        race = Race.objects.filter(slug=slug).first()
        if race:
            return race
        # Razas compuestas (p. ej. "caballero/heroe"): el filtro de mazo racial usa
        # race__slug__icontains, así que basta con crear la combinación.
        name = " / ".join(RACE_NAMES.get(part, part.title()) for part in slug.split("/"))
        myl_id = "c_" + hashlib.md5(slug.encode()).hexdigest()[:8]
        race, _ = Race.objects.get_or_create(myl_id=myl_id, defaults={"slug": slug, "name": name})
        return race
