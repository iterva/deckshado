from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db.models import Q


@api_view(["GET"])
@permission_classes([AllowAny])
def global_search(request):
    """Search cards, decks, users in one call."""
    q = request.query_params.get("q", "").strip()
    if len(q) < 2:
        return Response({"cards": [], "decks": [], "users": []})
    from cards.models import Card
    from decks.models import Deck
    from django.contrib.auth import get_user_model
    User = get_user_model()
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
    path("admin/", admin.site.urls),
    path("api/auth/", include("users.urls")),
    path("api/cards/", include("cards.urls")),
    path("api/decks/", include("decks.urls")),
    path("api/teams/", include("teams.urls")),
    path("api/carpeta/", include("carpeta.urls")),
    path("api/wordle/", include("wordle.urls")),
    path("api/riftbound/", include("riftbound.urls")),
    path("api/search/", global_search, name="global-search"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
