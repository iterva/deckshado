from rest_framework import generics, permissions
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Value, Case, When, BooleanField, TextField, Exists, OuterRef
from django.db.models.functions import Concat, Lower, Coalesce
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
import unicodedata
from .models import Card, Edition, Format, Race, CardType, Rarity, BanlistEntry
from .serializers import (
    CardListSerializer,
    CardDetailSerializer,
    EditionSerializer,
    FormatSerializer,
    RaceSerializer,
    CardTypeSerializer,
    RaritySerializer,
    BanlistEntrySerializer,
)

MYL_CARDS_CDN = "https://api.myl.cl/static/cards/"

# Ediciones que componen el formato virtual "Escuelas Elementales"
ESC_EDITION_SLUGS = [
    "bushido",
    "sol-naciente",
    "dominio",
    "contraataque",
    "aguila-imperial",
    "steampunk",
    "axis-mundi",
    "hijos-del-sol",
    "legado-gotico",
    "escuelas_elementales",
    "heroes_de_dharma",
]

# Multi-race deck archetypes (only for ESC format)
ESC_MULTI_RACE = {
    "culto-tenebris": ["sombra", "oni"],
    "vigilantes-etereos": ["eterno", "faerie"],
    "gremio-paladin": ["caballero", "sacerdote"],
    "clan-desafiante": ["dragon", "guerrero"],
}

# Map base vowels/consonants to regex classes that match accented variants
_ACCENT_MAP = {
    'a': '[aáàâãä]', 'e': '[eéèêë]', 'i': '[iíìîï]',
    'o': '[oóòôõö]', 'u': '[uúùûü]', 'n': '[nñ]',
}


def _accent_insensitive(text: str) -> str:
    """Convert search text to a regex pattern that matches with or without accents."""
    # Strip accents from search input first
    nfkd = unicodedata.normalize('NFKD', text.lower())
    stripped = ''.join(c for c in nfkd if not unicodedata.combining(c))
    return ''.join(_ACCENT_MAP.get(c, c) for c in stripped)


class CardPagination(PageNumberPagination):
    page_size = 20


