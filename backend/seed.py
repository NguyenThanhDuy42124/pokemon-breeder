"""
seed.py – Fetch Pokemon data from PokeAPI and save to local SQLite.

=== WHAT THIS DOES ===
Fetches real Pokemon data from https://pokeapi.co and inserts it into
your local SQLite database so the app works offline.

Tables populated:
  - nature            (25 natures: Adamant, Jolly, etc.)
  - egg_group         (15 egg groups: Monster, Water 1, etc.)
  - ability           (abilities discovered from Pokemon data)
  - pokemon           (species with base stats, sprites, gender)
  - pokemon_egg_group (which Pokemon belong to which egg groups)
  - pokemon_ability   (which Pokemon have which abilities + hidden flag)

=== HOW TO RUN ===
  cd backend
  python seed.py                # Default: Gen 1 (151 Pokemon)  ~3 min
  python seed.py --gen 3        # Gen 1-3 (386 Pokemon)         ~8 min
  python seed.py --all          # All Gen 1-9 (1025 Pokemon)    ~15 min

The script is RESUMABLE: if you interrupt it (Ctrl+C), run it again
and it will skip Pokemon that were already saved.

=== WHAT IS PokeAPI? ===
PokeAPI is a free, open REST API containing all Pokemon data.
We call it ONCE to fill our local DB, then never need it again.
Docs: https://pokeapi.co/docs/v2
"""

import sys
import time
import requests
from sqlalchemy.orm import Session
from database import SessionLocal
from models import (
    Pokemon, EggGroup, Ability, Nature,
    pokemon_egg_group, pokemon_ability,
)


# ================================================================
# CONFIGURATION
# ================================================================

POKEAPI = "https://pokeapi.co/api/v2"

# National Dex number where each generation ends
GEN_LIMITS = {
    1: 151,    # Kanto       (Bulbasaur → Mew)
    2: 251,    # Johto       (Chikorita → Celebi)
    3: 386,    # Hoenn       (Treecko → Deoxys)
    4: 493,    # Sinnoh      (Turtwig → Arceus)
    5: 649,    # Unova       (Snivy → Genesect)
    6: 721,    # Kalos       (Chespin → Volcanion)
    7: 809,    # Alola       (Rowlet → Melmetal)
    8: 905,    # Galar/Hisui (Grookey → Enamorus)
    9: 1025,   # Paldea+DLC  (Sprigatito → Pecharunt)
}

# Map PokeAPI stat names → our database column names
STAT_MAP = {
    "hp": "hp",
    "attack": "attack",
    "defense": "defense",
    "special-attack": "sp_attack",
    "special-defense": "sp_defense",
    "speed": "speed",
}


# ================================================================
# HELPER: Fetch JSON with retry + backoff
# ================================================================

# Reuse one TCP session for all requests (much faster than opening
# a new connection for each call).
http_session = requests.Session()


