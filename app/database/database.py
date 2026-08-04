import logging
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import (
    DB_HOST,
    DB_PORT,
    DB_NAME,
    DB_USER,
    DB_PASSWORD,
)

logger = logging.getLogger(__name__)

MYSQL_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
SQLITE_URL = "sqlite:///./property_portal.db"

try:
    engine = create_engine(MYSQL_URL, pool_pre_ping=True)
    with engine.connect() as conn:
        pass
    logger.info(f"Connected to MySQL database at {DB_HOST}:{DB_PORT}/{DB_NAME}")
    DATABASE_URL = MYSQL_URL
except Exception as e:
    logger.warning(
        f"MySQL database unavailable ({e}). Falling back to SQLite local database."
    )
    DATABASE_URL = SQLITE_URL
    engine = create_engine(
        SQLITE_URL,
        connect_args={"check_same_thread": False},
    )

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def sync_table_schema(engine, base):
    """Automatically adds missing columns to existing MySQL/SQLite tables."""
    try:
        inspector = inspect(engine)
        with engine.begin() as conn:
            for table_name, table_obj in base.metadata.tables.items():
                if inspector.has_table(table_name):
                    existing_columns = {
                        col["name"] for col in inspector.get_columns(table_name)
                    }
                    for column in table_obj.columns:
                        if column.name not in existing_columns:
                            col_type = column.type.compile(engine.dialect)
                            try:
                                sql = f"ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type} NULL"
                                conn.execute(text(sql))
                                logger.info(
                                    f"Added missing column '{column.name}' to table '{table_name}'"
                                )
                            except Exception as col_err:
                                logger.warning(
                                    f"Could not add column '{column.name}' to '{table_name}': {col_err}"
                                )
    except Exception as e:
        logger.error(f"Error checking/syncing table schema: {e}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()