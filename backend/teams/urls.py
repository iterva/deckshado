from django.urls import path
from . import views

urlpatterns = [
    path("", views.TeamListView.as_view(), name="team-list"),
    path("create/", views.TeamCreateView.as_view(), name="team-create"),
    path("my/", views.my_team, name="my-team"),
    path("leave/", views.leave_team, name="leave-team"),
    path("<int:pk>/", views.TeamDetailView.as_view(), name="team-detail"),
    path("<int:team_id>/join/", views.join_request, name="join-request"),
    path("<int:team_id>/requests/", views.list_requests, name="list-requests"),
    path("requests/<int:request_id>/handle/", views.handle_request, name="handle-request"),
    path("members/<int:member_id>/promote/", views.promote_member, name="promote-member"),
    path("members/<int:member_id>/kick/", views.kick_member, name="kick-member"),
    path("logo/", views.upload_logo, name="upload-logo"),
]
