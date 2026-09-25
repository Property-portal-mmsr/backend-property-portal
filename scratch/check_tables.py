import urllib.parse
from sqlalchemy import create_engine, inspect, text

DB_HOST="127.0.0.1"
DB_PORT=3336
DB_USER="appuser"
DB_PASSWORD="StrongPassword@123"
DB_NAME_SOURCE="makemystay"

encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
engine = create_engine(f"mysql+pymysql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME_SOURCE}")
inspector = inspect(engine)
print("Makemystay Tables:", inspector.get_table_names())
