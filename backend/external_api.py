"""
API Externa — Endpoints simplificados para integraciones de terceros.

Endpoints:
  POST /api/external/token/       → Login con username/password → devuelve token
  GET  /api/external/my-decks/    → Mazos del usuario autenticado (con cartas)
  GET  /api/external/cards/<fmt>/ → Todas las cartas de un formato (público)

Uso:
  1. Obtener token:
     POST /api/external/token/
     Body: {"username": "tu_usuario", "password": "tu_contraseña"}
     Response: {"access": "...", "refresh": "...", "user": {"id": 1, "username": "..."}}

  2. Usar token en headers:
     Authorization: Bearer <access_token>

  3. Consultar mazos:
     GET /api/external/my-decks/
     GET /api/external/my-decks/?format=imp

  4. Consultar cartas por formato:
     GET /api/external/cards/imp/
     GET /api/external/cards/pb/
     GET /api/external/cards/esc/
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Value, Case, When, BooleanField, Sum
from django.db.models.functions import Concat

from cards.models import Card, Edition
from cards.views import ESC_EDITION_SLUGS, MYL_CARDS_CDN, HIDDEN_CARD_FORMAT_CODES
from decks.models import Deck, DeckEntry


@api_view(["POST"])
@permission_classes([AllowAny])
def external_token(request):
    """Login con username y password. Devuelve tokens JWT + info del usuario."""
    username = request.data.get("username", "").strip()
    password = request.data.get("password", "")

    if not username or not password:
        return Response(
            {"error": "Se requiere username y password."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = authenticate(username=username, password=password)
    if user is None:
        return Response(
            {"error": "Credenciales inválidas."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if not user.is_active:
        return Response(
            {"error": "Cuenta desactivada."},
            status=status.HTTP_403_FORBIDDEN,
        )

    refresh = RefreshToken.for_user(user)
    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": {
            "id": user.id,
            "username": user.username,
        },
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def external_token_google(request):
    """Login con Google id_token (para usuarios creados con Gmail).

    Body: {"credential": "<google_id_token>"}
    """
    from users.google_auth import _verify_google_token
    from users.models import SocialAccount

    credential = (request.data.get("credential") or "").strip()
    if not credential:
        return Response(
            {"error": "Se requiere el campo 'credential' con el id_token de Google."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    payload = _verify_google_token(credential)
    if not payload:
        return Response(
            {"error": "Token de Google inválido."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    if "_error" in payload:
        return Response(
            {"error": payload["_error"]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not payload.get("email_verified"):
        return Response(
            {"error": "El correo de Google no está verificado."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    google_id = payload["sub"]
    email = payload.get("email", "").lower().strip()

    # Buscar usuario vinculado a esta cuenta Google
    from django.contrib.auth import get_user_model
    User = get_user_model()

    social = SocialAccount.objects.filter(provider="google", provider_uid=google_id).first()
    if social:
        user = social.user
    else:
        # Intentar por email
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return Response(
                {"error": "No existe una cuenta asociada a este correo de Google."},
                status=status.HTTP_404_NOT_FOUND,
            )

    if not user.is_active:
        return Response(
            {"error": "Cuenta desactivada."},
            status=status.HTTP_403_FORBIDDEN,
        )

    refresh = RefreshToken.for_user(user)
    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": {
            "id": user.id,
            "username": user.username,
        },
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def external_set_password(request):
    """Permite a un usuario (especialmente los creados con Google) definir una
    contraseña para usar el endpoint /api/external/token/ con username+password.

    Body: {"password": "mi_nueva_contraseña"}
    Requiere estar autenticado (header Authorization: Bearer <token>).
    """
    password = request.data.get("password", "")
    if len(password) < 8:
        return Response(
            {"error": "La contraseña debe tener al menos 8 caracteres."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    request.user.set_password(password)
    request.user.save(update_fields=["password"])
    return Response({
        "detail": "Contraseña configurada correctamente. Ya puedes usar /api/external/token/ con tu username y esta contraseña.",
        "username": request.user.username,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def external_my_decks(request):
    """Devuelve todos los mazos del usuario autenticado con sus cartas."""
    qs = Deck.objects.filter(owner=request.user).prefetch_related(
        "entries__card__edition",
        "entries__card__rarity",
        "entries__card__race",
        "entries__card__card_type",
    )

    # Filtro opcional por formato
    fmt = request.query_params.get("format")
    if fmt:
        qs = qs.filter(format=fmt)

    decks_data = []
    for deck in qs:
        entries = []
        sideboard = []
        for entry in deck.entries.all():
            card = entry.card
            card_data = {
                "card_id": card.id,
                "myl_id": card.myl_id,
                "name": card.name,
                "quantity": entry.quantity,
                "cost": card.cost,
                "damage": card.damage,
                "ability": card.ability,
                "edition_slug": card.edition.slug,
                "edition_title": card.edition.title,
                "rarity": card.rarity.name if card.rarity else None,
                "race": card.race.name if card.race else None,
                "type": card.card_type.name if card.card_type else None,
                "image_url": card.custom_image_url or f"{MYL_CARDS_CDN}{card.edition.myl_id}/{card.edid}.png",
            }
            if entry.is_sideboard:
                sideboard.append(card_data)
            else:
                entries.append(card_data)

        decks_data.append({
            "id": deck.id,
            "name": deck.name,
            "description": deck.description,
            "format": deck.format,
            "sub_format": deck.sub_format,
            "race": deck.race,
            "is_public": deck.is_public,
            "card_count": sum(e["quantity"] for e in entries),
            "sideboard_count": sum(e["quantity"] for e in sideboard),
            "created_at": deck.created_at,
            "updated_at": deck.updated_at,
            "entries": entries,
            "sideboard": sideboard,
        })

    return Response({
        "user": request.user.username,
        "deck_count": len(decks_data),
        "decks": decks_data,
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def external_cards_by_format(request, format_code):
    """Devuelve TODAS las cartas de un formato. No requiere autenticación.

    Formatos comunes: imp, pb, fx, esc (Escuelas Elementales)
    """
    if format_code in HIDDEN_CARD_FORMAT_CODES:
        qs = Card.objects.none()
    elif format_code == "esc":
        qs = Card.objects.filter(edition__slug__in=ESC_EDITION_SLUGS)
    else:
        qs = Card.objects.filter(edition__format__code=format_code)

    qs = qs.select_related("edition", "rarity", "race", "card_type").order_by(
        "edition__slug", "edid"
    )

    cards_data = []
    for card in qs:
        cards_data.append({
            "id": card.id,
            "myl_id": card.myl_id,
            "edid": card.edid,
            "name": card.name,
            "cost": card.cost,
            "damage": card.damage,
            "ability": card.ability,
            "edition_slug": card.edition.slug,
            "edition_title": card.edition.title,
            "rarity": card.rarity.name if card.rarity else None,
            "race": card.race.name if card.race else None,
            "type": card.card_type.name if card.card_type else None,
            "image_url": card.custom_image_url or f"{MYL_CARDS_CDN}{card.edition.myl_id}/{card.edid}.png",
        })

    return Response({
        "format": format_code,
        "total": len(cards_data),
        "cards": cards_data,
    })
