from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db.models import Q
from external_api import external_token, external_token_google, external_set_password, external_my_decks,external_decks, external_cards_by_format
from cards.views_admin import (
    cards_admin_dashboard,
    cards_admin_toggle_editions,
    cards_admin_season_new,
    cards_admin_season_edit,
    cards_admin_edition_new,
    cards_admin_edition_edit,
    cards_admin_edition_cards,
    cards_admin_card_new,
    cards_admin_card_edit,
    cards_admin_banlist_new,
    cards_admin_banlist_edit,
    cards_admin_banlist_delete,
    cards_admin_banlist,
    cards_admin_bulk_editions,
    cards_admin_bulk_cards,
    cards_admin_quick_search,
)
from riftbound.views_admin import (
    riftbound_admin_dashboard,
    riftbound_admin_toggle_sets,
    riftbound_admin_set_new,
    riftbound_admin_set_edit,
    riftbound_admin_set_cards,
    riftbound_admin_card_new,
    riftbound_admin_card_edit,
    riftbound_admin_banlist_new,
    riftbound_admin_banlist_edit,
    riftbound_admin_banlist_delete,
    riftbound_admin_banlist,
    riftbound_admin_bulk_sets,
    riftbound_admin_bulk_cards,
    riftbound_admin_search,
)


@api_view(["GET"])
@permission_classes([AllowAny])
def global_search(request):
    """Search cards, decks, users in one call. `game` selects myl (default) or riftbound."""
    q = request.query_params.get("q", "").strip()
    game = request.query_params.get("game", "myl").strip().lower()
    if len(q) < 2:
        return Response({"cards": [], "decks": [], "users": []})
    from django.contrib.auth import get_user_model
    User = get_user_model()

    if game == "riftbound":
        from riftbound.models import RiftboundCard, RiftboundDeck
        cards = list(
            RiftboundCard.objects.filter(name__icontains=q, is_active=True)
            .select_related("set")
            .values("id", "name", "card_number", "set__name")[:8]
        )
        decks = list(
            RiftboundDeck.objects.filter(is_public=True, name__icontains=q)
            .select_related("owner")
            .values("id", "name", "owner__username")[:8]
        )
    else:
        from cards.models import Card
        from decks.models import Deck
        cards = list(
            Card.objects.filter(name__icontains=q)
            .select_related("edition", "card_type")
            .values("id", "name", "edition__title", "card_type__name")[:8]
        )
        decks = list(
            Deck.objects.filter(is_public=True, name__icontains=q)
            .select_related("owner")
            .values("id", "name", "owner__username", "format", "race")[:8]
        )

    users = list(
        User.objects.filter(username__icontains=q)
        .values("id", "username")[:5]
    )
    return Response({"cards": cards, "decks": decks, "users": users})


urlpatterns = [
    path("admin/cards-tools/", cards_admin_dashboard, name="cards-admin-dashboard"),
    path("admin/cards-tools/toggle-editions/", cards_admin_toggle_editions, name="cards-admin-toggle-editions"),
    path("admin/cards-tools/seasons/new/", cards_admin_season_new, name="cards-admin-season-new"),
    path("admin/cards-tools/seasons/<int:season_id>/edit/", cards_admin_season_edit, name="cards-admin-season-edit"),
    path("admin/cards-tools/editions/new/", cards_admin_edition_new, name="cards-admin-edition-new"),
    path("admin/cards-tools/editions/<int:edition_id>/edit/", cards_admin_edition_edit, name="cards-admin-edition-edit"),
    path("admin/cards-tools/editions/<int:edition_id>/cards/", cards_admin_edition_cards, name="cards-admin-edition-cards"),
    path("admin/cards-tools/cards/new/", cards_admin_card_new, name="cards-admin-card-new"),
    path("admin/cards-tools/cards/<int:card_id>/edit/", cards_admin_card_edit, name="cards-admin-card-edit"),
    path("admin/cards-tools/banlist/new/", cards_admin_banlist_new, name="cards-admin-banlist-new"),
    path("admin/cards-tools/banlist/", cards_admin_banlist, name="cards-admin-banlist"),
    path("admin/cards-tools/banlist/<int:entry_id>/edit/", cards_admin_banlist_edit, name="cards-admin-banlist-edit"),
    path("admin/cards-tools/banlist/<int:entry_id>/delete/", cards_admin_banlist_delete, name="cards-admin-banlist-delete"),
    path("admin/cards-tools/bulk/editions/", cards_admin_bulk_editions, name="cards-admin-bulk-editions"),
    path("admin/cards-tools/bulk/cards/", cards_admin_bulk_cards, name="cards-admin-bulk-cards"),
    path("admin/cards-tools/search/", cards_admin_quick_search, name="cards-admin-search"),

    path("admin/riftbound-tools/", riftbound_admin_dashboard, name="riftbound-admin-dashboard"),
    path("admin/riftbound-tools/toggle-sets/", riftbound_admin_toggle_sets, name="riftbound-admin-toggle-sets"),
    path("admin/riftbound-tools/sets/new/", riftbound_admin_set_new, name="riftbound-admin-set-new"),
    path("admin/riftbound-tools/sets/<int:set_id>/edit/", riftbound_admin_set_edit, name="riftbound-admin-set-edit"),
    path("admin/riftbound-tools/sets/<int:set_id>/cards/", riftbound_admin_set_cards, name="riftbound-admin-set-cards"),
    path("admin/riftbound-tools/cards/new/", riftbound_admin_card_new, name="riftbound-admin-card-new"),
    path("admin/riftbound-tools/cards/<int:card_id>/edit/", riftbound_admin_card_edit, name="riftbound-admin-card-edit"),
    path("admin/riftbound-tools/banlist/", riftbound_admin_banlist, name="riftbound-admin-banlist"),
    path("admin/riftbound-tools/banlist/new/", riftbound_admin_banlist_new, name="riftbound-admin-banlist-new"),
    path("admin/riftbound-tools/banlist/<int:entry_id>/edit/", riftbound_admin_banlist_edit, name="riftbound-admin-banlist-edit"),
    path("admin/riftbound-tools/banlist/<int:entry_id>/delete/", riftbound_admin_banlist_delete, name="riftbound-admin-banlist-delete"),
    path("admin/riftbound-tools/bulk/sets/", riftbound_admin_bulk_sets, name="riftbound-admin-bulk-sets"),
    path("admin/riftbound-tools/bulk/cards/", riftbound_admin_bulk_cards, name="riftbound-admin-bulk-cards"),
    path("admin/riftbound-tools/search/", riftbound_admin_search, name="riftbound-admin-search"),

    path("admin/", admin.site.urls),
    path("api/auth/", include("users.urls")),
    path("api/cards/", include("cards.urls")),
    path("api/decks/", include("decks.urls")),
    path("api/teams/", include("teams.urls")),
    path("api/carpeta/", include("carpeta.urls")),
    path("api/wordle/", include("wordle.urls")),
    path("api/riftbound/", include("riftbound.urls")),
    path("api/search/", global_search, name="global-search"),
    # External API (para integraciones de terceros)
    path("api/external/token/", external_token, name="external-token"),
    path("api/external/token/google/", external_token_google, name="external-token-google"),
    path("api/external/set-password/", external_set_password, name="external-set-password"),
    path("api/external/my-decks/", external_my_decks, name="external-my-decks"),
    path("api/external/all-decks/", external_decks, name="external-decks"),
    path("api/external/cards/<str:format_code>/", external_cards_by_format, name="external-cards"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
