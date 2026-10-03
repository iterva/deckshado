"""
Crea la temporada Imperio "Drácula: Rey Vampiro" como temporada activa y le asigna
las ediciones de Drácula (drac, inmdrac). Las demás temporadas quedan inactivas.

La rotación del constructor (ediciones ocultas en esta temporada) vive en el
frontend: deck-builder.component.ts -> seasons.

Uso:
  python manage.py seed_season_dracula
"""

from django.core.management.base import BaseCommand

from cards.models import Edition, Season


SEASON_CODE = "drac"
SEASON_NAME = "Temporada Drácula: Rey Vampiro"
START_DATE = "2026-10-05"
EDITION_SLUGS = ["drac", "inmdrac"]


class Command(BaseCommand):
    help = "Crea la temporada Drácula: Rey Vampiro y le asigna sus ediciones"

    def handle(self, *args, **options):
        season, created = Season.objects.update_or_create(
            code=SEASON_CODE,
            defaults={"name": SEASON_NAME, "start_date": START_DATE, "is_active": True},
        )
        self.stdout.write(self.style.SUCCESS(
            f"{'Created' if created else 'Updated'} season: {season}"
        ))

        closed = Season.objects.exclude(pk=season.pk).filter(is_active=True)
        for old in closed:
            self.stdout.write(f"  Inactive: {old}")
        closed.update(is_active=False)

        linked = Edition.objects.filter(slug__in=EDITION_SLUGS).update(season=season)
        self.stdout.write(self.style.SUCCESS(f"Ediciones asignadas: {linked}/{len(EDITION_SLUGS)}"))
        if linked < len(EDITION_SLUGS):
            self.stdout.write(self.style.WARNING(
                "Faltan ediciones: corre primero seed_dracula_rey_vampiro."
            ))
