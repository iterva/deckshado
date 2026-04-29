from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views
from . import google_auth

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", TokenObtainPairView.as_view(), name="token-obtain"),
    path("refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    # Google OAuth
    path("google/", google_auth.google_login, name="google-login"),
    path("google/link/", google_auth.google_link, name="google-link"),
    path("google/unlink/", google_auth.google_unlink, name="google-unlink"),
    path("social/", google_auth.social_status, name="social-status"),
    path("me/", views.me_view, name="me"),
    path("profile/", views.update_profile, name="update-profile"),
    path("avatar/", views.upload_avatar, name="upload-avatar"),
    path("change-password/", views.change_password, name="change-password"),
    path("notifications/", views.notifications_view, name="notifications"),
    path("notifications/read-all/", views.mark_all_read, name="notifications-read-all"),
    path("notifications/<int:notif_id>/read/", views.mark_read, name="notification-read"),
    # Admin
    path("admin/users/", views.admin_list_users, name="admin-list-users"),
    path("admin/users/<int:user_id>/", views.admin_user_detail, name="admin-user-detail"),
    path("admin/users/<int:user_id>/reset-password/", views.admin_reset_password, name="admin-user-reset-password"),
]
