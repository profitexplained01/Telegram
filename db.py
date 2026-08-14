import os

from sqlmodel import create_engine
from sqlalchemy import event

from config import settings


# Ensure data directory exists before creating the SQLite DB file.
os.makedirs("./data", exist_ok=True)

connect_args = {}

if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {
        "timeout": 30,
    }

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args=connect_args,
)

# SQLite optimizations.
# WAL mode helps prevent write locks when webhook traffic comes in.
if settings.DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()

        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA busy_timeout=30000;")

        cursor.close()
