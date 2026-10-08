import csv
import io
import re
from typing import Iterable

from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import slugify

from .models import COLOR_CHOICES, RiftboundBanlistEntry, RiftboundCard, RiftboundFormat, RiftboundSet


DOMAIN_CHOICES = [("", "---------")] + list(COLOR_CHOICES)
DOMAIN_ALLOWED = {code for code, _ in COLOR_CHOICES}


def _normalize_domain(value: str) -> str:
    token = str(value or "").strip().lower()
    return token if token in DOMAIN_ALLOWED else ""


def _extract_row_domains(row: dict[str, str]) -> list[str]:
    collected: list[str] = []

    def _append(raw: str):
        normalized = _normalize_domain(raw)
        if normalized and normalized not in collected:
            collected.append(normalized)

    # Soporte explícito de columnas de dominio recomendadas.
    _append(row.get("domain_1", ""))
    _append(row.get("domain_2", ""))

    # Compatibilidad con variantes históricas de columnas.
    _append(row.get("domain1", ""))
    _append(row.get("domain2", ""))
    _append(row.get("dominio_1", ""))
    _append(row.get("dominio_2", ""))

    # Compatibilidad con campo combinado (ej: "fury,calm").
    combined = row.get("domains", "") or row.get("colors", "")
    if combined:
        for token in re.split(r"[,;|/]", str(combined)):
            _append(token)

    return collected[:2]


class RiftboundSetForm(forms.ModelForm):
    class Meta:
        model = RiftboundSet
        fields = ["code", "name", "release_date"]


