from rest_framework import generics, permissions
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Value, Case, When, BooleanField, TextField, IntegerField, Exists, OuterRef
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

# Map base vowels/consonants to regex classes that match accented variants
_ACCENT_MAP = {
    'a': '[aáàâãä]', 'e': '[eéèêë]', 'i': '[iíìîï]',
    'o': '[oóòôõö]', 'u': '[uúùûü]', 'n': '[nñ]',
}

# Default rarity display order (lower = shown first)
RARITY_ORDER = {
    "milenaria": 1,
    "secreta": 2,
    "legendaria": 3,
    "promo": 4,
    "ultra-real": 5,
    "mega-real": 6,
    "real": 7,
    "vasallo": 8,
    "cortesano": 9,
    "oro": 10,
    "ficha": 11,
    "set_paralelo": 12,
}


def _accent_insensitive(text: str) -> str:
    """Convert search text to a regex pattern that matches with or without accents."""
    # Strip accents from search input first
    nfkd = unicodedata.normalize('NFKD', text.lower())
    stripped = ''.join(c for c in nfkd if not unicodedata.combining(c))
    return ''.join(_ACCENT_MAP.get(c, c) for c in stripped)


class CardPagination(PageNumberPagination):
    page_size = 20

    def paginate_queryset(self, queryset, request, view=None):
        # Caché el count para querysets con filtros idénticos
        if not hasattr(queryset, "_cached_count"):
            queryset._cached_count = queryset.count()
        self.total = queryset._cached_count
        return super().paginate_queryset(queryset, request, view)


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
            qs = qs.filter(edition__slug=edition)
        if card_type:
            qs = qs.filter(card_type__slug=card_type)
        if race:
            qs = qs.filter(race__slug=race)
        if rarity:
            qs = qs.filter(rarity__slug=rarity)
        cost = self.request.query_params.get("cost")
        if cost is not None and cost != "":
            qs = qs.filter(cost=cost)
        if search:
            qs = qs.filter(name__iregex=_accent_insensitive(search))

        ability_search = self.request.query_params.get("ability_search")
        if ability_search:
            qs = qs.filter(ability__iregex=_accent_insensitive(ability_search))

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
                "duelo a siete pasos - sp",
                "plaza de armas - sp",
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
            )

        # deck_race: MYL racial deck filter
        deck_race = self.request.query_params.get("deck_race")
        if deck_race and deck_race != "dream":
            # Non-allies (Oro, Arma, Talismán, Tótem) always pass
            non_ally = ~Q(card_type__name="Aliado")
            if deck_race == "totem":
                # Only raceless allies
                qs = qs.filter(non_ally | Q(race__isnull=True) | Q(race__slug="noraza"))
            else:
                # Matching race (including sub-races) + raceless allies
                qs = qs.filter(
                    non_ally
                    | Q(race__slug__icontains=deck_race)
                    | Q(race__isnull=True)
                    | Q(race__slug="noraza")
                )

        # Default ordering: rarity priority, then edition, then edid
        rarity_whens = [When(rarity__slug=slug, then=Value(order)) for slug, order in RARITY_ORDER.items()]
        qs = qs.annotate(
            rarity_order=Case(
                *rarity_whens,
                default=Value(99),
                output_field=IntegerField(),
            ),
        ).order_by("rarity_order", "edition", "edid")

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
