from rest_framework import generics, permissions
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Value, Case, When, BooleanField
from django.db.models.functions import Concat, Lower
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
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
            "edition__slug", "edition__title", "edition__myl_id",
            "rarity__name", "race__name", "card_type__name",
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
            qs = qs.filter(edition__format__code=fmt)
        if edition:
            qs = qs.filter(edition__slug=edition)
        if card_type:
            qs = qs.filter(card_type__slug=card_type)
        if race:
            qs = qs.filter(race__slug=race)
        if rarity:
            qs = qs.filter(rarity__slug=rarity)
        if search:
            qs = qs.filter(name__icontains=search)

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
                    | Q(race__name__icontains=deck_race)
                    | Q(race__isnull=True)
                    | Q(race__slug="noraza")
                )

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
