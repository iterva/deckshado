import csv
import io
import os
from dataclasses import dataclass
from typing import Iterable

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.text import slugify

from .models import BanlistEntry, Card, CardType, Edition, Format, Race, Rarity, Season


class SeasonForm(forms.ModelForm):
    class Meta:
        model = Season
        fields = ["code", "name", "start_date", "end_date", "is_active"]


class EditionForm(forms.ModelForm):
    class Meta:
        model = Edition
        fields = [
            "myl_id",
            "slug",
            "title",
            "image",
            "date_release",
            "date_empire_valid",
            "season",
            "format",
            "active",
        ]


class CardForm(forms.ModelForm):
    class Meta:
        model = Card
        fields = [
            "myl_id",
            "edid",
            "slug",
            "name",
            "edition",
            "rarity",
            "race",
            "card_type",
            "cost",
            "damage",
            "ability",
            "flavour",
            "custom_image_url",
        ]


class BanlistEntryForm(forms.ModelForm):
    class Meta:
        model = BanlistEntry
        fields = ["card_name", "card", "format_code", "sub_format", "status", "max_copies"]


class ToggleEditionsForm(forms.Form):
    format = forms.ModelChoiceField(
        queryset=Format.objects.all(),
        required=False,
        help_text="Opcional: filtrar por formato para activar/desactivar en bloque.",
    )
    edition_ids = forms.ModelMultipleChoiceField(
        queryset=Edition.objects.select_related("format").all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    active = forms.BooleanField(required=False, initial=True, label="Marcar como activa")


class SessionImagekitEnvForm(forms.Form):
    env_file = forms.FileField(
        required=False,
        help_text="Suba archivo .env de la sesión. Solo se aceptan public_key, private_key y url.",
    )


class BulkEditionCsvForm(forms.Form):
    csv_file = forms.FileField(help_text="CSV con columnas mínimas: myl_id,slug,title")


class BulkCardCsvForm(forms.Form):
    csv_file = forms.FileField(
        help_text="CSV de cartas. Requeridas: myl_id,edid,name,edition_slug. Opcionales: type_slug,race_slug,rarity_slug,cost,damage,ability,flavour,image_url"
    )
    upload_images_to_imagekit = forms.BooleanField(required=False, initial=False)
    imagekit_folder = forms.CharField(required=False, max_length=255, initial="deckshado/myl_cards/admin_bulk")


@dataclass
class ImagekitSessionEnv:
    public_key: str
    private_key: str
    url_endpoint: str


_ALLOWED_ENV_KEYS = {"public_key", "private_key", "url"}


def parse_session_env(env_bytes: bytes) -> ImagekitSessionEnv:
    text = env_bytes.decode("utf-8", errors="replace")
    data: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key not in _ALLOWED_ENV_KEYS:
            continue
        value = value.strip().strip('"').strip("'")
        data[key] = value

    missing = [k for k in _ALLOWED_ENV_KEYS if not data.get(k)]
    if missing:
        raise ValidationError(f"Archivo env inválido. Faltan variables: {', '.join(sorted(missing))}")

    return ImagekitSessionEnv(
        public_key=data["public_key"],
        private_key=data["private_key"],
        url_endpoint=data["url"].rstrip("/"),
    )


def csv_rows(file_obj) -> Iterable[dict[str, str]]:
    raw = file_obj.read()
    text = raw.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        normalized: dict[str, str] = {}
        for key, value in row.items():
            if key is None:
                continue
            normalized[key.strip()] = (value or "").strip()
        yield normalized


def upsert_edition_row(row: dict[str, str]) -> Edition:
    myl_id = row.get("myl_id", "")
    slug = row.get("slug", "") or slugify(row.get("title", ""))
    title = row.get("title", "")
    if not myl_id or not slug or not title:
        raise ValidationError("Cada fila debe incluir myl_id, slug y title")

    format_obj = None
    format_code = row.get("format_code", "")
    if format_code:
        format_obj = Format.objects.filter(code=format_code).first()

    season_obj = None
    season_code = row.get("season_code", "")
    if season_code:
        season_obj = Season.objects.filter(code=season_code).first()

    edition, _ = Edition.objects.update_or_create(
        myl_id=myl_id,
        defaults={
            "slug": slug,
            "title": title,
            "image": row.get("image") or None,
            "format": format_obj,
            "season": season_obj,
            "active": str(row.get("active", "1")).lower() in {"1", "true", "yes", "si"},
        },
    )
    return edition


def _card_slug(name: str, edid: str) -> str:
    base = slugify(name)
    return f"{base}-{edid}" if edid else base


def upsert_card_row(row: dict[str, str]) -> Card:
    myl_id = row.get("myl_id", "")
    edid = row.get("edid", "")
    name = row.get("name", "")
    edition_slug = row.get("edition_slug", "")
    if not myl_id or not edid or not name or not edition_slug:
        raise ValidationError("Cada fila de carta requiere myl_id, edid, name, edition_slug")

    edition = Edition.objects.filter(slug=edition_slug).first()
    if not edition:
        raise ValidationError(f"No existe edición con slug '{edition_slug}'")

    card_type = CardType.objects.filter(slug=row.get("type_slug", "")).first() if row.get("type_slug") else None
    race = Race.objects.filter(slug=row.get("race_slug", "")).first() if row.get("race_slug") else None
    rarity = Rarity.objects.filter(slug=row.get("rarity_slug", "")).first() if row.get("rarity_slug") else None

    card, _ = Card.objects.update_or_create(
        myl_id=myl_id,
        defaults={
            "edid": edid,
            "slug": row.get("slug") or _card_slug(name, edid),
            "name": name,
            "edition": edition,
            "card_type": card_type,
            "race": race,
            "rarity": rarity,
            "cost": row.get("cost") or None,
            "damage": row.get("damage") or None,
            "ability": row.get("ability") or None,
            "flavour": row.get("flavour") or None,
            "custom_image_url": row.get("custom_image_url") or row.get("image_url") or None,
        },
    )
    return card


def default_allowed_image_hosts() -> set[str]:
    hosts = {
        "ik.imagekit.io",
        "api.myl.cl",
        "res.cloudinary.com",
    }
    configured = os.environ.get("ADMIN_BULK_ALLOWED_IMAGE_HOSTS", "")
    if configured.strip():
        hosts.update(h.strip().lower() for h in configured.split(",") if h.strip())
    return hosts
