"""Upload leftover data-URI property photos to CloudFront so they load for everyone."""

from dotenv import load_dotenv
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
load_dotenv(os.path.join(ROOT, ".env"))

import base64
import re
from sqlalchemy.orm import selectinload

from app.database.database import SessionLocal
from app.models.owner import Owner  # noqa: F401  # register FK target
from app.models.property import Property, PropertyImage
from app.utils.storage import store_image_bytes

DATA_URI_RE = re.compile(r"^data:(image/[\w.+-]+);base64,(.+)$", re.DOTALL)


def promote(url: str) -> str:
    if not isinstance(url, str):
        return url
    match = DATA_URI_RE.match(url.strip())
    if not match:
        return url
    mime, payload = match.group(1), match.group(2)
    try:
        contents = base64.b64decode(payload)
    except Exception:
        return url
    if not contents:
        return url
    return store_image_bytes(contents, filename=f"inline.{mime.split('/')[-1]}", content_type=mime)


def main():
    db = SessionLocal()
    changed = 0
    try:
        props = db.query(Property).options(selectinload(Property.property_images)).all()
        for prop in props:
            json_changed = False
            if isinstance(prop.images, list):
                new_json = []
                for url in prop.images:
                    promoted = promote(url) if isinstance(url, str) else url
                    if promoted != url:
                        json_changed = True
                        changed += 1
                    new_json.append(promoted)
                if json_changed:
                    prop.images = new_json

            row_changed = False
            for img in prop.property_images or []:
                if not img.image_url:
                    continue
                promoted = promote(img.image_url)
                if promoted != img.image_url:
                    img.image_url = promoted
                    row_changed = True
                    changed += 1

            if json_changed or row_changed:
                db.commit()
                print(f"updated {prop.id} {prop.property_name}")

        print(f"Promoted {changed} inline images to CloudFront/S3")
    finally:
        db.close()


if __name__ == "__main__":
    main()
