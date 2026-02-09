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
from sqlalchemy.orm import sessionmaker, declarative_base

# SQLite database file lives next to this script
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pokemon_breeding.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# echo=True → prints every SQL statement to the terminal (great for learning!)
# Set to False if the output gets too noisy.
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},  # needed for FastAPI + SQLite
)

# Enable SQLite foreign key enforcement (off by default!)
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
