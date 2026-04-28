from django.urls import path
from . import views

urlpatterns = [
    path("public/", views.PublicDeckListView.as_view(), name="public-deck-list"),
    path("public/<int:pk>/", views.PublicDeckDetailView.as_view(), name="public-deck-detail"),
    path("team/", views.TeamDeckListView.as_view(), name="team-deck-list"),
    path("team/<int:pk>/", views.TeamDeckDetailView.as_view(), name="team-deck-detail"),
    path("my/", views.MyDeckListView.as_view(), name="my-deck-list"),
    path("my/<int:pk>/", views.DeckDetailView.as_view(), name="deck-detail"),
    path("my/<int:deck_id>/entries/", views.deck_entry_view, name="deck-entries"),
    path("my/<int:deck_id>/changelog/", views.deck_changelog_view, name="deck-changelog"),
]