class CardListView(generics.ListAPIView):
    serializer_class = CardListSerializer
    pagination_class = CardPagination
    permission_classes = [permissions.AllowAny]

    @method_decorator(cache_page(60 * 5))  # 5 min
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        qs = Card.objects.select_related("edition", "rarity", "race", "card_type").only(
            "id", "myl_id", "edid", "slug", "name", "cost", "damage", "ability",
            "custom_image_url",
            "edition__slug", "edition__title", "edition__myl_id",
            "rarity__name", "race__name", "race__slug", "card_type__name",
        ).annotate(
            image_url=Concat(
                Value(MYL_CARDS_CDN),
                "edition__myl_id", Value("/"), "edid", Value(".png"),
            ),
            is_unique=Case(
                When(ability__startswith="Única", then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            ),
        )
        edition = self.request.query_params.get("edition")
        card_type = self.request.query_params.get("type")
        race = self.request.query_params.get("race")
        rarity = self.request.query_params.get("rarity")
        search = self.request.query_params.get("search")
        fmt = self.request.query_params.get("fmt")

        if fmt:
            if fmt == "esc":
                qs = qs.filter(edition__slug__in=ESC_EDITION_SLUGS)
            else:
                qs = qs.filter(edition__format__code=fmt)
        if edition:
            ed_slugs = [s for s in edition.split(",") if s]
            if len(ed_slugs) == 1:
                qs = qs.filter(edition__slug=ed_slugs[0])
            elif ed_slugs:
                qs = qs.filter(edition__slug__in=ed_slugs)
        if card_type:
            type_slugs = [s for s in card_type.split(",") if s]
            if len(type_slugs) == 1:
                qs = qs.filter(card_type__slug=type_slugs[0])
            elif type_slugs:
                qs = qs.filter(card_type__slug__in=type_slugs)
        if race:
            qs = qs.filter(race__slug=race)
        if rarity:
            rar_slugs = [s for s in rarity.split(",") if s]
            if len(rar_slugs) == 1:
                qs = qs.filter(rarity__slug=rar_slugs[0])
            elif rar_slugs:
                qs = qs.filter(rarity__slug__in=rar_slugs)
        cost = self.request.query_params.get("cost")
        if cost is not None and cost != "":
            cost_vals = [c for c in cost.split(",") if c != ""]
            if len(cost_vals) == 1:
                qs = qs.filter(cost=cost_vals[0])
            elif cost_vals:
                qs = qs.filter(cost__in=cost_vals)
        if search:
            qs = qs.filter(name__iregex=_accent_insensitive(search))

        ability_search = self.request.query_params.get("ability_search")
        if ability_search:
            qs = qs.filter(ability__iregex=_accent_insensitive(ability_search))

        # Exclude editions (season rotation)
        exclude_editions = self.request.query_params.get("exclude_editions")
        if exclude_editions:
            ex_slugs = [s for s in exclude_editions.split(",") if s]
            if ex_slugs:
                qs = qs.exclude(edition__slug__in=ex_slugs)

        # VCR sub-format filter: vasallo, cortesano, real + promos with same name AND ability
        sub_fmt = self.request.query_params.get("sub_fmt")
        if sub_fmt == "vcr" and fmt == "imp":
            vcr_slugs = ["vasallo", "cortesano", "real"]
            # Promos with updated wording but same functional card
            vcr_promo_whitelist = [
                "laterna",
                "miguel grau",
                "caon naval",
                "abordaje",
                "monumento inmortal",
            ]
            # Subquery: exists a VCR card with same name and same ability
            vcr_match = Card.objects.filter(
                rarity__slug__in=vcr_slugs,
                name=OuterRef("name"),
            ).annotate(
                _safe_ability=Coalesce("ability", Value(""), output_field=TextField()),
            ).filter(
                _safe_ability=Coalesce(OuterRef("ability"), Value(""), output_field=TextField())
            )
            qs = qs.filter(
                Q(rarity__slug__in=vcr_slugs)
                | Q(rarity__slug="promo") & (Exists(vcr_match) | Q(name__in=vcr_promo_whitelist))
                | Q(card_type__slug="oro") & (Q(ability__isnull=True) | Q(ability=""))
            )

        # deck_race: MYL racial deck filter
        deck_race = self.request.query_params.get("deck_race")
        if deck_race and deck_race != "dream":
            # Non-allies (Oro, Arma, Talismán, Tótem) always pass
            non_ally = ~Q(card_type__slug="aliado")
            if deck_race == "totem":
                # Only raceless allies
                qs = qs.filter(non_ally | Q(race__isnull=True) | Q(race__slug="noraza"))
            elif deck_race in ESC_MULTI_RACE:
                # Multi-race ESC archetypes: allies matching ANY of the races
                race_q = Q()
                for r in ESC_MULTI_RACE[deck_race]:
                    race_q |= Q(race__slug__icontains=r)
                qs = qs.filter(non_ally | race_q)
            elif deck_race in ("luz", "oscuridad"):
                # Ability-based: first line of ability starts with Luz / Oscuridad
                keyword = "Luz" if deck_race == "luz" else "Oscuridad"
                qs = qs.filter(
                    non_ally
                    | Q(ability__istartswith=keyword)
                )
            else:
                # Matching race (including sub-races)
                qs = qs.filter(
                    non_ally
                    | Q(race__slug__icontains=deck_race)
                )

        # Default ordering: rarity priority (precomputed in DB), then edition, then edid
        qs = qs.order_by("rarity__display_order", "edition", "edid")

        return qs


class CardDetailView(generics.RetrieveAPIView):
    serializer_class = CardDetailSerializer
    queryset = Card.objects.select_related("edition", "rarity", "race", "card_type")
    lookup_field = "pk"
    permission_classes = [permissions.AllowAny]


class EditionListView(generics.ListAPIView):
    serializer_class = EditionSerializer
    pagination_class = None
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = Edition.objects.select_related("format").all()
        fmt = self.request.query_params.get("fmt")
        if fmt:
            if fmt == "esc":
                qs = qs.filter(slug__in=ESC_EDITION_SLUGS)
            else:
                qs = qs.filter(format__code=fmt)
        return qs


class FormatListView(generics.ListAPIView):
    serializer_class = FormatSerializer
    queryset = Format.objects.all()
    pagination_class = None
    permission_classes = [permissions.AllowAny]


class RaceListView(generics.ListAPIView):
    serializer_class = RaceSerializer
    queryset = Race.objects.all().order_by("name")
    permission_classes = [permissions.AllowAny]
    pagination_class = None


class CardTypeListView(generics.ListAPIView):
    serializer_class = CardTypeSerializer
    queryset = CardType.objects.all().order_by("name")
    pagination_class = None
    permission_classes = [permissions.AllowAny]


class RarityListView(generics.ListAPIView):
    serializer_class = RaritySerializer
    queryset = Rarity.objects.all()
    pagination_class = None
    permission_classes = [permissions.AllowAny]


class CardsByFormatView(generics.ListAPIView):
    """Return ALL cards for a given format code (no pagination).
    GET /api/cards/by-format/<format_code>/
    Examples: /api/cards/by-format/imp/  /api/cards/by-format/pb/
    """
    serializer_class = CardListSerializer
    pagination_class = None
    permission_classes = [permissions.AllowAny]

    @method_decorator(cache_page(60 * 10))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        format_code = self.kwargs["format_code"]
        if format_code == "esc":
            qs = Card.objects.filter(edition__slug__in=ESC_EDITION_SLUGS)
        else:
            qs = Card.objects.filter(edition__format__code=format_code)
        return qs.select_related("edition", "rarity", "race", "card_type").only(
            "id", "myl_id", "edid", "slug", "name", "cost", "damage", "ability",
            "custom_image_url",
            "edition__slug", "edition__title", "edition__myl_id",
            "rarity__name", "race__name", "race__slug", "card_type__name",
        ).annotate(
            image_url=Concat(
                Value(MYL_CARDS_CDN),
                "edition__myl_id", Value("/"), "edid", Value(".png"),
            ),
            is_unique=Case(
                When(ability__startswith="Única", then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            ),
        ).order_by("rarity__display_order", "edition", "edid")


class BanlistView(generics.ListAPIView):
    serializer_class = BanlistEntrySerializer
    pagination_class = None
    permission_classes = [permissions.AllowAny]

    @method_decorator(cache_page(60 * 5))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        qs = BanlistEntry.objects.select_related("card", "card__edition").all()
        fmt = self.request.query_params.get("fmt")
        sub = self.request.query_params.get("sub")
        if fmt:
            qs = qs.filter(format_code=fmt)
        if sub:
            qs = qs.filter(sub_format=sub)
        return qs
