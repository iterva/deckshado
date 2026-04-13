from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("users.urls")),
    path("api/cards/", include("cards.urls")),
    path("api/decks/", include("decks.urls")),
    path("api/teams/", include("teams.urls")),
    path("api/carpeta/", include("carpeta.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # PythonAnywhere serves media via static files mapping
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
