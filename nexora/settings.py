import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
FROZEN = bool(getattr(sys, "frozen", False))
APP_ROOT = Path(getattr(sys, "_MEIPASS", BASE_DIR)) if FROZEN else BASE_DIR
DESKTOP_APP = os.getenv("NEXORA_DESKTOP_APP", "0").lower() in ("1", "true", "yes")
if FROZEN or DESKTOP_APP:
    DATA_DIR = Path(os.getenv("NEXORA_DATA_DIR", Path.home() / "AppData" / "Local" / "Nexora")).resolve()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
else:
    DATA_DIR = BASE_DIR
load_dotenv(DATA_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-change-me-before-deploying").strip()
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() in ("1", "true", "yes")
ALLOWED_HOSTS = [host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if host.strip()]
NEXORA_ENCRYPTION_KEY = os.getenv("NEXORA_ENCRYPTION_KEY", "").strip()
NEXORA_SITE_URL = os.getenv("NEXORA_SITE_URL", "http://localhost:8000").strip().rstrip("/")
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if origin.strip()]

if not DEBUG and not DESKTOP_APP:
    if not SECRET_KEY or SECRET_KEY == "dev-only-change-me-before-deploying" or SECRET_KEY.startswith("replace-"):
        raise ImproperlyConfigured("برای production مقدار تصادفی DJANGO_SECRET_KEY را در .env تنظیم کن.")
    if not NEXORA_ENCRYPTION_KEY or NEXORA_ENCRYPTION_KEY == "replace-with-generated-fernet-key":
        raise ImproperlyConfigured("برای production مقدار مستقل NEXORA_ENCRYPTION_KEY را در .env تنظیم کن.")
    if not ALLOWED_HOSTS or ALLOWED_HOSTS == ["127.0.0.1", "localhost"]:
        raise ImproperlyConfigured("برای production دامنه‌های واقعی را در DJANGO_ALLOWED_HOSTS وارد کن.")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "nexora.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [APP_ROOT / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
        "core.context_processors.nexora_context",
    ]},
}]
WSGI_APPLICATION = "nexora.wsgi.application"
ASGI_APPLICATION = "nexora.asgi.application"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": DATA_DIR / "db.sqlite3"}}
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "fa"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATICFILES_DIRS = [APP_ROOT / "static"]
STATIC_ROOT = APP_ROOT / "staticfiles"
STORAGES = {"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"}, "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_SECURE = not DEBUG and not DESKTOP_APP
CSRF_COOKIE_SECURE = not DEBUG and not DESKTOP_APP
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_SSL_REDIRECT = False if DESKTOP_APP else os.getenv("DJANGO_SECURE_SSL_REDIRECT", "False" if DEBUG else "True").lower() in ("1", "true", "yes")
