from django.contrib.auth.models import User
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from .serializers import (
    RegisterSerializer,
    UserSerializer,
    ProfileUpdateSerializer,
    ChangePasswordSerializer,
    AdminUserSerializer,
    _is_admin_user,
)


class IsAdminUserCustom(permissions.BasePermission):
    """Permite acceso solo al usuario 'iterva' o usuarios staff/superuser."""
    message = "No tienes permisos de administrador."

    def has_permission(self, request, view):
        return _is_admin_user(request.user)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def me_view(request):
    return Response(UserSerializer(request.user, context={"request": request}).data)


@api_view(["PATCH"])
@permission_classes([permissions.IsAuthenticated])
def update_profile(request):
    serializer = ProfileUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.update(request.user, serializer.validated_data)
    return Response(UserSerializer(request.user, context={"request": request}).data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def upload_avatar(request):
    avatar_url = request.data.get("avatar_url", "").strip()
    if not avatar_url:
        return Response({"detail": "No se envió ninguna URL."}, status=status.HTTP_400_BAD_REQUEST)
    profile = request.user.profile
    profile.avatar = avatar_url
    profile.save()
    return Response(UserSerializer(request.user, context={"request": request}).data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def change_password(request):
    serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    request.user.set_password(serializer.validated_data["new_password"])
    request.user.save()
    return Response({"detail": "Contraseña actualizada correctamente."})


# ── Notifications ────────────────────────────────────────

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def notifications_view(request):
    from .models import Notification
    notifs = Notification.objects.filter(user=request.user)[:30]
    data = [
        {
            "id": n.id,
            "type": n.notif_type,
            "message": n.message,
            "link": n.link,
            "is_read": n.is_read,
            "created_at": n.created_at,
        }
        for n in notifs
    ]
    unread = Notification.objects.filter(user=request.user, is_read=False).count()
    return Response({"notifications": data, "unread_count": unread})


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def mark_read(request, notif_id):
    from .models import Notification
    Notification.objects.filter(id=notif_id, user=request.user).update(is_read=True)
    return Response({"detail": "ok"})


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def mark_all_read(request):
    from .models import Notification
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return Response({"detail": "ok"})


# ── Admin: gestión de usuarios ───────────────────────────

@api_view(["GET"])
@permission_classes([IsAdminUserCustom])
def admin_list_users(request):
    """Lista todos los usuarios registrados (solo admin)."""
    qs = User.objects.select_related("profile").order_by("-date_joined")
    search = request.query_params.get("q", "").strip()
    if search:
        qs = qs.filter(username__icontains=search) | qs.filter(email__icontains=search)
    data = AdminUserSerializer(qs, many=True, context={"request": request}).data
    return Response(data)


@api_view(["GET", "PATCH"])
@permission_classes([IsAdminUserCustom])
def admin_user_detail(request, user_id):
    """Detalle / actualización de un usuario (solo admin)."""
    try:
        target = User.objects.select_related("profile").get(pk=user_id)
    except User.DoesNotExist:
        return Response({"detail": "Usuario no encontrado."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response(AdminUserSerializer(target, context={"request": request}).data)

    # PATCH: evitar que un admin se desactive a sí mismo o modifique a 'iterva'
    # si no es el propio 'iterva'.
    if target.username == "iterva" and request.user.username != "iterva":
        return Response(
            {"detail": "No puedes modificar al usuario administrador principal."},
            status=status.HTTP_403_FORBIDDEN,
        )
    if target.id == request.user.id and "is_active" in request.data:
        # No permitir auto-banearse
        if not request.data.get("is_active"):
            return Response(
                {"detail": "No puedes desactivar tu propia cuenta."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    serializer = AdminUserSerializer(
        target, data=request.data, partial=True, context={"request": request}
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAdminUserCustom])
def admin_reset_password(request, user_id):
    """Permite al admin establecer una nueva contraseña para un usuario."""
    try:
        target = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({"detail": "Usuario no encontrado."}, status=status.HTTP_404_NOT_FOUND)
    new_password = request.data.get("new_password", "")
    if len(new_password) < 8:
        return Response(
            {"detail": "La contraseña debe tener al menos 8 caracteres."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if target.username == "iterva" and request.user.username != "iterva":
        return Response(
            {"detail": "No puedes cambiar la contraseña del administrador principal."},
            status=status.HTTP_403_FORBIDDEN,
        )
    target.set_password(new_password)
    target.save()
    return Response({"detail": "Contraseña actualizada."})
