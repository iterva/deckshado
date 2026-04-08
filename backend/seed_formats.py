import django, os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from cards.models import Format, Edition
from cards.management.commands.sync_cards import EDITIONS_BY_FORMAT

# Crear imp_r
fmt_r, created = Format.objects.get_or_create(code="imp_r", defaults={"name": "Imperio (Rotado)"})
print(f"imp_r: {'creado' if created else 'ya existia'}")

# Reasignar ediciones rotadas
rotated_slugs = list(EDITIONS_BY_FORMAT["imp_r"])
updated = Edition.objects.filter(slug__in=rotated_slugs).update(format=fmt_r, active=False)
print(f"Ediciones movidas a imp_r: {updated}")

# Asegurar que imp quede activo
imp = Format.objects.get(code="imp")
active = Edition.objects.filter(format=imp).update(active=True)
print(f"Ediciones activas en imp: {active}")
print(f"Total ediciones en imp_r: {Edition.objects.filter(format=fmt_r).count()}")
