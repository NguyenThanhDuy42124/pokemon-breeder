"""
Seed Smogon build templates into local SQLite with low-RAM stream processing.

Usage:
  cd backend
  python seed_smogon_builds.py --from-index
  python seed_smogon_builds.py --formats gen9ou,gen9monotype
  python seed_smogon_builds.py --formats gen9ou --clean
"""

import argparse
import datetime
import json
import os
import re
import time
from typing import Any

import requests
from sqlalchemy import delete, text
from sqlalchemy import tuple_
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.dialects.mysql import insert as mysql_insert

from database import SessionLocal, engine
from models import Base, Pokemon, Move, SmogonBuild, CrawlHistory
from slugify_utils import slugify

try:
    import ijson  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - fallback for minimal environments
    ijson = None


SMOGON_BASE = "https://pkmn.github.io/smogon/data/sets"
INDEX_URL = f"{SMOGON_BASE}/index.json"
STAT_KEYS = ["hp", "atk", "def", "spa", "spd", "spe"]
GEN_PATTERN = re.compile(r"^gen([1-9])([a-z0-9-]*)$")
BATCH_COMMIT_SIZE = 1000

PRESET_GEN9_CORE = [
    "gen9ou",
    "gen9uu",
    "gen9ru",
    "gen9nu",
    "gen9ubers",
    "gen9lc",
    "gen9monotype",
    "gen91v1",
    "gen9doublesou",
    "gen9randombattle",
]

PRESET_EXPANDED_SUFFIXES = [
    "1v1",
    "doublesou",
    "doublesubers",
    "doublesuu",
    "ou",
    "uu",
    "ru",
    "nu",
    "pu",
    "ubers",
    "lc",
    "nfe",
    "zu",
    "uubl",
    "rubl",
    "nubl",
    "publ",
    "zubl",
    "nationaldex",
    "nationaldexou",
    "nationaldexuu",
    "nationaldexru",
    "nationaldexubers",
    "nationaldexmonotype",
    "nationaldexdoubles",
    "nationaldexrotational",
    "randombattle",
    "randomdoublesbattle",
    "almostanyability",
    "balancedhackmons",
    "stabmons",
    "camomons",
    "mixandmega",
    "godlygift",
    "sharedpower",
    "partnersincrime",
    "inheritance",
    "metronomebattle",
    "cap",
    "monotype",
    "draft",
    "leaderschoice",
    "ssb",
    "challengecup1v1",
    "battlefactory",
    "vgc2024",
    "vgc2023series1",
    "vgc2023series2",
    "vgc2023series3",
    "vgc2023series4",
    "vgc2024regulatione",
    "vgc2024regulationf",
    "vgc2024regulationg",
    "vgc2025regulationi",
    "battlestadiumsingles",
    "bssseries1",
    "bssseries2",
    "anythinggoes",
    "ubersuu",
    "omms",
    "omotm",
]

PRESET_CORE_SUFFIXES = [
    "ou",
    "uu",
    "ru",
    "nu",
    "ubers",
    "lc",
    "monotype",
    "1v1",
    "doublesou",
    "randombattle",
]

PRESET_GEN9_EXPANDED = [f"gen9{suffix}" for suffix in PRESET_EXPANDED_SUFFIXES]

FORMAT_PRESETS = {
    "core": [f"gen9{suffix}" for suffix in PRESET_CORE_SUFFIXES],
    "expanded": PRESET_GEN9_EXPANDED,
    "gen9-core": PRESET_GEN9_CORE,
    "gen9-expanded": PRESET_GEN9_EXPANDED,
}

INDEX_DRIVEN_STAGE_PRESETS = {
    "stage1",
    "stage-1",
    "backbone",
    "backbone-all-gens",
    "stage2",
    "stage-2",
    "stage3",
    "stage-3",
}

