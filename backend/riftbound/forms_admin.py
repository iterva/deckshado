import csv
import io
from typing import Iterable

from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import slugify

from .models import RiftboundBanlistEntry, RiftboundCard, RiftboundFormat, RiftboundSet


class RiftboundSetForm(forms.ModelForm):
    class Meta:
        model = RiftboundSet
        fields = ["code", "name", "release_date"]


class RiftboundCardForm(forms.ModelForm):
    class Meta:
        model = RiftboundCard
        fields = [
            "card_number",
            "name",
            "slug",
            "set",
            "card_type",
            "rarity",
            "variant",
            "energy",
            "power",
            "might",
            "description",
            "flavor",
            "image_url",
            "cdn_image_url",
            "is_active",
        ]


class RiftboundBanlistEntryForm(forms.ModelForm):
    class Meta:
        model = RiftboundBanlistEntry
        fields = ["format", "card", "status", "max_copies", "note", "effective_from"]


class ToggleRiftboundSetsForm(forms.Form):
    set_ids = forms.ModelMultipleChoiceField(
        queryset=RiftboundSet.objects.all().order_by("code"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    active = forms.BooleanField(required=False, initial=True, label="Marcar cartas de estos sets como activas")


class BulkRiftboundSetCsvForm(forms.Form):
    csv_file = forms.FileField(help_text="CSV con columnas mínimas: code,name")


class BulkRiftboundCardCsvForm(forms.Form):
    csv_file = forms.FileField(
        help_text="CSV de cartas. Requeridas: card_number,name,set_code. Opcionales: slug,card_type,rarity,energy,power,might,description,flavor,image_url,cdn_image_url,is_active"
    )
    upload_images_to_imagekit = forms.BooleanField(required=False, initial=False)
    imagekit_folder = forms.CharField(required=False, max_length=255, initial="deckshado/riftbound/cards_admin_bulk")


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


def upsert_set_row(row: dict[str, str]) -> RiftboundSet:
    code = row.get("code", "").strip().upper()
    name = row.get("name", "").strip()
    if not code or not name:
        raise ValidationError("Cada fila debe incluir code y name")

    set_obj, _ = RiftboundSet.objects.update_or_create(
        code=code,
        defaults={
            "name": name,
            "release_date": row.get("release_date") or None,
        },
    )
    return set_obj


def _to_int(value: str):
    value = (value or "").strip()
    if not value:
        return None
    return int(value)


def _normalize_choice(value: str, allowed: set[str], default: str) -> str:
    normalized = (value or "").strip().lower()
    return normalized if normalized in allowed else default


def upsert_card_row(row: dict[str, str]) -> RiftboundCard:
    card_number = row.get("card_number", "").strip().upper()
    name = row.get("name", "").strip()
    set_code = row.get("set_code", "").strip().upper()

    if not card_number or not name or not set_code:
        raise ValidationError("Cada fila requiere card_number, name y set_code")

    set_obj = RiftboundSet.objects.filter(code=set_code).first()
    if not set_obj:
        raise ValidationError(f"No existe set con código '{set_code}'")

    card_type_allowed = {choice for choice, _ in RiftboundCard._meta.get_field("card_type").choices}
    rarity_allowed = {choice for choice, _ in RiftboundCard._meta.get_field("rarity").choices}

    card, _ = RiftboundCard.objects.update_or_create(
        card_number=card_number,
        defaults={
            "name": name,
            "slug": row.get("slug") or slugify(f"{name}-{card_number.lower()}"),
            "set": set_obj,
            "card_type": _normalize_choice(row.get("card_type", ""), card_type_allowed, "unit"),
            "rarity": _normalize_choice(row.get("rarity", ""), rarity_allowed, "common"),
            "variant": row.get("variant", ""),
            "energy": _to_int(row.get("energy", "")),
            "power": _to_int(row.get("power", "")),
            "might": _to_int(row.get("might", "")),
            "description": row.get("description", ""),
            "flavor": row.get("flavor", ""),
            "image_url": row.get("image_url", ""),
            "cdn_image_url": row.get("cdn_image_url", ""),
            "is_active": str(row.get("is_active", "1")).lower() in {"1", "true", "yes", "si"},
        },
    )
    return card
