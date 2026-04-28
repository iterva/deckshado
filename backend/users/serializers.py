from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import Profile


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["first_name", "last_name", "league_code", "avatar"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Ya existe un usuario con este correo.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
        )
        return user


def _is_admin_user(user):
    """Devuelve True si el usuario tiene privilegios de administración."""
    if not user or not user.is_authenticated:
        return False
    return user.username == "iterva" or user.is_superuser or user.is_staff


class UserSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="profile.first_name", read_only=True)
    last_name = serializers.CharField(source="profile.last_name", read_only=True)
    league_code = serializers.CharField(source="profile.league_code", read_only=True)
    avatar_url = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "league_code", "avatar_url", "is_admin",
        ]

    def get_avatar_url(self, obj):
        if hasattr(obj, "profile") and obj.profile.avatar:
            return obj.profile.avatar
        return None

    def get_is_admin(self, obj):
        return _is_admin_user(obj)


class AdminUserSerializer(serializers.ModelSerializer):
    """Serializer extendido para la vista de administración."""
    first_name = serializers.CharField(source="profile.first_name", required=False, allow_blank=True)
    last_name = serializers.CharField(source="profile.last_name", required=False, allow_blank=True)
    league_code = serializers.CharField(source="profile.league_code", required=False, allow_blank=True)
    avatar_url = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "league_code", "avatar_url", "is_active", "is_staff",
            "is_admin", "date_joined", "last_login",
        ]
        read_only_fields = ["id", "date_joined", "last_login", "avatar_url", "is_admin"]

    def get_avatar_url(self, obj):
        if hasattr(obj, "profile") and obj.profile.avatar:
            return obj.profile.avatar
        return None

    def get_is_admin(self, obj):
        return _is_admin_user(obj)

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", {})
        for field in ("username", "email", "is_active", "is_staff"):
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        instance.save()
        if profile_data:
            profile = instance.profile
            for k, v in profile_data.items():
                setattr(profile, k, v)
            profile.save()
        return instance


class ProfileUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=50, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=50, required=False, allow_blank=True)
    league_code = serializers.CharField(max_length=30, required=False, allow_blank=True)
    avatar = serializers.URLField(max_length=500, required=False, allow_blank=True)

    def update(self, instance, validated_data):
        profile = instance.profile
        for field in ("first_name", "last_name", "league_code", "avatar"):
            if field in validated_data:
                setattr(profile, field, validated_data[field])
        profile.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Contraseña actual incorrecta.")
        return value

    def validate_new_password(self, value):
        validate_password(value, self.context["request"].user)
        return value
