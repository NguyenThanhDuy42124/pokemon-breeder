"""
database.py – Database connection setup.

HOW IT WORKS (for beginners):
1. DATABASE_URL tells SQLAlchemy WHERE your database file is.
   Format: sqlite:///path/to/file.db
2. engine    = the "connection" to SQLite.
3. SessionLocal = a factory that creates database sessions (like opening a notebook to write).
4. Base      = every model class inherits from this so SQLAlchemy tracks them.
"""

import os
from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, declarative_base
from db_url_utils import normalize_database_url

# SQLite database file lives next to this script
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pokemon_breeding.db")
DEFAULT_SQLITE_URL = f"sqlite:///{DB_PATH}"


def _load_database_url_from_env_mysql() -> str | None:
    """Load DATABASE_URL from project-level .env.mysql when env var is missing."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_file_path = os.path.join(project_root, ".env.mysql")
    if not os.path.exists(env_file_path):
        return None

    try:
        with open(env_file_path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                if key.strip() != "DATABASE_URL":
                    continue
                cleaned = value.strip().strip('"').strip("'")
                return cleaned or None
    except Exception:
        return None

    return None


raw_database_url = os.getenv("DATABASE_URL") or _load_database_url_from_env_mysql()
DATABASE_URL = normalize_database_url(raw_database_url) or DEFAULT_SQLITE_URL

is_sqlite = DATABASE_URL.startswith("sqlite://")


def get_database_runtime_info() -> dict[str, str]:
    """Return safe DB runtime details for startup logs."""
    try:
        url = make_url(DATABASE_URL)
        backend = (url.get_backend_name() or "unknown").lower()

        if backend == "mysql":
            return {
                "engine": "MySQL",
                "name": url.database or "unknown",
            }

        if backend == "sqlite":
            if url.database in (None, "", ":memory:"):
                db_name = ":memory:"
            else:
                db_name = os.path.basename(url.database)
            return {
                "engine": "SQLite",
                "name": db_name,
            }

        return {
            "engine": backend.upper(),
            "name": url.database or "unknown",
        }
    except Exception:
        return {
            "engine": "UNKNOWN",
            "name": "unknown",
        }

connect_args = {}
if is_sqlite:
    connect_args = {
        "check_same_thread": False,
        "timeout": 30,
    }

# echo=True → prints every SQL statement to the terminal (great for learning!)
# Set to False if the output gets too noisy.
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args=connect_args,
    pool_pre_ping=True,
)

# Enable SQLite foreign key enforcement (off by default!)
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if not is_sqlite:
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
