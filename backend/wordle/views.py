from datetime import date as _date

from django.contrib.auth import get_user_model
from django.db.models import IntegerField, Sum
from django.db.models.functions import Cast
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .game import (
    MAX_ATTEMPTS,
    calc_score,
    evaluate_guess,
    get_or_create_today,
    normalize,
)
from .models import DailyWord, WordleAttempt


User = get_user_model()


def _serialize_attempt(daily: DailyWord, attempt: WordleAttempt | None, reveal_word: bool):
    guesses = attempt.guesses if attempt else []
    won = bool(attempt and attempt.won)
    finished = bool(attempt and attempt.finished)
    return {
        "date": daily.date.isoformat(),
        "length": daily.length,
        "max_attempts": MAX_ATTEMPTS,
        "hint": daily.hint if (attempt and attempt.hint_revealed) else None,
        "hint_available": True,
        "guesses": guesses,
        "attempts_used": attempt.attempts_used if attempt else 0,
        "won": won,
        "finished": finished,
        "hint_revealed": bool(attempt and attempt.hint_revealed),
        "score": attempt.score if attempt else 0,
        "answer": daily.display_word if (finished or reveal_word) else None,
        "card_image": (
            getattr(daily.card, "custom_image_url", None) if finished else None
        ),
        "card_id": daily.card_id if finished else None,
    }


@api_view(["GET"])
@permission_classes([AllowAny])
def today_view(request):
    daily = get_or_create_today()
    attempt = None
    if request.user.is_authenticated:
        attempt = WordleAttempt.objects.filter(user=request.user, daily=daily).first()
    return Response(_serialize_attempt(daily, attempt, reveal_word=False))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def guess_view(request):
    raw = (request.data or {}).get("guess", "")
    if not isinstance(raw, str):
        return Response({"detail": "guess inválido"}, status=400)
    guess_norm = normalize(raw)
    daily = get_or_create_today()

    attempt, _ = WordleAttempt.objects.get_or_create(user=request.user, daily=daily)
    if attempt.finished:
        return Response({"detail": "Ya completaste la palabra de hoy."}, status=400)
    if attempt.attempts_used >= MAX_ATTEMPTS:
        attempt.finished = True
        attempt.save(update_fields=["finished"])
        return Response({"detail": "Sin intentos restantes."}, status=400)
    if len(guess_norm) != daily.length:
        return Response(
            {"detail": f"La palabra debe tener {daily.length} letras."},
            status=400,
        )

    statuses = evaluate_guess(guess_norm, daily.word)
    won = guess_norm == daily.word
    attempt.attempts_used += 1
    attempt.guesses = (attempt.guesses or []) + [
        {"letters": list(guess_norm), "statuses": statuses}
    ]
    if won:
        attempt.won = True
        attempt.finished = True
        attempt.completed_at = timezone.now()
        attempt.score = calc_score(attempt.attempts_used, True, attempt.hint_revealed)
    elif attempt.attempts_used >= MAX_ATTEMPTS:
        attempt.finished = True
        attempt.completed_at = timezone.now()
        attempt.score = 0
    attempt.save()

    return Response(_serialize_attempt(daily, attempt, reveal_word=False))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def hint_view(request):
    daily = get_or_create_today()
    attempt, _ = WordleAttempt.objects.get_or_create(user=request.user, daily=daily)
    if not attempt.hint_revealed:
        attempt.hint_revealed = True
        attempt.save(update_fields=["hint_revealed"])
    return Response({"hint": daily.hint, "hint_revealed": True})


@api_view(["GET"])
@permission_classes([AllowAny])
def leaderboard_view(request):
    today = timezone.localdate()
    try:
        year = int(request.query_params.get("year", today.year))
        month = int(request.query_params.get("month", today.month))
    except ValueError:
        return Response({"detail": "year/month inválidos"}, status=400)

    qs = (
        WordleAttempt.objects.filter(
            daily__date__year=year,
            daily__date__month=month,
        )
        .values("user_id", "user__username")
        .annotate(
            total_score=Sum("score"),
            wins=Sum(Cast("won", IntegerField())),
            played=Sum(Cast("finished", IntegerField())),
        )
        .order_by("-total_score", "-wins")
    )
    rows = [
        {
            "user_id": r["user_id"],
            "username": r["user__username"],
            "score": r["total_score"] or 0,
            "wins": int(r["wins"] or 0),
            "played": int(r["played"] or 0),
        }
        for r in qs
    ]
    return Response({"year": year, "month": month, "leaderboard": rows})


@api_view(["GET"])
@permission_classes([AllowAny])
def previous_winner_view(request):
    """Devuelve el ganador del MES ANTERIOR al actual."""
    today = timezone.localdate()
    if today.month == 1:
        year, month = today.year - 1, 12
    else:
        year, month = today.year, today.month - 1
    top = (
        WordleAttempt.objects.filter(
            daily__date__year=year, daily__date__month=month
        )
        .values("user_id", "user__username")
        .annotate(total_score=Sum("score"))
        .order_by("-total_score")
        .first()
    )
    if not top or not top["total_score"]:
        return Response({"year": year, "month": month, "winner": None})
    return Response(
        {
            "year": year,
            "month": month,
            "winner": {
                "user_id": top["user_id"],
                "username": top["user__username"],
                "score": top["total_score"],
            },
        }
    )
