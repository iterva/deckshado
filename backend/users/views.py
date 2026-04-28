from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from .serializers import (
    RegisterSerializer,
    UserSerializer,
    ProfileUpdateSerializer,
    ChangePasswordSerializer,
)


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
