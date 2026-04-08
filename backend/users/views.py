from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .serializers import RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def me_view(request):
    return Response(UserSerializer(request.user).data)
