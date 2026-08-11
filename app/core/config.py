from dotenv import load_dotenv
import os

load_dotenv()

def get_env(name: str, default: str = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(
            f"❌ Missing required environment variable: {name}\n"
            "Please configure your .env file from .env.example"
        )
    return value

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

