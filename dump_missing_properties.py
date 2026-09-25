import urllib.parse
from sqlalchemy import create_engine, text

# DB Config
DB_HOST="127.0.0.1"
DB_PORT=3336
DB_USER="appuser"
DB_PASSWORD="StrongPassword@123"
DB_NAME_SOURCE="makemystay"
DB_NAME_DEST="property_portal"

encoded_password = urllib.parse.quote_plus(DB_PASSWORD)

engine_source = create_engine(f"mysql+pymysql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME_SOURCE}")
engine_dest = create_engine(f"mysql+pymysql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME_DEST}")

with engine_source.connect() as conn_src:
    src_properties = conn_src.execute(text("SELECT id FROM properties")).fetchall()
    src_ids = [row[0] for row in src_properties]

with engine_dest.connect() as conn_dest:
    dest_properties = conn_dest.execute(text("SELECT id FROM properties")).fetchall()
    dest_ids = [row[0] for row in dest_properties]

missing_ids = set(src_ids) - set(dest_ids)
print(f"Total Source Properties: {len(src_ids)}")
print(f"Total Dest Properties: {len(dest_ids)}")
print(f"Missing IDs: {len(missing_ids)}")

if not missing_ids:
    print("No missing properties found.")
    exit(0)

# Also check for photos table
with engine_source.connect() as conn_src:
    src_photos = conn_src.execute(text("SELECT id FROM property_photos")).fetchall()
    print(f"Total Source Photos: {len(src_photos)}")

print("Done checking.")
