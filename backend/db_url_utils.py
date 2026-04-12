"""Utilities for normalizing database URLs across environments."""


def normalize_database_url(raw_url: str | None) -> str | None:
    if not raw_url:
        return raw_url

    value = raw_url.strip()
    # Accept Java/JDBC style URL and convert it for SQLAlchemy.
    if value.startswith("jdbc:mysql://"):
        return "mysql+pymysql://" + value[len("jdbc:mysql://"):]

    # Accept plain mysql:// and route it through pymysql driver.
    if value.startswith("mysql://"):
        return "mysql+pymysql://" + value[len("mysql://"):]

    return value
