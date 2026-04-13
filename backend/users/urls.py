from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", TokenObtainPairView.as_view(), name="token-obtain"),
    path("refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", views.me_view, name="me"),
    path("profile/", views.update_profile, name="update-profile"),
    path("avatar/", views.upload_avatar, name="upload-avatar"),
    path("change-password/", views.change_password, name="change-password"),
]
