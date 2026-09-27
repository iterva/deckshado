import os
from pathlib import Path
from datetime import timedelta


def _load_env_file(path: Path) -> None:
    if not path.exists() or not path.is_file():
        return
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        lines = path.read_text(encoding="latin-1").splitlines()

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue

        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]

        value = value.strip()
        force_override_keys = {
            "CDN_PROVIDER",
            "IMAGEKIT_PUBLIC_KEY",
            "IMAGEKIT_PRIVATE_KEY",
            "IMAGEKIT_URL_ENDPOINT",
            "public_key",
            "private_key",
            "url",
        }
        if key in force_override_keys:
            os.environ[key] = value
        else:
            os.environ.setdefault(key, value)


def _load_local_env() -> None:
    settings_dir = Path(__file__).resolve().parent
    backend_dir = settings_dir.parent
    repo_dir = backend_dir.parent
    workspace_dir = repo_dir.parent

    candidates = [
        backend_dir / ".env",
        backend_dir / ".env.local",
        repo_dir / ".env",
        repo_dir / ".env.local",
        repo_dir / ".env.imagekit",
        repo_dir / ".env_imagekit",
        repo_dir / ".env_imagekit copy",
        workspace_dir / ".env",
        workspace_dir / ".env.local",
        workspace_dir / ".env.imagekit",
        workspace_dir / ".env_imagekit",
        workspace_dir / ".env_imagekit copy",
    ]
    for env_file in candidates:
        _load_env_file(env_file)

    legacy_private = (
        os.environ.get("private_key")
        or os.environ.get("PRIVATE_KEY")
        or ""
    ).strip()
    if legacy_private:
        os.environ["IMAGEKIT_PRIVATE_KEY"] = legacy_private

    legacy_public = (
        os.environ.get("public_key")
        or os.environ.get("PUBLIC_KEY")
        or ""
    ).strip()
    if legacy_public:
        os.environ["IMAGEKIT_PUBLIC_KEY"] = legacy_public

    legacy_url = (
        os.environ.get("url")
        or os.environ.get("URL")
        or ""
    ).strip()
    if legacy_url:
        os.environ["IMAGEKIT_URL_ENDPOINT"] = legacy_url

    if (os.environ.get("IMAGEKIT_PRIVATE_KEY") or "").strip() and not (os.environ.get("CDN_PROVIDER") or "").strip():
        os.environ["CDN_PROVIDER"] = "imagekit"


_load_local_env()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-change-me-in-production-deckshado-2026",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() in ("true", "1")

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,iterva.pythonanywhere.com,dev-preprod-shadow-forge-deck.vercel.app").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    # Local apps
    "cards",
    "decks",
    "users",
    "teams",
    "carpeta",
    "wordle",
    "riftbound",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "backend.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        # Avoid intermittent "database is locked" 500s under concurrent writes.
        "OPTIONS": {
            "timeout": 20,
            "transaction_mode": "IMMEDIATE",
            "init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;",
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CORS
_cors_extra = os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
_cors_regex_extra = os.environ.get("CORS_ALLOWED_ORIGIN_REGEXES", "").split(",")
CORS_ALLOWED_ORIGINS = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
    "http://localhost:4300",
    "http://127.0.0.1:4300",
    "https://shadow-forge-deck.vercel.app",
    "https://dev-preprod-shadow-forge-deck.vercel.app",
] + [o.strip() for o in _cors_extra if o.strip()]
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*shadow-forge-deck.*\.vercel\.app$",
    r"^https://ik\.imagekit\.io$",
] + [r.strip() for r in _cors_regex_extra if r.strip()]

# REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# JWT
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=7),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=365),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
}

# Google OAuth (Sign-In). El client secret no es necesario para verificar id_token.
GOOGLE_CLIENT_ID = os.environ.get(
    "GOOGLE_CLIENT_ID",
    "739285382559-c10lo6ddtaa7j7fi07halv5jr1e6laju.apps.googleusercontent.com",
)

# CSRF trusted origins (for admin panel access from these domains)
CSRF_TRUSTED_ORIGINS = [
    "https://iterva.pythonanywhere.com",
    "https://frontend-cyan-alpha-34.vercel.app",
    "https://shadow-forge-deck.vercel.app",
    "https://dev-preprod-shadow-forge-deck.vercel.app",
]

# MyL API
MYL_API_BASE_URL = "https://api.myl.cl"

# ── Sentry (opcional, se activa solo si SENTRY_DSN está definido) ──
SENTRY_DSN = os.environ.get("SENTRY_DSN", "").strip()
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[DjangoIntegration()],
            traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
            send_default_pii=False,
            environment=os.environ.get("SENTRY_ENVIRONMENT", "production" if not DEBUG else "development"),
            release=os.environ.get("SENTRY_RELEASE"),
        )
    except ImportError:
        # sentry-sdk no está instalado; se ignora silenciosamente.
        pass

