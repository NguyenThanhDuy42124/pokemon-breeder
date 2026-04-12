"""
Seed pokemon_moves (egg move data) from PokeAPI into local SQLite.

Usage:
  cd backend
  python seed_pokemon_moves.py --limit 200
  python seed_pokemon_moves.py --all
"""

import argparse
import time
import requests
from sqlalchemy import text

from database import SessionLocal, engine
from models import Base, Pokemon, Move, PokemonMove, PokemonMoveLearn
from slugify_utils import slugify


POKEAPI = "https://pokeapi.co/api/v2"


def ensure_move(db, move_name: str) -> Move:
    norm = slugify(move_name)
    mv = db.query(Move).filter(Move.normalized_name == norm).first()
    if mv:
        return mv
    mv = Move(name=move_name, normalized_name=norm)
    db.add(mv)
    db.flush()
    return mv


def has_egg_move_entry(db, pokemon_id: int, move_id: int) -> bool:
    row = (
        db.query(PokemonMove.id)
        .filter(
            PokemonMove.pokemon_id == pokemon_id,
            PokemonMove.move_id == move_id,
            PokemonMove.is_egg_move,
        )
        .first()
    )
    return row is not None


def has_move_learn_entry(db, pokemon_id: int, move_id: int, learn_method: str, generation: str) -> bool:
    row = (
        db.query(PokemonMoveLearn.id)
        .filter(
            PokemonMoveLearn.pokemon_id == pokemon_id,
            PokemonMoveLearn.move_id == move_id,
            PokemonMoveLearn.learn_method == learn_method,
            PokemonMoveLearn.generation == generation,
        )
        .first()
    )
    return row is not None


def normalize_generation(version_group_name: str) -> str:
    # Version group examples: scarlet-violet, sword-shield, x-y
    if not version_group_name:
        return "unknown"
    mapping = {
        "red-blue": "gen1",
        "yellow": "gen1",
        "gold-silver": "gen2",
        "crystal": "gen2",
        "ruby-sapphire": "gen3",
        "emerald": "gen3",
        "firered-leafgreen": "gen3",
        "diamond-pearl": "gen4",
        "platinum": "gen4",
        "heartgold-soulsilver": "gen4",
        "black-white": "gen5",
        "black-2-white-2": "gen5",
        "x-y": "gen6",
        "omega-ruby-alpha-sapphire": "gen6",
        "sun-moon": "gen7",
        "ultra-sun-ultra-moon": "gen7",
        "lets-go-pikachu-lets-go-eevee": "gen7",
        "sword-shield": "gen8",
        "brilliant-diamond-and-shining-pearl": "gen8",
        "legends-arceus": "gen8",
        "scarlet-violet": "gen9",
    }
    return mapping.get(version_group_name, "unknown")


def ensure_indexes(db):
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_pm_pokemon_move ON pokemon_moves (pokemon_id, move_id)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_pm_is_egg ON pokemon_moves (is_egg_move)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_pml_pokemon ON pokemon_move_learn (pokemon_id)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_pml_move ON pokemon_move_learn (move_id)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_pml_method_gen ON pokemon_move_learn (learn_method, generation)"))
    db.commit()


def fetch_json(url: str, retries: int = 3):
    for attempt in range(retries):
        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException:
            if attempt == retries - 1:
                return None
            time.sleep(2 ** attempt)
    return None


def main():
    parser = argparse.ArgumentParser(description="Seed move learning data into pokemon_moves and pokemon_move_learn")
    parser.add_argument("--limit", type=int, default=200, help="Number of base species IDs to scan (default: 200)")
    parser.add_argument("--all", action="store_true", help="Scan all base species currently in DB")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        ensure_indexes(db)

        if args.all:
            species_ids = [row[0] for row in db.query(Pokemon.id).filter(Pokemon.id <= 1025).order_by(Pokemon.id).all()]
        else:
            species_ids = [row[0] for row in db.query(Pokemon.id).filter(Pokemon.id <= 1025).order_by(Pokemon.id).limit(args.limit).all()]

        total = len(species_ids)
        added_egg = 0
        added_learn = 0
        scanned = 0
        seen_learn_keys = set()

        for idx, pokemon_id in enumerate(species_ids, 1):
            scanned += 1
            data = fetch_json(f"{POKEAPI}/pokemon/{pokemon_id}")
            if not data:
                continue

            for move_entry in data.get("moves", []):
                move_name = move_entry.get("move", {}).get("name")
                if not move_name:
                    continue

                move = ensure_move(db, move_name)

                is_egg = False
                for vd in move_entry.get("version_group_details", []):
                    method = vd.get("move_learn_method", {}).get("name")
                    version_group = vd.get("version_group", {}).get("name")
                    generation = normalize_generation(version_group)
                    key = (pokemon_id, move.id, method, generation)

                    if method and key not in seen_learn_keys and not has_move_learn_entry(db, pokemon_id, move.id, method, generation):
                        db.add(
                            PokemonMoveLearn(
                                pokemon_id=pokemon_id,
                                move_id=move.id,
                                learn_method=method,
                                generation=generation,
                            )
                        )
                        seen_learn_keys.add(key)
                        added_learn += 1

                    if method == "egg":
                        is_egg = True

                if not is_egg:
                    continue
                if has_egg_move_entry(db, pokemon_id, move.id):
                    continue

                db.add(
                    PokemonMove(
                        pokemon_id=pokemon_id,
                        move_id=move.id,
                        is_egg_move=True,
                        source_pokemon_id=None,
                    )
                )
                added_egg += 1

            if idx % 25 == 0:
                db.commit()
                print(f"[{idx}/{total}] added egg rows: {added_egg}, learn rows: {added_learn}")

            # Keep API usage polite on weak hosts/network.
            time.sleep(0.05)

        db.commit()
        print(f"Done. scanned={scanned}, added_egg_move_rows={added_egg}, added_move_learn_rows={added_learn}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