FORMAT_ALIASES = {
    "1v1": "1v1",
    "2v2doubles": "doublesou",
    "doubles": "doublesou",
    "doublesou": "doublesou",
    "doublesubers": "doublesubers",
    "doublesuu": "doublesuu",
    "ou": "ou",
    "uu": "uu",
    "ru": "ru",
    "nu": "nu",
    "pu": "pu",
    "uber": "ubers",
    "ubers": "ubers",
    "lc": "lc",
    "nfe": "nfe",
    "zu": "zu",
    "uubl": "uubl",
    "rubl": "rubl",
    "nubl": "nubl",
    "publ": "publ",
    "zubl": "zubl",
    "nationaldex": "nationaldex",
    "nationaldexou": "nationaldexou",
    "nationaldexuu": "nationaldexuu",
    "nationaldexru": "nationaldexru",
    "nationaldexubers": "nationaldexubers",
    "nationaldexmonotype": "nationaldexmonotype",
    "nationaldexdoubles": "nationaldexdoubles",
    "nationaldexrotational": "nationaldexrotational",
    "randombattle": "randombattle",
    "randomdoubles": "randomdoublesbattle",
    "randomdoublesbattle": "randomdoublesbattle",
    "almostanyability": "almostanyability",
    "aaa": "almostanyability",
    "balancedhackmons": "balancedhackmons",
    "bh": "balancedhackmons",
    "stabmons": "stabmons",
    "camomons": "camomons",
    "mixandmega": "mixandmega",
    "godlygift": "godlygift",
    "sharedpower": "sharedpower",
    "partnersincrime": "partnersincrime",
    "inheritance": "inheritance",
    "inh": "inheritance",
    "metronomebattle": "metronomebattle",
    "cap": "cap",
    "monotype": "monotype",
    "draft": "draft",
    "leaderschoice": "leaderschoice",
    "ssb": "ssb",
    "cc1v1": "challengecup1v1",
    "challengecup1v1": "challengecup1v1",
    "battlefactory": "battlefactory",
    "vgc": "vgc2024",
    "vgc2024": "vgc2024",
    "vgc23series1": "vgc2023series1",
    "vgc23series2": "vgc2023series2",
    "vgc23series3": "vgc2023series3",
    "vgc23series4": "vgc2023series4",
    "vgc24regulatione": "vgc2024regulatione",
    "vgc24regulationf": "vgc2024regulationf",
    "vgc24regulationg": "vgc2024regulationg",
    "vgc25regulationi": "vgc2025regulationi",
    "battlestadiumsingles": "battlestadiumsingles",
    "bssseries1": "bssseries1",
    "bssseries2": "bssseries2",
    "ag": "anythinggoes",
    "anythinggoes": "anythinggoes",
    "ubersuu": "ubersuu",
    "ommspotlight": "omms",
    "omms": "omms",
    "omotm": "omotm",
}


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
    suffix = m.group(2) or "base"
    return f"gen{m.group(1)}", suffix


def _normalize_token(raw: str) -> str:
    value = (raw or "").strip().lower()
    value = value.replace("&", "and")
    value = value.replace("'", "")
    return re.sub(r"[^a-z0-9]", "", value)


def _resolve_format_token(raw_token: str, default_generation: int) -> str | None:
    token = (raw_token or "").strip()
    if not token:
        return None

    lowered = token.lower()
    if GEN_PATTERN.match(lowered):
        return lowered

    compact = _normalize_token(token)
    if GEN_PATTERN.match(compact):
        return compact

    suffix = FORMAT_ALIASES.get(compact)
    if suffix:
        return f"gen{default_generation}{suffix}"
    return None


def _parse_formats_arg(args_formats: str, default_generation: int) -> tuple[list[str], list[str]]:
    resolved: list[str] = []
    unknown: list[str] = []

    raw_tokens = [x.strip() for x in re.split(r"[,;\n]", args_formats or "") if x.strip()]
    expanded_tokens: list[str] = []
    for token in raw_tokens:
        if "/" in token:
            parts = [p.strip() for p in token.split("/") if p.strip()]
            expanded_tokens.extend(parts)
        else:
            expanded_tokens.append(token)

    for token in expanded_tokens:
        fmt = _resolve_format_token(token, default_generation)
        if fmt:
            resolved.append(fmt)
        else:
            unknown.append(token)

    return sorted(set(resolved)), unknown


def _resolve_preset(preset: str | None, default_generation: int) -> list[str]:
    if not preset:
        return []

    if preset in FORMAT_PRESETS:
        if preset in {"core", "expanded"}:
            suffixes = PRESET_CORE_SUFFIXES if preset == "core" else PRESET_EXPANDED_SUFFIXES
            return [f"gen{default_generation}{suffix}" for suffix in suffixes]
        return list(FORMAT_PRESETS[preset])

    m = re.match(r"^gen([1-9])-(core|expanded)$", preset)
    if m:
        gen = int(m.group(1))
        mode = m.group(2)
        suffixes = PRESET_CORE_SUFFIXES if mode == "core" else PRESET_EXPANDED_SUFFIXES
        return [f"gen{gen}{suffix}" for suffix in suffixes]

    return []


