from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Team, TeamMember, JoinRequest

User = get_user_model()


class TeamMemberSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = TeamMember
        fields = ["id", "username", "role", "role_display", "joined_at"]


class TeamListSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(read_only=True)
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ["id", "name", "description", "member_count", "logo_url", "created_at"]

    def get_logo_url(self, obj):
        if obj.logo:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.logo.url)
            return obj.logo.url
        return None


class TeamDetailSerializer(serializers.ModelSerializer):
    members = TeamMemberSerializer(many=True, read_only=True)
    member_count = serializers.IntegerField(read_only=True)
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ["id", "name", "description", "members", "member_count", "logo_url", "created_at"]

    def get_logo_url(self, obj):
        if obj.logo:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.logo.url)
            return obj.logo.url
        return None


class TeamCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ["name", "description"]


class JoinRequestSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = JoinRequest
        fields = ["id", "username", "status", "status_display", "created_at"]
