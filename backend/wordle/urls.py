from django.urls import path

from . import views

urlpatterns = [
    path("today/", views.today_view, name="wordle-today"),
    path("guess/", views.guess_view, name="wordle-guess"),
    path("hint/", views.hint_view, name="wordle-hint"),
    path("leaderboard/", views.leaderboard_view, name="wordle-leaderboard"),
    path("winner/", views.previous_winner_view, name="wordle-winner"),
]
