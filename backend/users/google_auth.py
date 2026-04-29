"""Google OAuth: login + signup + account linking (Opción A).

Verifica el id_token de Google Identity Services y emite un par de tokens
JWT (los mismos que usa el resto de la app vía SimpleJWT).

Flujos cubiertos:
  - Usuario nuevo (sin cuenta) → crea User + Profile + SocialAccount.
  - Usuario con cuenta clásica y mismo email (verificado por Google) →
    vincula automáticamente y devuelve JWT.
  - Usuario con SocialAccount existente → login directo.
  - Vinculación manual: el usuario autenticado vincula Google a su cuenta.
  - Desvinculación: solo si el usuario aún tiene contraseña utilizable.
"""
from __future__ import annotations

import os
import re
import unicodedata

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import SocialAccount

User = get_user_model()


def _get_client_id() -> str:
    return os.environ.get("GOOGLE_CLIENT_ID", getattr(settings, "GOOGLE_CLIENT_ID", "")).strip()


def _verify_google_token(id_token_str: str) -> dict | None:
    """Verifica el id_token contra Google. Devuelve el payload o None."""
    if not id_token_str:
        return None
    try:
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests
    except ImportError:
        # google-auth no instalado: fallar de forma controlada
        return {"_error": "google-auth no instalado en el servidor"}

    client_id = _get_client_id()
    if not client_id:
        return {"_error": "GOOGLE_CLIENT_ID no configurado"}

    try:
        payload = google_id_token.verify_oauth2_token(
            id_token_str, google_requests.Request(), client_id
        )
        return payload
    except Exception as e:  # pragma: no cover - defensivo
        return {"_error": f"Token inválido: {e}"}


def _slugify_username(value: str) -> str:
    """Normaliza un string para usarlo como username."""
    value = unicodedata.normalize("NFD", value or "")
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^A-Za-z0-9_.-]+", "", value)
    return value[:30] or "user"


def _generate_username(email: str, given_name: str = "") -> str:
    """Genera un username único a partir del email o del nombre."""
    base = _slugify_username(given_name) if given_name else _slugify_username(email.split("@")[0])
    if not base:
        base = "user"
    candidate = base
    n = 1
    while User.objects.filter(username=candidate).exists():
        n += 1
        suffix = str(n)
        candidate = f"{base[: 30 - len(suffix)]}{suffix}"
    return candidate


def _tokens_for(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


def _apply_google_profile(user: User, payload: dict) -> None:
    """Rellena profile.first_name, last_name y avatar si están vacíos."""
    profile = getattr(user, "profile", None)
    if not profile:
        return
    given = (payload.get("given_name") or "").strip()
    family = (payload.get("family_name") or "").strip()
    picture = (payload.get("picture") or "").strip()
    changed = False
    if given and not profile.first_name:
        profile.first_name = given[:50]
        changed = True
    if family and not profile.last_name:
        profile.last_name = family[:50]
        changed = True
    if picture and not profile.avatar:
        profile.avatar = picture[:500]
        changed = True
    if changed:
        profile.save()
    # Sincronizar email del User si no tenía
    email = (payload.get("email") or "").strip()
    if email and not user.email:
        user.email = email
        user.save(update_fields=["email"])


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def google_login(request):
    """Login / signup con Google id_token. Body: { credential: '<id_token>' }."""
    credential = (request.data.get("credential") or "").strip()
    payload = _verify_google_token(credential)
    if not payload:
        return Response({"detail": "Token de Google ausente o inválido."}, status=400)
    if "_error" in payload:
        return Response({"detail": payload["_error"]}, status=400)

    if not payload.get("email_verified"):
        return Response(
            {"detail": "Tu correo de Google no está verificado. No se puede iniciar sesión."},
            status=400,
        )

    sub = payload.get("sub")
    email = (payload.get("email") or "").strip().lower()
    if not sub or not email:
        return Response({"detail": "Token de Google incompleto."}, status=400)

    # 1) ¿Ya existe SocialAccount con este sub? → login directo.
    sa = SocialAccount.objects.filter(provider="google", provider_uid=sub).select_related("user").first()
    if sa:
        _apply_google_profile(sa.user, payload)
        tokens = _tokens_for(sa.user)
        return Response({**tokens, "linked": False, "created": False})

    # 2) ¿Existe User con ese email? → Opción A: vincular automático.
    existing = User.objects.filter(email__iexact=email).first()
    if existing:
        SocialAccount.objects.create(
            user=existing, provider="google", provider_uid=sub, email=email
        )
        _apply_google_profile(existing, payload)
        tokens = _tokens_for(existing)
        return Response({**tokens, "linked": True, "created": False})

    # 3) Nuevo: crear User + SocialAccount.
    with transaction.atomic():
        username = _generate_username(email, payload.get("given_name") or "")
        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=(payload.get("given_name") or "")[:30],
            last_name=(payload.get("family_name") or "")[:30],
        )
        # Sin contraseña utilizable hasta que el usuario la setee.
        user.set_unusable_password()
        user.save()
        SocialAccount.objects.create(
            user=user, provider="google", provider_uid=sub, email=email
        )
        _apply_google_profile(user, payload)

    tokens = _tokens_for(user)
    return Response({**tokens, "linked": False, "created": True}, status=201)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def google_link(request):
    """Vincula una cuenta Google al usuario autenticado."""
    credential = (request.data.get("credential") or "").strip()
    payload = _verify_google_token(credential)
    if not payload or "_error" in payload:
        msg = payload.get("_error") if isinstance(payload, dict) else "Token inválido."
        return Response({"detail": msg or "Token inválido."}, status=400)
    if not payload.get("email_verified"):
        return Response({"detail": "Tu correo de Google no está verificado."}, status=400)

    sub = payload.get("sub")
    email = (payload.get("email") or "").strip().lower()
    if not sub:
        return Response({"detail": "Token incompleto."}, status=400)

    # Si esa cuenta Google ya está vinculada a otro usuario → conflicto.
    other = (
        SocialAccount.objects.filter(provider="google", provider_uid=sub)
        .exclude(user=request.user)
        .first()
    )
    if other:
        return Response(
            {"detail": "Esta cuenta de Google ya está vinculada a otro usuario."},
            status=409,
        )

    SocialAccount.objects.update_or_create(
        provider="google", provider_uid=sub,
        defaults={"user": request.user, "email": email},
    )
    _apply_google_profile(request.user, payload)
    return Response({"linked": True, "email": email})


@api_view(["DELETE"])
@permission_classes([permissions.IsAuthenticated])
def google_unlink(request):
    """Desvincula Google del usuario autenticado.

    No permite desvincular si quedaría sin método de acceso (sin contraseña
    utilizable). En ese caso el usuario debe primero establecer una contraseña.
    """
    user = request.user
    if not user.has_usable_password():
        return Response(
            {
                "detail": (
                    "No puedes desvincular Google sin tener una contraseña configurada. "
                    "Establece una contraseña primero desde tu perfil."
                )
            },
            status=400,
        )
    SocialAccount.objects.filter(user=user, provider="google").delete()
    return Response({"unlinked": True})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def social_status(request):
    """Devuelve el estado de cuentas sociales del usuario actual."""
    accounts = list(
        SocialAccount.objects.filter(user=request.user).values(
            "provider", "email", "linked_at"
        )
    )
    return Response({
        "has_usable_password": request.user.has_usable_password(),
        "accounts": accounts,
    })
