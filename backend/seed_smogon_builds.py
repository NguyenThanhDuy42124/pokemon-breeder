"""
Seed Smogon build templates into local SQLite with low-RAM stream processing.

Usage:
  cd backend
  python seed_smogon_builds.py --from-index
  python seed_smogon_builds.py --formats gen9ou,gen9monotype
  python seed_smogon_builds.py --formats gen9ou --clean
"""

import argparse
import json
import os
import re
from typing import Any

import requests
from sqlalchemy import delete, text
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from database import SessionLocal, engine
from models import Base, Pokemon, Move, SmogonBuild
from slugify_utils import slugify

try:
    import ijson  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - fallback for minimal environments
    ijson = None


SMOGON_BASE = "https://pkmn.github.io/smogon/data/sets"
INDEX_URL = f"{SMOGON_BASE}/index.json"
STAT_KEYS = ["hp", "atk", "def", "spa", "spd", "spe"]
GEN_PATTERN = re.compile(r"^gen([1-9])([a-z0-9-]+)$")


def pick_first(value: Any):
    if isinstance(value, list):
        if not value:
            return None
        first = value[0]
        if isinstance(first, list):
            return pick_first(first)
        return first
    return value


def parse_moves(raw_moves: Any) -> list[str]:
    if not isinstance(raw_moves, list):
        return []

    out = []
    for slot in raw_moves:
        picked = pick_first(slot)
        if isinstance(picked, str) and picked.strip():
            out.append(picked.strip())
    return out


def parse_target_ivs(raw_ivs: Any) -> list[bool]:
    target = [True, True, True, True, True, True]
    if not isinstance(raw_ivs, dict):
        return target

    for idx, key in enumerate(STAT_KEYS):
        if key in raw_ivs:
            try:
                target[idx] = int(raw_ivs[key]) >= 31
            except (TypeError, ValueError):
                target[idx] = True
    return target


def parse_generation_and_format(format_id: str) -> tuple[str, str]:
    m = GEN_PATTERN.match((format_id or "").lower())
    if not m:
        return "unknown", format_id or "unknown"
    return f"gen{m.group(1)}", m.group(2)


def ensure_schema_upgrade(db):
    # Add missing columns for old DB files and create critical indexes.
    columns = {row[1] for row in db.execute(text("PRAGMA table_info(smogon_builds)")).fetchall()}
    alter_specs = [
        ("pokemon_slug", "TEXT DEFAULT ''"),
        ("generation", "TEXT DEFAULT 'gen9'"),
        ("format_name", "TEXT DEFAULT 'ou'"),
        ("format_slug", "TEXT DEFAULT 'gen9ou'"),
        ("move_slugs_json", "TEXT DEFAULT '[]'"),
    ]
    for col, col_type in alter_specs:
        if col not in columns:
            db.execute(text(f"ALTER TABLE smogon_builds ADD COLUMN {col} {col_type}"))

    db.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_smogon_build_unique ON smogon_builds (pokemon_id, format, build_name)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_smogon_pokemon_id ON smogon_builds (pokemon_id)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_smogon_generation ON smogon_builds (generation)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_smogon_format ON smogon_builds (format)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_smogon_format_name ON smogon_builds (format_name)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_smogon_format_slug ON smogon_builds (format_slug)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_smogon_pokemon_slug ON smogon_builds (pokemon_slug)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_move_slug ON move (normalized_name)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_pokemon_slug ON pokemon (name)"))
    db.commit()


def ensure_move_id(db, move_name: str) -> int:
    normalized = slugify(move_name)
    existing = db.query(Move).filter(Move.normalized_name == normalized).first()
    if existing:
        return existing.id

    move = Move(name=move_name, normalized_name=normalized)
    db.add(move)
    db.flush()
    return move.id


def build_pokemon_lookup(db):
    return {slugify(p.name): p for p in db.query(Pokemon).all()}


def infer_hidden_ability(db, pokemon_id: int, ability_name: str | None) -> bool:
    if not ability_name:
        return False

    rows = db.execute(
        text(
            """
            SELECT a.name, pa.is_hidden
            FROM ability a
            JOIN pokemon_ability pa ON pa.ability_id = a.id
            WHERE pa.pokemon_id = :pokemon_id
            """
        ),
        {"pokemon_id": pokemon_id},
    ).fetchall()

    ability_slug = slugify(ability_name)
    for name, is_hidden in rows:
        if slugify(name) == ability_slug and bool(is_hidden):
            return True
    return False


def resolve_format_ids(args_formats: str | None, from_index: bool) -> list[str]:
    if args_formats:
        return [x.strip() for x in args_formats.split(",") if x.strip()]

    if not from_index:
        return ["gen9ou"]

    payload = requests.get(INDEX_URL, timeout=30).json()
    candidates = []
    if isinstance(payload, list):
        candidates = [str(x) for x in payload]
    elif isinstance(payload, dict):
        if isinstance(payload.get("formats"), list):
            candidates = [str(x) for x in payload["formats"]]
        else:
            candidates = [str(x) for x in payload.keys()]

    valid = []
    for fmt in candidates:
        if GEN_PATTERN.match(fmt.lower()):
            valid.append(fmt.lower())
    return sorted(set(valid))