def fetch_json(url, retries=3):
    """
    Fetch JSON from a URL.
    Retries up to 3 times with exponential backoff (1s, 2s, 4s).
    Returns None if all retries fail.
    """
    for attempt in range(retries):
        try:
            resp = http_session.get(url, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            if attempt == retries - 1:
                print(f"    FAILED: {url}")
                print(f"    Error: {e}")
                return None
            wait = 2 ** attempt
            time.sleep(wait)


# ================================================================
# STEP 1: Seed Natures (25 total)
# ================================================================

def seed_natures(db: Session):
    """
    Fetch all 25 Pokemon Natures from PokeAPI.

    WHAT ARE NATURES?
    Each Pokemon has a nature that gives +10% to one stat and -10% to another.
    Five natures are "neutral" (no stat change): Hardy, Docile, Serious, Bashful, Quirky.

    WHY DOES THIS MATTER FOR BREEDING?
    If a parent holds an Everstone, its nature is GUARANTEED to pass to the baby.
    """
    print("\n" + "=" * 50)
    print("  STEP 1: Seeding Natures")
    print("=" * 50)

    # Skip if already seeded (idempotent)
    existing = db.query(Nature).count()
    if existing > 0:
        print(f"  Already have {existing} natures. Skipping.")
        return

    # Fetch the list of all natures (PokeAPI paginates, so limit=50 covers all 25)
    data = fetch_json(f"{POKEAPI}/nature?limit=50")
    if not data:
        print("  ERROR: Could not fetch natures list!")
        return

    count = 0
    total = len(data["results"])

    for entry in data["results"]:
        # Each entry has {"name": "hardy", "url": "https://pokeapi.co/api/v2/nature/1/"}
        # We need the full details, so we fetch the URL
        nature_data = fetch_json(entry["url"])
        if not nature_data:
            continue

        # Extract which stat is boosted/lowered (None for neutral natures)
        increased = None
        decreased = None
        if nature_data.get("increased_stat"):
            increased = nature_data["increased_stat"]["name"]
        if nature_data.get("decreased_stat"):
            decreased = nature_data["decreased_stat"]["name"]

        nature = Nature(
            id=nature_data["id"],
            name=nature_data["name"],
            increased_stat=increased,
            decreased_stat=decreased,
        )
        db.add(nature)
        count += 1

        # Print progress
        if increased:
            print(f"  [{count:2d}/{total}] {nature.name:12s}  +{increased}, -{decreased}")
        else:
            print(f"  [{count:2d}/{total}] {nature.name:12s}  (neutral)")

    db.commit()
    print(f"\n  DONE: {count} natures saved.")


# ================================================================
# STEP 2: Seed Egg Groups (15 total)
# ================================================================

def seed_egg_groups(db: Session):
    """
    Fetch all 15 Egg Groups from PokeAPI.

    WHAT ARE EGG GROUPS?
    Egg Groups determine which Pokemon can breed together.
    Two Pokemon can breed if they share at least one Egg Group.

    SPECIAL EGG GROUPS:
    - "ditto"   → Only Ditto. Ditto can breed with ANY breedable Pokemon.
    - "no-eggs" → Undiscovered group. Pokemon here CANNOT breed.
                   (Legendaries, Mythicals, Baby Pokemon before evolving)
    """
    print("\n" + "=" * 50)
    print("  STEP 2: Seeding Egg Groups")
    print("=" * 50)

    existing = db.query(EggGroup).count()
    if existing > 0:
        print(f"  Already have {existing} egg groups. Skipping.")
        return

    data = fetch_json(f"{POKEAPI}/egg-group?limit=20")
    if not data:
        print("  ERROR: Could not fetch egg groups!")
        return

    count = 0
    for entry in data["results"]:
        eg_data = fetch_json(entry["url"])
        if not eg_data:
            continue

        egg_group = EggGroup(
            id=eg_data["id"],
            name=eg_data["name"],
        )
        db.add(egg_group)
        count += 1

        # Show how many Pokemon belong to this group
        member_count = len(eg_data.get("pokemon_species", []))
        print(f"  [{count:2d}] {egg_group.name:15s}  ({member_count} species)")

    db.commit()
    print(f"\n  DONE: {count} egg groups saved.")


# ================================================================
# STEP 3: Seed Pokemon + Abilities
# ================================================================

def seed_pokemon(db: Session, max_id: int):
    """
    Fetch Pokemon data from PokeAPI and populate:
      - pokemon table           (species + base stats + sprite)
      - ability table           (unique abilities discovered)
      - pokemon_egg_group       (M2M: which egg groups each Pokemon is in)
      - pokemon_ability         (M2M: which abilities + is_hidden flag)

    For EACH Pokemon, we make 2 API calls:
      1. /pokemon-species/{id}  → egg groups, gender rate, baby/legendary flags
      2. /pokemon/{id}          → base stats, abilities, sprite URL

    The script is RESUMABLE: already-saved Pokemon are skipped.
    Progress is committed every 10 Pokemon so you don't lose work.
    """
    print("\n" + "=" * 50)
    print(f"  STEP 3: Seeding Pokemon (1 to {max_id})")
    print("=" * 50)
    print(f"  This requires ~{max_id * 2} API calls. Please wait...\n")

    # Build lookup: egg_group name → EggGroup row
    egg_group_map = {eg.name: eg for eg in db.query(EggGroup).all()}

    # Track abilities already in DB: name → Ability row
    ability_map = {a.name: a for a in db.query(Ability).all()}

    # Find which Pokemon IDs are already saved (for resume support)
    existing_ids = {row[0] for row in db.query(Pokemon.id).all()}
    if existing_ids:
        print(f"  Resuming: {len(existing_ids)} already in DB.\n")

    start_time = time.time()
    added = 0
    skipped = 0
    failed = 0

    for pokemon_id in range(1, max_id + 1):
        # ── Skip if already in DB ──
        if pokemon_id in existing_ids:
            skipped += 1
            continue

        # ── Progress display ──
        elapsed = time.time() - start_time
        if added > 0:
            rate = elapsed / added            # seconds per pokemon
            remaining = (max_id - pokemon_id - skipped) * rate
            eta = f"~{int(remaining)}s left"
        else:
            eta = "calculating..."

        print(f"  [{pokemon_id:4d}/{max_id}] ", end="", flush=True)

        # ── API Call 1: Species data ──
        # This gives us: egg groups, gender rate, is_baby, is_legendary, is_mythical
        species = fetch_json(f"{POKEAPI}/pokemon-species/{pokemon_id}")
        if not species:
            print("SKIP (species API failed)")
            failed += 1
            continue

        # ── API Call 2: Pokemon data ──
        # This gives us: base stats, abilities, sprite
        poke_data = fetch_json(f"{POKEAPI}/pokemon/{pokemon_id}")
        if not poke_data:
            print("SKIP (pokemon API failed)")
            failed += 1
            continue

        # ── Parse gender rate ──
        # PokeAPI scale: -1 = genderless, 0 = always male, 8 = always female
        # Each unit = 12.5% chance of being female
        # Our DB:       -1.0 = genderless, 0.0 = male only, 100.0 = female only
        api_gender = species.get("gender_rate", 4)  # default: 50/50
        if api_gender == -1:
            gender_rate = -1.0       # genderless (e.g. Magnemite, Voltorb)
        else:
            gender_rate = api_gender * 12.5   # convert to percentage

        # ── Parse egg groups ──
        egg_group_names = [eg["name"] for eg in species.get("egg_groups", [])]

        # ── Determine breedability ──
        # "no-eggs" is PokeAPI's name for the "Undiscovered" egg group
        is_breedable = "no-eggs" not in egg_group_names

        # ── Ditto check ──
        is_ditto = (pokemon_id == 132)

        # ── Parse base stats ──
        stats = {}
        for stat_entry in poke_data.get("stats", []):
            api_stat_name = stat_entry["stat"]["name"]    # e.g. "special-attack"
            db_col_name = STAT_MAP.get(api_stat_name)     # e.g. "sp_attack"
            if db_col_name:
                stats[db_col_name] = stat_entry["base_stat"]

        # ── Parse sprite URL ──
        sprites = poke_data.get("sprites", {})
        sprite_url = sprites.get("front_default")

        # ── Create Pokemon row ──
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
        db.flush()  # assigns the ID so we can create associations

        # ── Link Pokemon ↔ Egg Groups ──
        for eg_name in egg_group_names:
            if eg_name in egg_group_map:
                db.execute(
                    pokemon_egg_group.insert().values(
                        pokemon_id=pokemon_id,
                        egg_group_id=egg_group_map[eg_name].id,
                    )
                )

        # ── Process Abilities ──
        for ab_entry in poke_data.get("abilities", []):
            ab_name = ab_entry["ability"]["name"]
            is_hidden = ab_entry.get("is_hidden", False)

            # Create ability row if first time seeing it
            if ab_name not in ability_map:
                # Extract ability ID from the URL
                ab_url = ab_entry["ability"]["url"]
                ab_id = int(ab_url.rstrip("/").split("/")[-1])

                ability_obj = Ability(id=ab_id, name=ab_name)
                db.add(ability_obj)
                db.flush()
                ability_map[ab_name] = ability_obj

            # Link Pokemon ↔ Ability (with is_hidden flag)
            db.execute(
                pokemon_ability.insert().values(
                    pokemon_id=pokemon_id,
                    ability_id=ability_map[ab_name].id,
                    is_hidden=is_hidden,
                )
            )

        added += 1

        # Commit every 10 Pokemon (saves progress in case of crash)
        if added % 10 == 0:
            db.commit()

        # Print name + ETA
        print(f"{species['name']:15s}  ({eta})")

    # Final commit
    db.commit()

    elapsed_total = time.time() - start_time
    print(f"\n  DONE!")
    print(f"  Added: {added} | Skipped (already in DB): {skipped} | Failed: {failed}")
    print(f"  Time: {int(elapsed_total)}s")
    print(f"  Unique abilities discovered: {len(ability_map)}")


# ================================================================
# MAIN
# ================================================================

def main():
    """
    Parse command-line arguments and run the seed process.

    Usage:
      python seed.py              # Gen 1 only (default, fast)
      python seed.py --gen 3      # Gen 1-3
      python seed.py --all        # All 9 generations
    """
    # ── Parse arguments ──
    max_gen = 1  # default

    if "--all" in sys.argv:
        max_gen = 9
    elif "--gen" in sys.argv:
        idx = sys.argv.index("--gen")
        if idx + 1 < len(sys.argv):
            try:
                max_gen = int(sys.argv[idx + 1])
            except ValueError:
                print("ERROR: --gen expects a number (1-9)")
                sys.exit(1)

    if max_gen not in GEN_LIMITS:
        print(f"ERROR: Gen {max_gen} is not valid. Use 1-9.")
        sys.exit(1)

    max_id = GEN_LIMITS[max_gen]

    # ── Banner ──
    print()
    print("=" * 55)
    print("  Pokemon Breeding Calculator - Data Seeder")
    print("=" * 55)
    print(f"  Target .... Gen 1-{max_gen} ({max_id} Pokemon)")
    print(f"  Database .. pokemon_breeding (MySQL)")
    print(f"  Source .... PokeAPI (https://pokeapi.co)")
    print(f"  Estimated . ~{max_id * 2} API calls")
    print("=" * 55)

    # ── Open database session ──
    db = SessionLocal()

    try:
        seed_natures(db)         # 25 natures
        seed_egg_groups(db)      # 15 egg groups
        seed_pokemon(db, max_id) # Pokemon + abilities + associations

        # ── Final Summary ──
        print("\n" + "=" * 55)
        print("  SEEDING COMPLETE!")
        print("=" * 55)
        print(f"  Natures ......... {db.query(Nature).count():>5}")
        print(f"  Egg Groups ...... {db.query(EggGroup).count():>5}")
        print(f"  Abilities ....... {db.query(Ability).count():>5}")
        print(f"  Pokemon ......... {db.query(Pokemon).count():>5}")
        print("=" * 55)
        print("  You can now start the API:  uvicorn main:app --reload")
        print("=" * 55)

    except KeyboardInterrupt:
        print("\n\n  Interrupted! Progress has been saved.")
        print("  Run this script again to resume where you left off.")
        db.commit()
    except Exception as e:
        print(f"\n  ERROR: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
