"""
auto_update.py – Automatically check for new Pokemon and update the database.

=== HOW IT WORKS ===
1. On server startup, calls PokeAPI to get the total Pokemon species count.
2. Compares with the current count in our local SQLite database.
3. If PokeAPI has MORE Pokemon → fetches only the NEW ones.
4. Skips if no new Pokemon are found.
5. Also ensures natures & egg groups are complete (in case of first run).

This runs ONCE on every server startup. It's safe to run repeatedly —
already-existing Pokemon will never be touched or duplicated.

=== WHEN DOES NEW POKEMON APPEAR? ===
Game Freak releases ~80-150 new Pokemon per generation (every 3-4 years).
DLC adds ~100+ forms. PokeAPI updates within days of official release.
"""

import time
import logging
import requests
from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import (
    Base, Pokemon, EggGroup, Ability, Nature,
    pokemon_egg_group, pokemon_ability,
)

logger = logging.getLogger("auto_update")

POKEAPI = "https://pokeapi.co/api/v2"

# Reuse TCP session for speed
http = requests.Session()

# Map PokeAPI stat names → DB column names
STAT_MAP = {
    "hp": "hp",
    "attack": "attack",
    "defense": "defense",
    "special-attack": "sp_attack",
    "special-defense": "sp_defense",
    "speed": "speed",
}