def _extract_index_formats(payload: Any) -> list[str]:
    candidates: list[str] = []
    if isinstance(payload, list):
        candidates = [str(x) for x in payload]
    elif isinstance(payload, dict):
        if isinstance(payload.get("formats"), list):
            candidates = [str(x) for x in payload["formats"]]
        else:
            candidates = [str(x) for x in payload.keys()]

    valid: list[str] = []
    for fmt in candidates:
        normalized = str(fmt).strip().lower()
        if normalized.endswith(".json"):
            normalized = normalized[:-5]
        if GEN_PATTERN.match(normalized):
            valid.append(normalized)
    return sorted(set(valid))


def _fetch_index_formats() -> list[str]:
    try:
        payload = requests.get(INDEX_URL, timeout=30).json()
        return _extract_index_formats(payload)
    except Exception:
        return []


def _resolve_index_stage_preset(preset: str, index_formats: list[str]) -> list[str]:
    key = (preset or "").strip().lower()
    if key in {"stage1", "stage-1", "backbone", "backbone-all-gens"}:
        return sorted(
            fmt
            for fmt in index_formats
            if re.match(r"^gen[1-9]ou$", fmt) or re.match(r"^gen[1-9]vgc", fmt)
        )

    if key in {"stage2", "stage-2"}:
        base = _resolve_index_stage_preset("stage1", index_formats)
        extra = [
            fmt
            for fmt in index_formats
            if re.match(r"^gen(8|9)(uu|ru|nu)$", fmt)
        ]
        return sorted(set(base + extra))

    if key in {"stage3", "stage-3"}:
        base = _resolve_index_stage_preset("stage2", index_formats)
        extra = [
            fmt
            for fmt in index_formats
            if re.match(r"^gen9nationaldex", fmt)
        ]
        return sorted(set(base + extra))

    return []


