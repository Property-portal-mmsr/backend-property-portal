import urllib.parse
from sqlalchemy import create_engine, text

DB_HOST="127.0.0.1"
DB_PORT=3336
DB_USER="appuser"
DB_PASSWORD="StrongPassword@123"

encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
engine_mms = create_engine(f"mysql+pymysql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/makemystay")
engine_pp = create_engine(f"mysql+pymysql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/property_portal")

with engine_mms.connect() as conn:
    print("MMS Pricing schema:")
    res = conn.execute(text("DESCRIBE property_pricing")).fetchall()
    for row in res:
        print(row)
        
    print("\nMMS Status unique values:")
    res = conn.execute(text("SELECT status, count(*) FROM properties GROUP BY status")).fetchall()
    print(res)

with engine_pp.connect() as conn:
    print("\nPP Pricing schema:")
    res = conn.execute(text("DESCRIBE property_pricing")).fetchall()
    for row in res:
        print(row)
        
    print("\nPP Status unique values:")
    res = conn.execute(text("SELECT status, count(*) FROM properties GROUP BY status")).fetchall()
    print(res)

