import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _bool(name, default=False):
    v = os.getenv(name)
    return default if v is None else v.strip().lower() in ("1", "true", "yes", "on")


def _database_url():
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        (BASE_DIR / "instance").mkdir(exist_ok=True)
        return "sqlite:///" + str(BASE_DIR / "instance" / "maagi.db")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-insecure-key-change-me")
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    MAX_CONTENT_LENGTH = 6 * 1024 * 1024
    UPLOAD_FOLDER = str(BASE_DIR / "app" / "static" / "uploads")
    ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_DURATION = timedelta(days=14)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    WTF_CSRF_TIME_LIMIT = 60 * 60 * 8

    SITE_URL = os.getenv("SITE_URL", "http://127.0.0.1:5000").rstrip("/")

    RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
    RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
    ALLOW_PAYMENT_SIMULATION = _bool("ALLOW_PAYMENT_SIMULATION", True)
    PAYMENT_TIMEOUT_MINUTES = 30

    MAIL_SERVER = os.getenv("MAIL_SERVER", "")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587") or 587)
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_USE_TLS = _bool("MAIL_USE_TLS", True)
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "") or os.getenv("MAIL_USERNAME", "")

    COMPANY_NAME = os.getenv("COMPANY_NAME", "Maagi Pickle")
    COMPANY_EMAIL = os.getenv("COMPANY_EMAIL", "hello@maagi.local")
    COMPANY_PHONE = os.getenv("COMPANY_PHONE", "+91 00000 00000")
    COMPANY_ADDRESS = os.getenv("COMPANY_ADDRESS", "Update COMPANY_ADDRESS in .env, Karnataka, India")
    COMPANY_GSTIN = os.getenv("COMPANY_GSTIN", "")

    SHIPPING_FLAT = 60
    FREE_SHIPPING_THRESHOLD = 999
    B2B_SHIPPING = 0
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_MINUTES = 15
    PER_PAGE = 12
    ADMIN_PER_PAGE = 15
    DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "Maagi@12345")


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    WTF_CSRF_ENABLED = False
    ALLOW_PAYMENT_SIMULATION = True
    RAZORPAY_KEY_ID = ""
    RAZORPAY_KEY_SECRET = ""
    SECRET_KEY = "test-secret"
    SERVER_NAME = None


class ProductionConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = "https"
    ALLOW_PAYMENT_SIMULATION = False

    @classmethod
    def validate(cls):
        if cls.SECRET_KEY.startswith("dev-only") or len(cls.SECRET_KEY) < 32:
            raise RuntimeError("Set a strong SECRET_KEY (32+ chars) in the environment for production.")


CONFIGS = {"development": DevelopmentConfig, "testing": TestingConfig, "production": ProductionConfig}
