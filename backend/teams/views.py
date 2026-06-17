from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.response import Response
from django.db.models import Count
from backend.cdn_image_upload import upload_image_to_cdn, CdnImageUploadError
from .models import Team, TeamMember, JoinRequest
from .serializers import (
    TeamListSerializer, TeamDetailSerializer, TeamCreateSerializer,
    JoinRequestSerializer,
)
from users.models import Notification


class TeamListView(generics.ListAPIView):
    serializer_class = TeamListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Team.objects.annotate(member_count=Count("members")).order_by("-created_at")


class TeamCreateView(generics.CreateAPIView):
    serializer_class = TeamCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        team = serializer.save()
        TeamMember.objects.create(team=team, user=self.request.user, role="captain")


class TeamDetailView(generics.RetrieveAPIView):
    serializer_class = TeamDetailSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Team.objects.annotate(member_count=Count("members")).prefetch_related("members__user")


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def my_team(request):
    try:
        membership = TeamMember.objects.select_related("team").get(user=request.user)
        team = membership.team
        team_data = TeamDetailSerializer(team, context={"request": request}).data
        team_data["member_count"] = team.members.count()
        team_data["members"] = [
            {
                "id": m.id,
                "username": m.user.username,
                "role": m.role,
                "role_display": m.get_role_display(),
                "joined_at": m.joined_at,
            }
            for m in team.members.select_related("user").all()
        ]
        team_data["my_role"] = membership.role
        return Response(team_data)
    except TeamMember.DoesNotExist:
        return Response({"detail": "No tienes equipo"}, status=status.HTTP_404_NOT_FOUND)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def join_request(request, team_id):
    if TeamMember.objects.filter(user=request.user).exists():
        return Response({"error": "Ya perteneces a un equipo"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        team = Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        return Response({"error": "Equipo no encontrado"}, status=status.HTTP_404_NOT_FOUND)
    if JoinRequest.objects.filter(team=team, user=request.user, status="pending").exists():
        return Response({"error": "Ya tienes una solicitud pendiente"}, status=status.HTTP_400_BAD_REQUEST)
    jr = JoinRequest.objects.create(team=team, user=request.user)
    # Notify captains
    for cap in TeamMember.objects.filter(team=team, role="captain").select_related("user"):
        Notification.objects.create(
            user=cap.user,
            notif_type="team_join",
            message=f"{request.user.username} quiere unirse a {team.name}",
            link="/team",
        )
    return Response(JoinRequestSerializer(jr).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def list_requests(request, team_id):
    try:
        membership = TeamMember.objects.get(user=request.user, team_id=team_id, role="captain")
    except TeamMember.DoesNotExist:
        return Response({"error": "No eres capitán de este equipo"}, status=status.HTTP_403_FORBIDDEN)
    requests = JoinRequest.objects.filter(team_id=team_id, status="pending").select_related("user").order_by("-created_at")
    return Response(JoinRequestSerializer(requests, many=True).data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def handle_request(request, request_id):
    action = request.data.get("action")
    if action not in ("accept", "reject"):
        return Response({"error": "Acción inválida"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        jr = JoinRequest.objects.select_related("team").get(id=request_id, status="pending")
    except JoinRequest.DoesNotExist:
        return Response({"error": "Solicitud no encontrada"}, status=status.HTTP_404_NOT_FOUND)
    if not TeamMember.objects.filter(user=request.user, team=jr.team, role="captain").exists():
        return Response({"error": "No eres capitán de este equipo"}, status=status.HTTP_403_FORBIDDEN)

    if action == "accept":
        if TeamMember.objects.filter(user=jr.user).exists():
            jr.status = "rejected"
            jr.save()
            return Response({"error": "El usuario ya pertenece a un equipo"}, status=status.HTTP_400_BAD_REQUEST)
        TeamMember.objects.create(team=jr.team, user=jr.user, role="member")
        jr.status = "accepted"
        jr.save()
        Notification.objects.create(
            user=jr.user,
            notif_type="team_accepted",
            message=f"Tu solicitud a {jr.team.name} fue aceptada 🎉",
            link="/team",
        )
        return Response({"detail": "Solicitud aceptada"})
    else:
        jr.status = "rejected"
        jr.save()
        Notification.objects.create(
            user=jr.user,
            notif_type="team_rejected",
            message=f"Tu solicitud a {jr.team.name} fue rechazada",
            link="/team",
        )
        return Response({"detail": "Solicitud rechazada"})


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def leave_team(request):
    try:
        membership = TeamMember.objects.select_related("team").get(user=request.user)
    except TeamMember.DoesNotExist:
        return Response({"error": "No perteneces a un equipo"}, status=status.HTTP_400_BAD_REQUEST)
    team = membership.team
    # Prevent last captain from leaving if other members remain
    if membership.role == "captain":
        captain_count = team.members.filter(role="captain").count()
        has_other_members = team.members.count() > 1
        if captain_count <= 1 and has_other_members:
            return Response({"error": "No puedes salir: eres el único capitán. Designa otro capitán primero."}, status=status.HTTP_400_BAD_REQUEST)
    membership.delete()
    if not team.members.exists():
        team.delete()
    return Response({"detail": "Has salido del equipo"})


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def promote_member(request, member_id):
    try:
        target = TeamMember.objects.select_related("team").get(id=member_id)
    except TeamMember.DoesNotExist:
        return Response({"error": "Miembro no encontrado"}, status=status.HTTP_404_NOT_FOUND)
    if not TeamMember.objects.filter(user=request.user, team=target.team, role="captain").exists():
        return Response({"error": "No eres capitán"}, status=status.HTTP_403_FORBIDDEN)
    target.role = "captain"
    target.save()
    return Response({"detail": f"{target.user.username} ahora es capitán"})


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def kick_member(request, member_id):
    try:
        target = TeamMember.objects.select_related("team").get(id=member_id)
    except TeamMember.DoesNotExist:
        return Response({"error": "Miembro no encontrado"}, status=status.HTTP_404_NOT_FOUND)
    if not TeamMember.objects.filter(user=request.user, team=target.team, role="captain").exists():
        return Response({"error": "No eres capitán"}, status=status.HTTP_403_FORBIDDEN)
    if target.user == request.user:
        return Response({"error": "No puedes expulsarte a ti mismo"}, status=status.HTTP_400_BAD_REQUEST)
    target.delete()
    return Response({"detail": "Miembro expulsado"})


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def upload_logo(request):
    try:
        membership = TeamMember.objects.select_related("team").get(user=request.user, role="captain")
    except TeamMember.DoesNotExist:
        return Response({"error": "No eres capitán de ningún equipo"}, status=status.HTTP_403_FORBIDDEN)

    logo_url = request.data.get("logo_url", "").strip()
    file_obj = request.FILES.get("file")

    if not logo_url and file_obj is not None:
        try:
            logo_url = upload_image_to_cdn(file_obj, folder="deckshado/team_logos")
        except CdnImageUploadError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    if not logo_url:
        return Response({"error": "No se envió URL o archivo de imagen"}, status=status.HTTP_400_BAD_REQUEST)
    team = membership.team
    team.logo = logo_url
    team.save()
    return Response({"logo_url": team.logo})

