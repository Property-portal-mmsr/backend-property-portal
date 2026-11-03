from dotenv import load_dotenv
import os

load_dotenv()
if os.getenv("ENVIRONMENT") == "production":
    load_dotenv(".env.production", override=True)
elif os.path.exists(".env.local"):
    load_dotenv(".env.local", override=True)

def get_env(name: str, default: str = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(
            f"❌ Missing required environment variable: {name}\n"
            "Please configure your .env file from .env.example"
        )
    return value

ENVIRONMENT = get_env("ENVIRONMENT", "development")

DB_HOST = get_env("DB_HOST")
DB_PORT = get_env("DB_PORT")
DB_NAME = get_env("DB_NAME")
DB_USER = get_env("DB_USER")
DB_PASSWORD = get_env("DB_PASSWORD")

SECRET_KEY = get_env("SECRET_KEY", "makemystay_super_secret_jwt_key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440)
)
REFRESH_TOKEN_EXPIRE_DAYS = int(
    os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7)
)

GOOGLE_SHEET_URL = os.getenv(
    "GOOGLE_SHEET_URL",
    ""
)

# Shared photo storage. Old listings already live on this CloudFront distribution.
# New uploads must go here too — local disk is per-server and is wiped by deploys.
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "").strip()
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "").strip()
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1").strip() or "ap-south-1"
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "makemystayrealty").strip()
CLOUDFRONT_DOMAIN = os.getenv("CLOUDFRONT_DOMAIN", "d1yfdszs9lcm9e.cloudfront.net").strip()
PUBLIC_UPLOADS_BASE_URL = os.getenv("PUBLIC_UPLOADS_BASE_URL", "").strip().rstrip("/")
UPLOADS_FALLBACK_ORIGIN = os.getenv("UPLOADS_FALLBACK_ORIGIN", "").strip().rstrip("/")
UPLOADS_DIR = os.path.abspath(os.getenv("UPLOADS_DIR", "uploads"))