def ensure_schema_upgrade(db):
    dialect = db.bind.dialect.name

    if dialect == "mysql":
        # Ensure high-cardinality lookup indexes for large MySQL datasets.
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_smogon_pokemon_id ON smogon_builds (pokemon_id)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_smogon_generation ON smogon_builds (generation)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_smogon_format ON smogon_builds (format)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_smogon_pokemon_gen_format ON smogon_builds (pokemon_id, generation, format)"))

        # Keep a generation-aware unique key used by ON DUPLICATE KEY UPDATE.
        # Old deployments may still have uq_smogon_build_unique; this new key is additive and safe.
        db.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_smogon_build_unique_v2
                ON smogon_builds (pokemon_id, format, generation, build_name)
                """
            )
        )
        db.commit()
        return

    if dialect != "sqlite":
        return

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

    db.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_smogon_build_unique ON smogon_builds (pokemon_id, format, generation, build_name)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_smogon_pokemon_id ON smogon_builds (pokemon_id)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_smogon_generation ON smogon_builds (generation)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_smogon_format ON smogon_builds (format)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_smogon_format_name ON smogon_builds (format_name)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_smogon_format_slug ON smogon_builds (format_slug)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_smogon_pokemon_slug ON smogon_builds (pokemon_slug)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_move_slug ON move (normalized_name)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_pokemon_slug ON pokemon (name)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_smogon_pokemon_gen_format ON smogon_builds (pokemon_id, generation, format)"))
    db.commit()


def upsert_crawl_history(
    db,
    format_id: str,
    generation: str,
    source_url: str,
    status: str,
    record_count: int = 0,
    skipped_count: int = 0,
    error_log: str | None = None,
):
    now = datetime.datetime.utcnow()
    row = {
        "source": "smogon",
        "format": format_id,
        "generation": generation,
        "status": status,
        "record_count": int(record_count),
        "skipped_count": int(skipped_count),
        "error_log": error_log,
        "source_url": source_url,
        "updated_at": now,
        "last_synced_at": now if status == "success" else None,
    }

    dialect = db.bind.dialect.name
    if dialect == "mysql":
        stmt = mysql_insert(CrawlHistory).values(**row)
        upsert = stmt.on_duplicate_key_update(**{k: row[k] for k in row if k != "format"})
    else:
        stmt = sqlite_insert(CrawlHistory).values(**row)
        upsert = stmt.on_conflict_do_update(
            index_elements=["format"],
            set_={k: row[k] for k in row if k != "format"},
        )
    db.execute(upsert)
    db.commit()


def build_move_lookup(db) -> dict[str, int]:
    return {m.normalized_name: m.id for m in db.query(Move).all()}


def ensure_move_id(db, move_name: str, move_id_cache: dict[str, int]) -> int:
    normalized = slugify(move_name)
    cached = move_id_cache.get(normalized)
    if cached:
        return cached

    move = Move(name=move_name, normalized_name=normalized)
    db.add(move)
    db.flush()
    move_id_cache[normalized] = move.id
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


def resolve_format_ids(
    args_formats: str | None,
    from_index: bool,
    preset: str | None,
    default_generation: int = 9,
) -> tuple[list[str], list[str]]:
    selected: list[str] = []
    unknown: list[str] = []
    index_formats: list[str] | None = None

    if preset:
        if preset.strip().lower() in INDEX_DRIVEN_STAGE_PRESETS:
            index_formats = _fetch_index_formats()
            selected.extend(_resolve_index_stage_preset(preset, index_formats))
        else:
            selected.extend(_resolve_preset(preset, default_generation))

    if args_formats:
        resolved, unresolved = _parse_formats_arg(args_formats, default_generation)
        selected.extend(resolved)
        unknown.extend(unresolved)

    if selected:
        return sorted(set(selected)), unknown

    if not from_index:
        return ["gen9ou"], unknown

    if index_formats is None:
        index_formats = _fetch_index_formats()
    return index_formats, unknown


def stream_download(url: str, target_file: str, retries: int = 3):
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            with requests.get(url, stream=True, timeout=90) as resp:
                resp.raise_for_status()
                with open(target_file, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=1024 * 64):
                        if chunk:
                            f.write(chunk)
            return
        except requests.RequestException as exc:
            last_exc = exc
            if attempt >= retries:
                break
            time.sleep(min(2 * attempt, 6))
    raise last_exc


def stream_seed_format(
    db,
    format_id: str,
    local_path: str,
    source_url: str,
    pokemon_lookup: dict[str, Pokemon],
    move_id_cache: dict[str, int],
) -> tuple[int, int]:
    generation, format_name = parse_generation_and_format(format_id)
    dialect = db.bind.dialect.name

    inserted = 0
    updated = 0
    skipped = 0

    if ijson is None:
        raise RuntimeError("ijson is required for stream parsing. Install ijson before full ingest.")

    def _flush_rows(rows: list[dict[str, Any]]):
        nonlocal inserted, updated
        if not rows:
            return

        keys = [(r["pokemon_id"], r["format"], r["generation"], r["build_name"]) for r in rows]
        existing_rows = (
            db.query(
                SmogonBuild.pokemon_id,
                SmogonBuild.format,
                SmogonBuild.generation,
                SmogonBuild.build_name,
            )
            .filter(tuple_(SmogonBuild.pokemon_id, SmogonBuild.format, SmogonBuild.generation, SmogonBuild.build_name).in_(keys))
            .all()
        )
        existing_keys = {(r[0], r[1], r[2], r[3]) for r in existing_rows}

        inserted += sum(1 for k in keys if k not in existing_keys)
        updated += sum(1 for k in keys if k in existing_keys)

        if dialect == "mysql":
            stmt = mysql_insert(SmogonBuild).values(rows)
            upsert = stmt.on_duplicate_key_update(
                pokemon_slug=stmt.inserted.pokemon_slug,
                format_name=stmt.inserted.format_name,
                format_slug=stmt.inserted.format_slug,
                source_url=stmt.inserted.source_url,
                nature=stmt.inserted.nature,
                ability=stmt.inserted.ability,
                item=stmt.inserted.item,
                moves_json=stmt.inserted.moves_json,
                move_slugs_json=stmt.inserted.move_slugs_json,
                move_ids_json=stmt.inserted.move_ids_json,
                target_ivs_json=stmt.inserted.target_ivs_json,
                requires_hidden_ability=stmt.inserted.requires_hidden_ability,
            )
        else:
            stmt = sqlite_insert(SmogonBuild).values(rows)
            upsert = stmt.on_conflict_do_update(
                index_elements=["pokemon_id", "format", "generation", "build_name"],
                set_={
                    "pokemon_slug": stmt.excluded.pokemon_slug,
                    "format_name": stmt.excluded.format_name,
                    "format_slug": stmt.excluded.format_slug,
                    "source_url": stmt.excluded.source_url,
                    "nature": stmt.excluded.nature,
                    "ability": stmt.excluded.ability,
                    "item": stmt.excluded.item,
                    "moves_json": stmt.excluded.moves_json,
                    "move_slugs_json": stmt.excluded.move_slugs_json,
                    "move_ids_json": stmt.excluded.move_ids_json,
                    "target_ivs_json": stmt.excluded.target_ivs_json,
                    "requires_hidden_ability": stmt.excluded.requires_hidden_ability,
                },
            )
        db.execute(upsert)
        db.commit()

    with open(local_path, "rb") as f:
        pokemon_iter = ijson.kvitems(f, "")
        pending_rows: list[dict[str, Any]] = []

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
                    move_ids.append(ensure_move_id(db, mv, move_id_cache))
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

                pending_rows.append(row)
                if len(pending_rows) >= BATCH_COMMIT_SIZE:
                    _flush_rows(pending_rows)
                    pending_rows = []

        _flush_rows(pending_rows)

    return inserted, updated, skipped


def main():
    parser = argparse.ArgumentParser(description="Seed Smogon sets into smogon_builds table")
    parser.add_argument(
        "--generation",
        type=int,
        choices=list(range(1, 10)),
        default=9,
        help="Default generation used when formats are provided as aliases (ou,uu,bh,vgc...).",
    )
    parser.add_argument(
        "--formats",
        default=None,
        help="Comma-separated format IDs or aliases, ex: gen9ou,gen9monotype,ou,1v1,vgc",
    )
    parser.add_argument(
        "--preset",
        default=None,
        help="Named format preset, ex: core, expanded, gen9-core, gen6-expanded",
    )
    parser.add_argument("--from-index", action="store_true", help="Load all available formats from index.json")
    parser.add_argument("--clean", action="store_true", help="Delete existing builds for selected formats before insert")
    args = parser.parse_args()

    format_ids, unknown_tokens = resolve_format_ids(
        args.formats,
        args.from_index,
        args.preset,
        default_generation=args.generation,
    )
    if not format_ids:
        print("No valid format IDs found.")
        return

    if unknown_tokens:
        print(f"Ignored unknown format tokens: {', '.join(unknown_tokens)}")

    if ijson is None:
        print("ERROR: ijson is required for full ingest stream mode. Install it first: pip install ijson")
        return

    Base.metadata.create_all(bind=engine)

    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "smogon", "sets")
    os.makedirs(data_dir, exist_ok=True)

    db = SessionLocal()
    try:
        ensure_schema_upgrade(db)
        pokemon_lookup = build_pokemon_lookup(db)
        move_id_cache = build_move_lookup(db)

        total_inserted = 0
        total_updated = 0
        total_skipped = 0
        failed_formats: list[str] = []

        for fmt in format_ids:
            url = f"{SMOGON_BASE}/{fmt}.json"
            local_path = os.path.join(data_dir, f"{fmt}.json")
            generation, _ = parse_generation_and_format(fmt)

            upsert_crawl_history(
                db=db,
                format_id=fmt,
                generation=generation,
                source_url=url,
                status="pending",
                record_count=0,
                skipped_count=0,
                error_log=None,
            )

            print(f"Streaming download {url} ...")
            try:
                stream_download(url, local_path)
            except requests.RequestException as exc:
                print(f"[{fmt}] download failed: {exc}")
                failed_formats.append(fmt)
                upsert_crawl_history(
                    db=db,
                    format_id=fmt,
                    generation=generation,
                    source_url=url,
                    status="failed",
                    error_log=str(exc),
                )
                continue

            if args.clean:
                db.execute(delete(SmogonBuild).where(SmogonBuild.format == fmt))
                db.commit()

            try:
                inserted, updated, skipped = stream_seed_format(
                    db=db,
                    format_id=fmt,
                    local_path=local_path,
                    source_url=url,
                    pokemon_lookup=pokemon_lookup,
                    move_id_cache=move_id_cache,
                )
            except Exception as exc:
                failed_formats.append(fmt)
                upsert_crawl_history(
                    db=db,
                    format_id=fmt,
                    generation=generation,
                    source_url=url,
                    status="failed",
                    error_log=str(exc),
                )
                print(f"[{fmt}] parse/seed failed for file {local_path}: {exc}")
                continue

            total_inserted += inserted
            total_updated += updated
            total_skipped += skipped

            upsert_crawl_history(
                db=db,
                format_id=fmt,
                generation=generation,
                source_url=url,
                status="success",
                record_count=inserted + updated,
                skipped_count=skipped,
                error_log=None,
            )

            print(f"[{fmt}] inserted: {inserted}, updated: {updated}, skipped (pokemon map miss): {skipped}")
            print(f"Saved raw json: {local_path}")

        total_rows = db.query(SmogonBuild).count()
        print("Done.")
        print(f"Total new builds added: {total_inserted}")
        print(f"Total existing builds updated: {total_updated}")
        print(f"Total rows in smogon_builds: {total_rows}")
        print(f"Total skipped pokemon entries: {total_skipped}")
        print(f"Failed format files: {len(failed_formats)}")
        if failed_formats:
            print("Failed list: " + ", ".join(failed_formats))

    finally:
        db.close()


if __name__ == "__main__":
    main()
