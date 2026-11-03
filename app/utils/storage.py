"""Durable property photo storage.

Photos used to be written to each API host's local `uploads/` folder as a
relative `/uploads/images/...` path. That breaks for colleagues because:

1. `deploy.sh` used `rsync --delete`, which wiped the folder on every release
2. Two API hosts sit behind the load balancer, so a file on host A 404s on host B
3. The employee portal (`employee.makemystay.ai`) does not serve `/uploads`

Existing working photos already live on CloudFront (`d1yfdszs9lcm9e.cloudfront.net`).
New uploads go to the same bucket so every teammate sees the same URL.
"""

from __future__ import annotations

import logging
import mimetypes
import os
import re
import uuid
from typing import Optional
from urllib.parse import urlparse

_PROPERTIES_CDN_RE = re.compile(r"^/properties/(\d+)/(.*)$")

logger = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 8 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}
EXT_BY_TYPE = {
    "image/jpeg": ".jpeg",
    "image/jpg": ".jpeg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def _settings():
    from app.core import config

    return config


def _normalize_content_type(filename: str, content_type: Optional[str]) -> str:
    ct = (content_type or "").strip().lower()
    if ct == "image/jpg":
        ct = "image/jpeg"
    if ct in ALLOWED_CONTENT_TYPES:
        return "image/jpeg" if ct == "image/jpg" else ct
    guessed, _ = mimetypes.guess_type(filename or "")
    guessed = (guessed or "").lower()
    if guessed == "image/jpg":
        guessed = "image/jpeg"
    if guessed in ALLOWED_CONTENT_TYPES:
        return guessed
    ext = os.path.splitext(filename or "")[1].lower()
    if ext in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if ext == ".png":
        return "image/png"
    if ext == ".webp":
        return "image/webp"
    return "image/jpeg"


def _s3_client():
    import boto3
    from botocore.config import Config as BotoConfig

    cfg = _settings()
    s3_config = BotoConfig(
        signature_version="s3v4",
        retries={"max_attempts": 3, "mode": "standard"},
    )
    kwargs = {
        "region_name": cfg.AWS_REGION,
        "config": s3_config,
    }
    if cfg.AWS_ACCESS_KEY_ID and cfg.AWS_SECRET_ACCESS_KEY:
        kwargs["aws_access_key_id"] = cfg.AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = cfg.AWS_SECRET_ACCESS_KEY
    return boto3.client("s3", **kwargs)


def _uploads_path_to_s3_key(path: str) -> str:
    """Map /uploads/images/foo.jpeg or uploads/foo.jpeg to S3 key uploads/foo.jpeg."""
    normalized = path.lstrip("/")
    if normalized.startswith("uploads/images/"):
        return "uploads/" + normalized[len("uploads/images/") :]
    if normalized.startswith("uploads/"):
        return normalized
    return f"uploads/{normalized}"


def _local_upload_path(relative_upload_path: str) -> str:
    """Absolute path under UPLOADS_DIR for a /uploads/... URL."""
    cfg = _settings()
    rel = relative_upload_path.lstrip("/")
    if rel.startswith("uploads/"):
        rel = rel[len("uploads/") :]
    return os.path.join(cfg.UPLOADS_DIR, rel)


def _local_upload_exists(relative_upload_path: str) -> bool:
    local_path = _local_upload_path(relative_upload_path)
    return os.path.isfile(local_path)


def _cdn_url_for_upload_path(upload_path: str) -> Optional[str]:
    cfg = _settings()
    if not (cfg.CLOUDFRONT_DOMAIN or cfg.S3_BUCKET_NAME):
        return None
    path = upload_path if upload_path.startswith("/") else f"/{upload_path}"
    if not path.startswith("/uploads/"):
        return None
    return public_url_for_key(_uploads_path_to_s3_key(path.lstrip("/")))


def public_url_for_key(key: str) -> str:
    cfg = _settings()
    domain = (cfg.CLOUDFRONT_DOMAIN or "").strip()
    if domain:
        if not domain.startswith("http"):
            domain = f"https://{domain}"
        return f"{domain.rstrip('/')}/{key.lstrip('/')}"
    if cfg.S3_BUCKET_NAME:
        return (
            f"https://{cfg.S3_BUCKET_NAME}.s3.{cfg.AWS_REGION}.amazonaws.com/"
            f"{key.lstrip('/')}"
        )
    base = cfg.PUBLIC_UPLOADS_BASE_URL
    local_path = f"/{key.lstrip('/')}"
    return f"{base}{local_path}" if base else local_path


def _reject_invalid_image_string(trimmed: str) -> Optional[str]:
    if not trimmed or trimmed in {"url1", "url2", "null", "undefined"}:
        return None
    if trimmed.startswith("data:"):
        if ";base64," not in trimmed or len(trimmed) < 1000:
            return None
        return trimmed
    return trimmed


def canonical_image_url_for_storage(url: Optional[str]) -> Optional[str]:
    """Normalize image URLs for DB persistence (prefer durable CloudFront URLs)."""
    if not url or not isinstance(url, str):
        return None
    trimmed = _reject_invalid_image_string(url.strip())
    if not trimmed:
        return None
    if trimmed.startswith("data:"):
        return trimmed

    if trimmed.startswith("http://") or trimmed.startswith("https://"):
        parsed = urlparse(trimmed)
        if parsed.path.startswith("/uploads/"):
            cdn = _cdn_url_for_upload_path(parsed.path)
            if cdn:
                return f"{cdn}?{parsed.query}" if parsed.query else cdn
        return trimmed

    path = trimmed if trimmed.startswith("/") else f"/{trimmed}"
    if path.startswith("/uploads/properties/"):
        path = path[len("/uploads") :]

    cdn_match = _PROPERTIES_CDN_RE.match(path)
    if cdn_match:
        return public_url_for_key(f"properties/{cdn_match.group(1)}/{cdn_match.group(2)}")

    if path.startswith("/properties/"):
        filename = path.replace("/properties/seed/", "/properties/").rsplit("/", 1)[-1]
        filename = filename.replace("_", " ")
        return f"/properties/{filename}"

    if path.startswith("/uploads/") or trimmed.startswith("uploads/"):
        path = "/" + trimmed.lstrip("/")
        if not path.startswith("/uploads/"):
            path = f"/uploads/{trimmed.lstrip('/')}"
        cdn = _cdn_url_for_upload_path(path)
        if cdn:
            return cdn
        cfg = _settings()
        base = cfg.PUBLIC_UPLOADS_BASE_URL
        return f"{base}{path}" if base else path

    return path if path.startswith("/") else f"/{trimmed}"


def normalize_image_url(url: Optional[str]) -> Optional[str]:
    """Turn stored image values into a browser-reachable URL, or None if unusable."""
    if not url or not isinstance(url, str):
        return None
    trimmed = _reject_invalid_image_string(url.strip())
    if not trimmed:
        return None
    if trimmed.startswith("data:"):
        return trimmed

    if trimmed.startswith("http://") or trimmed.startswith("https://"):
        parsed = urlparse(trimmed)
        if parsed.path.startswith("/uploads/"):
            cfg = _settings()
            if cfg.ENVIRONMENT == "development" and _local_upload_exists(parsed.path):
                return parsed.path
            cdn = _cdn_url_for_upload_path(parsed.path)
            if cdn:
                return f"{cdn}?{parsed.query}" if parsed.query else cdn
        return trimmed

    cfg = _settings()
    path = trimmed if trimmed.startswith("/") else f"/{trimmed}"
    if path.startswith("/uploads/properties/"):
        path = path[len("/uploads") :]

    cdn_match = _PROPERTIES_CDN_RE.match(path)
    if cdn_match:
        return public_url_for_key(f"properties/{cdn_match.group(1)}/{cdn_match.group(2)}")

    if path.startswith("/properties/"):
        filename = path.replace("/properties/seed/", "/properties/").rsplit("/", 1)[-1]
        filename = filename.replace("_", " ")
        return f"/properties/{filename}"

    if path.startswith("/uploads/") or trimmed.startswith("uploads/"):
        path = "/" + trimmed.lstrip("/")
        if not path.startswith("/uploads/"):
            path = f"/uploads/{trimmed.lstrip('/')}"

        if cfg.ENVIRONMENT == "development" and _local_upload_exists(path):
            return path

        cdn = _cdn_url_for_upload_path(path)
        if cdn:
            return cdn

        base = cfg.PUBLIC_UPLOADS_BASE_URL
        return f"{base}{path}" if base else path
    return path if path.startswith("/") else f"/{trimmed}"


def store_image_bytes(contents: bytes, filename: str = "", content_type: Optional[str] = None) -> str:
    if not contents:
        raise ValueError("Empty image file")
    if len(contents) > MAX_IMAGE_BYTES:
        raise ValueError("Image too large (max 8MB)")

    cfg = _settings()
    normalized_type = _normalize_content_type(filename, content_type)
    ext = EXT_BY_TYPE.get(normalized_type, ".jpeg")
    unique = uuid.uuid4().hex
    s3_key = f"uploads/{unique}{ext}"

    if cfg.S3_BUCKET_NAME:
        try:
            client = _s3_client()
            client.put_object(
                Bucket=cfg.S3_BUCKET_NAME,
                Key=s3_key,
                Body=contents,
                ContentType=normalized_type,
                CacheControl="public, max-age=31536000, immutable",
            )
            return public_url_for_key(s3_key)
        except Exception:
            logger.exception("S3 upload failed for property image")
            if cfg.S3_BUCKET_NAME:
                raise RuntimeError(
                    "Image upload to shared storage failed. Please retry in a moment."
                ) from None

    os.makedirs(os.path.join(cfg.UPLOADS_DIR, "images"), exist_ok=True)
    local_name = f"{unique}{ext}"
    local_path = os.path.join(cfg.UPLOADS_DIR, "images", local_name)
    with open(local_path, "wb") as handle:
        handle.write(contents)
    relative = f"/uploads/images/{local_name}"
    return f"{cfg.PUBLIC_UPLOADS_BASE_URL}{relative}" if cfg.PUBLIC_UPLOADS_BASE_URL else relative