def stream_download(url: str, target_file: str):
    with requests.get(url, stream=True, timeout=90) as resp:
        resp.raise_for_status()
        with open(target_file, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 64):
                if chunk:
                    f.write(chunk)


def stream_seed_format(db, format_id: str, local_path: str, source_url: str, pokemon_lookup: dict[str, Pokemon]) -> tuple[int, int]:
    generation, format_name = parse_generation_and_format(format_id)

    inserted = 0
    skipped = 0
    batch = 0

    with open(local_path, "rb") as f:
        if ijson:
            pokemon_iter = ijson.kvitems(f, "")
        else:
            payload = json.load(f)
            pokemon_iter = payload.items()

        for smogon_pokemon_name, builds_obj in pokemon_iter:
            pokemon = pokemon_lookup.get(slugify(str(smogon_pokemon_name)))
            if not pokemon or not isinstance(builds_obj, dict):
                skipped += 1
                continue

            for build_name, build_data in builds_obj.items():
                if not isinstance(build_data, dict):
                    continue

                nature = pick_first(build_data.get("nature"))
                ability = pick_first(build_data.get("ability"))
                item = pick_first(build_data.get("item"))
                moves = parse_moves(build_data.get("moves"))
                target_ivs = parse_target_ivs(build_data.get("ivs"))

                move_ids = []
                move_slugs = []
                for mv in moves:
                    move_ids.append(ensure_move_id(db, mv))
                    move_slugs.append(slugify(mv))

                requires_hidden_ability = infer_hidden_ability(db, pokemon.id, str(ability) if ability else None)

                row = {
                    "pokemon_id": pokemon.id,
                    "pokemon_slug": slugify(pokemon.name),
                    "format": format_id,
                    "generation": generation,
                    "format_name": format_name,
                    "format_slug": slugify(format_id),
                    "build_name": str(build_name),
                    "source_url": source_url,
                    "nature": str(nature) if nature else None,
                    "ability": str(ability) if ability else None,
                    "item": str(item) if item else None,
                    "moves_json": json.dumps(moves),
                    "move_slugs_json": json.dumps(move_slugs),
                    "move_ids_json": json.dumps(move_ids),
                    "target_ivs_json": json.dumps(target_ivs),
                    "requires_hidden_ability": requires_hidden_ability,
                }

                stmt = sqlite_insert(SmogonBuild).values(**row)
                upsert = stmt.on_conflict_do_update(
                    index_elements=["pokemon_id", "format", "build_name"],
                    set_={k: row[k] for k in row if k not in {"pokemon_id", "format", "build_name"}},
                )
                db.execute(upsert)

                inserted += 1
                batch += 1
                if batch >= 250:
                    db.commit()
                    batch = 0

    db.commit()
    return inserted, skipped


def main():
    parser = argparse.ArgumentParser(description="Seed Smogon sets into smogon_builds table")
    parser.add_argument("--formats", default=None, help="Comma-separated format IDs, ex: gen9ou,gen9monotype")
    parser.add_argument("--from-index", action="store_true", help="Load all available formats from index.json")
    parser.add_argument("--clean", action="store_true", help="Delete existing builds for selected formats before insert")
    args = parser.parse_args()

    format_ids = resolve_format_ids(args.formats, args.from_index)
    if not format_ids:
        print("No valid format IDs found.")
        return

    Base.metadata.create_all(bind=engine)

    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "smogon", "sets")
    os.makedirs(data_dir, exist_ok=True)

    db = SessionLocal()
    try:
        ensure_schema_upgrade(db)
        pokemon_lookup = build_pokemon_lookup(db)

        total_inserted = 0
        total_skipped = 0

        for fmt in format_ids:
            url = f"{SMOGON_BASE}/{fmt}.json"
            local_path = os.path.join(data_dir, f"{fmt}.json")

            print(f"Streaming download {url} ...")
            try:
                stream_download(url, local_path)
            except requests.RequestException as exc:
                print(f"[{fmt}] download failed: {exc}")
                continue

            if args.clean:
                db.execute(delete(SmogonBuild).where(SmogonBuild.format == fmt))
                db.commit()

            inserted, skipped = stream_seed_format(
                db=db,
                format_id=fmt,
                local_path=local_path,
                source_url=url,
                pokemon_lookup=pokemon_lookup,
            )
            total_inserted += inserted
            total_skipped += skipped

            print(f"[{fmt}] inserted/updated: {inserted}, skipped (pokemon map miss): {skipped}")
            print(f"Saved raw json: {local_path}")

        print("Done.")
        print(f"Total inserted/updated builds: {total_inserted}")
        print(f"Total skipped pokemon entries: {total_skipped}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
