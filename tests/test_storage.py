from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from app.utils import storage


def _make_cfg(**overrides):
    defaults = {
        "ENVIRONMENT": "production",
        "AWS_ACCESS_KEY_ID": "AKIADEADKEY123456789",
        "AWS_SECRET_ACCESS_KEY": "deadsecret",
        "AWS_REGION": "ap-south-1",
        "S3_BUCKET_NAME": "makemystayrealty",
        "CLOUDFRONT_DOMAIN": "d1yfdszs9lcm9e.cloudfront.net",
        "PUBLIC_UPLOADS_BASE_URL": "https://employee-api.makemystay.ai",
        "UPLOADS_DIR": "/tmp/test_uploads",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_store_image_bytes_falls_back_to_default_chain_on_invalid_static_key(monkeypatch):
    cfg = _make_cfg(ENVIRONMENT="production")
    monkeypatch.setattr(storage, "_settings", lambda: cfg)

    bad_client = MagicMock()
    bad_client.put_object.side_effect = ClientError(
        {"Error": {"Code": "InvalidAccessKeyId", "Message": "Invalid key"}},
        "PutObject",
    )
    iam_client = MagicMock()
    calls = []

    def fake_s3_client(use_configured_credentials: bool = True):
        calls.append(use_configured_credentials)
        return bad_client if use_configured_credentials else iam_client

    monkeypatch.setattr(storage, "_s3_client", fake_s3_client)

    url = storage.store_image_bytes(b"\xff\xd8\xff\xe0test", filename="photo.jpg", content_type="image/jpeg")

    assert calls == [True, False]
    assert iam_client.put_object.called
    assert url.startswith("https://d1yfdszs9lcm9e.cloudfront.net/uploads/")
    assert url.endswith(".jpeg")


def test_store_image_bytes_raises_503_runtime_error_in_production_when_s3_fails(monkeypatch):
    cfg = _make_cfg(ENVIRONMENT="production", AWS_ACCESS_KEY_ID="", AWS_SECRET_ACCESS_KEY="")
    monkeypatch.setattr(storage, "_settings", lambda: cfg)

    failing_client = MagicMock()
    failing_client.put_object.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Denied"}},
        "PutObject",
    )
    monkeypatch.setattr(storage, "_s3_client", lambda use_configured_credentials=True: failing_client)

    with pytest.raises(RuntimeError, match="Image upload to shared storage failed"):
        storage.store_image_bytes(b"\xff\xd8\xff\xe0test", filename="photo.jpg", content_type="image/jpeg")


def test_store_image_bytes_falls_back_to_local_disk_in_development(monkeypatch, tmp_path):
    cfg = _make_cfg(ENVIRONMENT="development", UPLOADS_DIR=str(tmp_path))
    monkeypatch.setattr(storage, "_settings", lambda: cfg)

    bad_client = MagicMock()
    bad_client.put_object.side_effect = ClientError(
        {"Error": {"Code": "InvalidAccessKeyId", "Message": "Invalid key"}},
        "PutObject",
    )
    monkeypatch.setattr(storage, "_s3_client", lambda use_configured_credentials=True: bad_client)

    url = storage.store_image_bytes(b"\xff\xd8\xff\xe0test", filename="photo.jpg", content_type="image/jpeg")

    assert url.startswith("/uploads/images/")
    saved_name = url.split("/")[-1]
    assert (tmp_path / "images" / saved_name).is_file()
    # Even when canonicalized to a CloudFront /uploads/<name> URL, normalize_image_url resolves back to local disk in dev
    assert storage.normalize_image_url(f"https://d1yfdszs9lcm9e.cloudfront.net/uploads/{saved_name}") == url
