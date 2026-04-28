from django.urls import path
from . import views

urlpatterns = [
    path("public/", views.PublicDeckListView.as_view(), name="public-deck-list"),
    path("public/<int:pk>/", views.PublicDeckDetailView.as_view(), name="public-deck-detail"),
    path("public/<int:deck_id>/like/", views.toggle_like, name="deck-like"),
    path("public/<int:deck_id>/comments/", views.deck_comments_view, name="deck-comments"),
    path("comments/<int:comment_id>/", views.delete_comment, name="delete-comment"),
    path("team/", views.TeamDeckListView.as_view(), name="team-deck-list"),
    path("team/<int:pk>/", views.TeamDeckDetailView.as_view(), name="team-deck-detail"),
    path("my/", views.MyDeckListView.as_view(), name="my-deck-list"),
    path("my/<int:pk>/", views.DeckDetailView.as_view(), name="deck-detail"),
    path("my/<int:deck_id>/entries/", views.deck_entry_view, name="deck-entries"),
    path("my/<int:deck_id>/changelog/", views.deck_changelog_view, name="deck-changelog"),
    path("my/<int:deck_id>/snapshots/", views.deck_snapshots_view, name="deck-snapshots"),
    path("my/<int:deck_id>/suggestions/", views.card_suggestions, name="deck-suggestions"),
    path("snapshots/<int:snapshot_id>/restore/", views.restore_snapshot, name="restore-snapshot"),
]
