"""Migrate all core tables from local SQLite to MySQL.

Usage:
  python migrate_sqlite_to_mysql.py --mysql-url "jdbc:mysql://user:pass@host:3307/db"
"""

from __future__ import annotations

import argparse
import os
from typing import Iterable

from sqlalchemy import MetaData, Table, create_engine, select, text

from db_url_utils import normalize_database_url
from models import Base


TABLE_ORDER = [
    "pokemon",
    "egg_group",
    "ability",
    "nature",
    "pokemon_egg_group",
    "pokemon_ability",
    "move",
    "pokemon_moves",
    "pokemon_move_learn",
    "smogon_builds",
]


def copy_table(source_engine, target_engine, table_name: str) -> int:
    src_meta = MetaData()
    dst_meta = MetaData()
    src_table = Table(table_name, src_meta, autoload_with=source_engine)
    dst_table = Table(table_name, dst_meta, autoload_with=target_engine)

    rows_copied = 0
    with source_engine.connect() as src_conn, target_engine.begin() as dst_conn:
        result = src_conn.execute(select(src_table))
        batch = []
        for row in result.mappings():
            batch.append(dict(row))
            if len(batch) >= 1000:
                dst_conn.execute(dst_table.insert(), batch)
                rows_copied += len(batch)
                batch = []

        if batch:
            dst_conn.execute(dst_table.insert(), batch)
            rows_copied += len(batch)

    return rows_copied


def reset_mysql_autoincrement(target_engine, table_names: Iterable[str]):
    with target_engine.begin() as conn:
        for table_name in table_names:
            conn.execute(text(f"ALTER TABLE {table_name} AUTO_INCREMENT = 1"))


def clear_target_tables(target_engine):
    with target_engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        for table_name in reversed(TABLE_ORDER):
            conn.execute(text(f"DELETE FROM {table_name}"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate SQLite data to MySQL")
    parser.add_argument("--sqlite-url", default=None, help="Optional SQLite SQLAlchemy URL")
    parser.add_argument("--mysql-url", required=True, help="MySQL SQLAlchemy/JDBC URL")
    args = parser.parse_args()

    backend_dir = os.path.dirname(os.path.abspath(__file__))
    sqlite_url = args.sqlite_url or f"sqlite:///{os.path.join(backend_dir, 'pokemon_breeding.db')}"
    mysql_url = normalize_database_url(args.mysql_url)
    if not mysql_url:
        raise SystemExit("MySQL URL is required")

    source_engine = create_engine(sqlite_url)
    target_engine = create_engine(mysql_url, pool_pre_ping=True)

    # Create target schema from ORM models first.
    Base.metadata.create_all(bind=target_engine)
    clear_target_tables(target_engine)

    print("Starting SQLite -> MySQL migration...")
    for table_name in TABLE_ORDER:
        copied = copy_table(source_engine, target_engine, table_name)
        print(f"[{table_name}] copied rows: {copied}")

    reset_mysql_autoincrement(
        target_engine,
        ["move", "pokemon_moves", "pokemon_move_learn", "smogon_builds"],
    )

    print("Migration completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