class RiftboundCardForm(forms.ModelForm):
    domain_1 = forms.ChoiceField(required=False, choices=DOMAIN_CHOICES, label="Dominio 1")
    domain_2 = forms.ChoiceField(required=False, choices=DOMAIN_CHOICES, label="Dominio 2")
    subtypes_text = forms.CharField(
        required=False,
        label="Subtipos",
        help_text="Separe los subtipos o tags con comas. Ejemplo: Akali, Champion Unit.",
    )

    class Meta:
        model = RiftboundCard
        fields = [
            "card_number",
            "name",
            "slug",
            "set",
            "card_type",
            "supertype",
            "rarity",
            "variant",
            "energy",
            "power",
            "might",
            "description",
            "flavor",
            "image_url",
            "image_url_small",
            "cdn_image_url",
            "source_url",
            "raw",
            "is_active",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current = [str(c).lower() for c in (getattr(self.instance, "colors", []) or []) if _normalize_domain(c)]
        self.fields["domain_1"].initial = current[0] if len(current) >= 1 else ""
        self.fields["domain_2"].initial = current[1] if len(current) >= 2 else ""
        self.fields["subtypes_text"].initial = ", ".join(getattr(self.instance, "subtypes", []) or [])
        self.fields["image_url"].label = "URL ImageKit / imagen principal"
        self.fields["cdn_image_url"].label = "URL Cloudinary / CDN alternativo"
        self.fields["raw"].widget = forms.Textarea(attrs={"rows": 6})

    def clean(self):
        cleaned = super().clean()
        d1 = _normalize_domain(cleaned.get("domain_1", ""))
        d2 = _normalize_domain(cleaned.get("domain_2", ""))
        if d1 and d2 and d1 == d2:
            raise ValidationError("No puede repetir el mismo dominio en Dominio 1 y Dominio 2.")
        cleaned["_domains_clean"] = [d for d in (d1, d2) if d]
        cleaned["_subtypes_clean"] = list(dict.fromkeys(
            subtype.strip()
            for subtype in (cleaned.get("subtypes_text") or "").split(",")
            if subtype.strip()
        ))
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.colors = self.cleaned_data.get("_domains_clean", [])
        instance.subtypes = self.cleaned_data.get("_subtypes_clean", [])
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class RiftboundBanlistEntryForm(forms.ModelForm):
    class Meta:
        model = RiftboundBanlistEntry
        fields = ["format", "card", "status", "max_copies", "note", "effective_from"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["card"].queryset = RiftboundCard.objects.order_by("name", "card_number")


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
        help_text="CSV de cartas. Requeridas: card_number,name,set_code. Opcionales: slug,card_type,rarity,energy,power,might,description,flavor,image_url,cdn_image_url,domain_1,domain_2,is_active"
    )
    images_zip_file = forms.FileField(
        required=False,
        help_text="Opcional: ZIP de imágenes descargadas (un solo archivo). Se prioriza esta fuente para subir a ImageKit.",
    )
    default_domain_1 = forms.ChoiceField(
        required=False,
        choices=DOMAIN_CHOICES,
        label="Dominio 1 por defecto",
        help_text="Se usa si la fila CSV no trae domain_1/domain_2.",
    )
    default_domain_2 = forms.ChoiceField(
        required=False,
        choices=DOMAIN_CHOICES,
        label="Dominio 2 por defecto",
        help_text="Opcional. No debe repetir Dominio 1.",
    )
    auto_create_missing_sets = forms.BooleanField(
        required=False,
        initial=True,
        label="Crear sets faltantes automáticamente",
        help_text="Si un set_code no existe (ej: VEN), se crea automáticamente con nombre igual al código.",
    )
    upload_images_to_imagekit = forms.BooleanField(required=False, initial=False)
    imagekit_folder = forms.CharField(required=False, max_length=255, initial="deckshado/riftbound/cards_admin_bulk")

    def clean(self):
        cleaned = super().clean()
        d1 = _normalize_domain(cleaned.get("default_domain_1", ""))
        d2 = _normalize_domain(cleaned.get("default_domain_2", ""))
        if d1 and d2 and d1 == d2:
            self.add_error("default_domain_2", "No puede repetir el mismo dominio.")
        cleaned["default_domains"] = [d for d in (d1, d2) if d]
        return cleaned


class SourceRiftboundGalleryForm(forms.Form):
    SOURCE_MODE_URL = "url"
    SOURCE_MODE_HTML_FILE = "html_file"
    SOURCE_MODE_HTML_TEXT = "html_text"

    SOURCE_MODE_CHOICES = [
        (SOURCE_MODE_URL, "Desde URL"),
        (SOURCE_MODE_HTML_FILE, "Desde archivo HTML"),
        (SOURCE_MODE_HTML_TEXT, "Pegando HTML"),
    ]

    source_mode = forms.ChoiceField(
        label="Modo de fuente",
        required=True,
        choices=SOURCE_MODE_CHOICES,
        initial=SOURCE_MODE_URL,
    )
    source_url = forms.URLField(
        label="URL fuente",
        required=False,
        initial="https://playriftbound.com/en-us/card-gallery/",
        help_text="Fuente soportada: playriftbound.com/en-us/card-gallery/",
    )
    source_html_file = forms.FileField(
        label="Archivo HTML",
        required=False,
        help_text="Útil cuando el servidor no puede abrir la URL por proxy/firewall.",
    )
    source_html_text = forms.CharField(
        label="HTML de la galería",
        required=False,
        widget=forms.Textarea(attrs={"rows": 6}),
        help_text="Pegue aquí el código fuente HTML de la galería.",
    )
    set_code = forms.CharField(
        label="Set code (filtro opcional)",
        required=False,
        max_length=10,
        help_text="Ejemplo: OGN, ARC. Deje vacío (o use TODOS) para incluir todas las cartas.",
    )
    max_cards = forms.IntegerField(
        label="Máximo de cartas a preparar",
        required=True,
        min_value=1,
        max_value=3000,
        initial=1200,
    )
    generate_bulk_csv = forms.BooleanField(
        label="Generar CSV para carga masiva",
        required=False,
        initial=True,
    )

    def clean(self):
        cleaned = super().clean()
        mode = (cleaned.get("source_mode") or "").strip()
        source_url = cleaned.get("source_url")
        source_html_file = cleaned.get("source_html_file")
        source_html_text = (cleaned.get("source_html_text") or "").strip()

        # Priorice automáticamente la fuente manual cuando existe,
        # aunque el selector haya quedado en "Desde URL".
        if source_html_file:
            mode = self.SOURCE_MODE_HTML_FILE
            cleaned["source_mode"] = mode
        elif source_html_text:
            mode = self.SOURCE_MODE_HTML_TEXT
            cleaned["source_mode"] = mode

        if mode == self.SOURCE_MODE_URL:
            if not source_url:
                self.add_error("source_url", "Debe indicar la URL de la galería.")
        elif mode == self.SOURCE_MODE_HTML_FILE:
            if not source_html_file:
                self.add_error("source_html_file", "Debe subir un archivo HTML.")
        elif mode == self.SOURCE_MODE_HTML_TEXT:
            if not source_html_text:
                self.add_error("source_html_text", "Debe pegar el HTML de la galería.")
        else:
            self.add_error("source_mode", "Modo de fuente no válido.")

        return cleaned


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


def upsert_card_row(
    row: dict[str, str],
    *,
    auto_create_missing_set: bool = False,
    set_cache: dict[str, RiftboundSet] | None = None,
    fallback_domains: list[str] | None = None,
) -> RiftboundCard:
    card_number = row.get("card_number", "").strip().upper()
    name = row.get("name", "").strip()
    set_code = row.get("set_code", "").strip().upper()

    if not card_number or not name or not set_code:
        raise ValidationError("Cada fila requiere card_number, name y set_code")

    set_obj = None
    if set_cache is not None:
        set_obj = set_cache.get(set_code)

    if not set_obj:
        set_obj = RiftboundSet.objects.filter(code=set_code).first()

    if not set_obj and auto_create_missing_set:
        set_obj = RiftboundSet.objects.create(code=set_code, name=set_code)

    if not set_obj:
        raise ValidationError(f"No existe set con código '{set_code}'")

    if set_cache is not None:
        set_cache[set_code] = set_obj

    card_type_allowed = {choice for choice, _ in RiftboundCard._meta.get_field("card_type").choices}
    rarity_allowed = {choice for choice, _ in RiftboundCard._meta.get_field("rarity").choices}
    row_domains = _extract_row_domains(row)
    if not row_domains and fallback_domains:
        row_domains = [d for d in fallback_domains if _normalize_domain(d)][:2]

    existing_card = RiftboundCard.objects.filter(card_number=card_number).only("image_url", "cdn_image_url").first()
    image_url_value = str(row.get("image_url") or "").strip()
    cdn_image_url_value = str(row.get("cdn_image_url") or "").strip()

    # Si el CSV no trae URL de imagen para una carta existente, no sobrescribir con vacío.
    if existing_card:
        if not image_url_value:
            image_url_value = existing_card.image_url
        if not cdn_image_url_value:
            cdn_image_url_value = existing_card.cdn_image_url

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
            "colors": row_domains,
            "image_url": image_url_value,
            "cdn_image_url": cdn_image_url_value,
            "is_active": str(row.get("is_active", "1")).lower() in {"1", "true", "yes", "si"},
        },
    )
    return card