def fetch_json(url, retries=3):
    """Fetch JSON with retry + backoff. Returns None on failure."""
    for attempt in range(retries):
        try:
            resp = http.get(url, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            if attempt == retries - 1:
                logger.warning(f"Failed to fetch {url}: {e}")
                return None
            time.sleep(2 ** attempt)


def get_pokeapi_total_count():
    """Ask PokeAPI how many Pokemon species exist in total."""
    data = fetch_json(f"{POKEAPI}/pokemon-species?limit=1")
    if data and "count" in data:
        return data["count"]
    return None


def ensure_natures(db: Session):
    """Seed natures if empty (first-run safety)."""
    if db.query(Nature).count() > 0:
        return
    logger.info("Seeding natures...")
    data = fetch_json(f"{POKEAPI}/nature?limit=50")
    if not data:
        return
    for entry in data["results"]:
        nd = fetch_json(entry["url"])
        if not nd:
            continue
        increased = nd["increased_stat"]["name"] if nd.get("increased_stat") else None
        decreased = nd["decreased_stat"]["name"] if nd.get("decreased_stat") else None
        db.add(Nature(id=nd["id"], name=nd["name"],
                      increased_stat=increased, decreased_stat=decreased))
    db.commit()
    logger.info(f"Seeded {db.query(Nature).count()} natures.")


def ensure_egg_groups(db: Session):
    """Seed egg groups if any are missing."""
    data = fetch_json(f"{POKEAPI}/egg-group?limit=30")
    if not data:
        return
    existing_ids = {r[0] for r in db.query(EggGroup.id).all()}
    added = 0
    for entry in data["results"]:
        egd = fetch_json(entry["url"])
        if not egd or egd["id"] in existing_ids:
            continue
        db.add(EggGroup(id=egd["id"], name=egd["name"]))
        added += 1
    if added:
        db.commit()
        logger.info(f"Added {added} new egg groups.")


def fetch_and_insert_pokemon(db: Session, pokemon_id: int, egg_group_map: dict, ability_map: dict):
    """Fetch one Pokemon from PokeAPI and insert into DB. Returns True on success."""
    species = fetch_json(f"{POKEAPI}/pokemon-species/{pokemon_id}")
    if not species:
        return False

    poke_data = fetch_json(f"{POKEAPI}/pokemon/{pokemon_id}")
    if not poke_data:
        return False

    # Gender rate
    api_gender = species.get("gender_rate", 4)
    gender_rate = -1.0 if api_gender == -1 else api_gender * 12.5

    # Egg groups
    egg_group_names = [eg["name"] for eg in species.get("egg_groups", [])]
    is_breedable = "no-eggs" not in egg_group_names
    is_ditto = (pokemon_id == 132)

    # Base stats
    stats = {}
    for stat_entry in poke_data.get("stats", []):
        col = STAT_MAP.get(stat_entry["stat"]["name"])
        if col:
            stats[col] = stat_entry["base_stat"]

    # Sprite
    sprite_url = poke_data.get("sprites", {}).get("front_default")

    # Create Pokemon
    pokemon = Pokemon(
        id=pokemon_id,
        name=species["name"],
        sprite_url=sprite_url,
        hp=stats.get("hp", 0),
        attack=stats.get("attack", 0),
        defense=stats.get("defense", 0),
        sp_attack=stats.get("sp_attack", 0),
        sp_defense=stats.get("sp_defense", 0),
        speed=stats.get("speed", 0),
        gender_rate=gender_rate,
        is_breedable=is_breedable,
        is_ditto=is_ditto,
    )
    db.add(pokemon)
    db.flush()

    # Link egg groups
    for eg_name in egg_group_names:
        if eg_name in egg_group_map:
            db.execute(
                pokemon_egg_group.insert().values(
                    pokemon_id=pokemon_id,
                    egg_group_id=egg_group_map[eg_name].id,
                )
            )

    # Link abilities
    for ab_entry in poke_data.get("abilities", []):
        ab_name = ab_entry["ability"]["name"]
        is_hidden = ab_entry.get("is_hidden", False)

        if ab_name not in ability_map:
            ab_url = ab_entry["ability"]["url"]
            ab_id = int(ab_url.rstrip("/").split("/")[-1])
            ability_obj = Ability(id=ab_id, name=ab_name)
            db.add(ability_obj)
            db.flush()
            ability_map[ab_name] = ability_obj

        db.execute(
            pokemon_ability.insert().values(
                pokemon_id=pokemon_id,
                ability_id=ability_map[ab_name].id,
                is_hidden=is_hidden,
            )
        )

    return True


def check_and_update():
    """
    Main auto-update function. Called once on server startup.
    
    - Checks PokeAPI for total Pokemon count
    - Compares with local DB
    - Fetches only new Pokemon if any exist
    - Safe, idempotent, no conflicts
    """
    logger.info("=== Auto-Update: Checking for new Pokemon... ===")

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Step 1: Ensure natures & egg groups
        ensure_natures(db)
        ensure_egg_groups(db)

        # Step 2: Check PokeAPI total
        api_total = get_pokeapi_total_count()
        if api_total is None:
            logger.warning("Could not reach PokeAPI. Skipping update.")
            return

        # Step 3: Check local DB
        local_count = db.query(Pokemon).count()
        local_max_id = db.query(Pokemon.id).order_by(Pokemon.id.desc()).first()
        local_max_id = local_max_id[0] if local_max_id else 0

        logger.info(f"PokeAPI total: {api_total} | Local DB: {local_count} (max ID: {local_max_id})")

        if api_total <= local_count:
            logger.info("Database is up to date! No new Pokemon.")
            return

        new_count = api_total - local_count
        logger.info(f"Found {new_count} new Pokemon! Fetching...")

        # Step 4: Get existing IDs to skip
        existing_ids = {r[0] for r in db.query(Pokemon.id).all()}
        egg_group_map = {eg.name: eg for eg in db.query(EggGroup).all()}
        ability_map = {a.name: a for a in db.query(Ability).all()}

        # Step 5: Fetch new Pokemon (from max_id+1 to api_total)
        # Also check gaps (IDs between 1 and max_id that might be missing)
        added = 0
        failed = 0
        check_up_to = max(local_max_id + new_count + 10, api_total + 10)

        for pid in range(1, check_up_to + 1):
            if pid in existing_ids:
                continue

            success = fetch_and_insert_pokemon(db, pid, egg_group_map, ability_map)
            if success:
                added += 1
                logger.info(f"  Added #{pid}")
                # Commit every 10
                if added % 10 == 0:
                    db.commit()
            else:
                failed += 1

            # Stop if we've found enough
            if added >= new_count + 5:
                break

        db.commit()

        logger.info(f"=== Auto-Update Complete: +{added} new Pokemon (failed: {failed}) ===")
        logger.info(f"Total Pokemon in DB: {db.query(Pokemon).count()}")

    except Exception as e:
        logger.error(f"Auto-update error: {e}")
        db.rollback()
    finally:
        db.close()
