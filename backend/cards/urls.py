from django.urls import path
from . import views

urlpatterns = [
    path("", views.CardListView.as_view(), name="card-list"),
    path("<int:pk>/", views.CardDetailView.as_view(), name="card-detail"),
    path("by-format/<str:format_code>/", views.CardsByFormatView.as_view(), name="cards-by-format"),
    path("editions/", views.EditionListView.as_view(), name="edition-list"),
    path("formats/", views.FormatListView.as_view(), name="format-list"),
    path("races/", views.RaceListView.as_view(), name="race-list"),
    path("types/", views.CardTypeListView.as_view(), name="type-list"),
    path("rarities/", views.RarityListView.as_view(), name="rarity-list"),
    path("banlist/", views.BanlistView.as_view(), name="banlist"),
]
