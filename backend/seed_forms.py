"""
seed_forms.py – Fetch regional form Pokemon from PokeAPI.

Regional forms (Alolan, Galarian, Hisuian, Paldean) are stored in PokeAPI
as separate Pokemon entries with IDs > 10000. They share the same species
(egg groups, gender rate) as their base form but have different abilities,
stats, and sprites.

Usage:
  cd backend
  python seed_forms.py

This script:
1. For each base Pokemon (1–1025), checks if it has regional variants
2. If yes, fetches the variant data and saves it with form_name + base_species_id
3. Is RESUMABLE — skips already-saved forms
"""

import time
import requests
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import SessionLocal, engine
from models import (
    Pokemon, Ability,
    pokemon_egg_group, pokemon_ability,
    Base,
)


POKEAPI = "https://pokeapi.co/api/v2"

# Regional form keywords to detect
REGIONAL_KEYWORDS = ["alola", "galar", "hisui", "paldea"]

http_session = requests.Session()


def fetch_json(url, retries=3):
    for attempt in range(retries):
        try:
            resp = http_session.get(url, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            if attempt == retries - 1:
                print(f"    FAILED: {url} — {e}")
                return None
            time.sleep(2 ** attempt)


# Map PokeAPI stat names → our DB column names
STAT_MAP = {
    "hp": "hp",
    "attack": "attack",
    "defense": "defense",
    "special-attack": "sp_attack",
    "special-defense": "sp_defense",
    "speed": "speed",
}


def ensure_columns_exist():
    """Add form_name and base_species_id columns if they don't exist yet."""
    with engine.connect() as conn:
        # Check existing columns
        result = conn.execute(text("PRAGMA table_info(pokemon)"))
        columns = {row[1] for row in result.fetchall()}

        if "form_name" not in columns:
            conn.execute(text("ALTER TABLE pokemon ADD COLUMN form_name VARCHAR(50)"))
            print("  Added column: form_name")

        if "base_species_id" not in columns:
            conn.execute(text("ALTER TABLE pokemon ADD COLUMN base_species_id INTEGER"))
            print("  Added column: base_species_id")

        conn.commit()


def detect_regional_form(variety_name, species_name):
    """
    Given a variety name like 'vulpix-alola', detect the regional keyword.
    Returns the region string or None.
    """
    suffix = variety_name.replace(species_name + "-", "")
    for region in REGIONAL_KEYWORDS:
        if region in suffix:
            return region
    return None


def main():
    ensure_columns_exist()

    db = SessionLocal()

    # Build ability lookup
    ability_map = {a.name: a for a in db.query(Ability).all()}

    # Find which Pokemon IDs already exist (for resume)
    existing_ids = {row[0] for row in db.query(Pokemon.id).all()}

    print("\n" + "=" * 55)
    print("  Regional Form Seeder")
    print("=" * 55)
    print(f"  Scanning 1025 base species for regional variants...")
    print(f"  Already in DB: {len(existing_ids)} entries\n")

    added = 0
    scanned = 0
    start_time = time.time()

    for base_id in range(1, 1026):
        scanned += 1
        if scanned % 100 == 0:
            elapsed = time.time() - start_time
            print(f"  ... scanned {scanned}/1025 species, added {added} forms ({int(elapsed)}s)")

        # Fetch species data (has the varieties list)
        species = fetch_json(f"{POKEAPI}/pokemon-species/{base_id}")
        if not species:
            continue

        varieties = species.get("varieties", [])
        if len(varieties) <= 1:
            continue  # Only base form, no variants

        species_name = species["name"]

        for variety in varieties:
            if variety.get("is_default", True):
                continue  # Skip the default/base form

            poke_url = variety["pokemon"]["url"]
            # Extract the PokeAPI Pokemon ID from the URL
            form_id = int(poke_url.rstrip("/").split("/")[-1])

            if form_id in existing_ids:
                continue  # Already seeded

            variety_name = variety["pokemon"]["name"]
            region = detect_regional_form(variety_name, species_name)
            if not region:
                continue  # Not a regional form (could be mega, gmax, etc.)

            # Fetch the full Pokemon data for this form
            poke_data = fetch_json(poke_url)
            if not poke_data:
                continue

            # Parse stats
            stats = {}
            for stat_entry in poke_data.get("stats", []):
                api_stat_name = stat_entry["stat"]["name"]
                db_col = STAT_MAP.get(api_stat_name)
                if db_col:
                    stats[db_col] = stat_entry["base_stat"]

            # Parse sprite
            sprites = poke_data.get("sprites", {})
            sprite_url = sprites.get("front_default")

            # Gender rate — same as base species
            api_gender = species.get("gender_rate", 4)
            gender_rate = -1.0 if api_gender == -1 else api_gender * 12.5

            # Egg groups — same as base species
            egg_group_names = [eg["name"] for eg in species.get("egg_groups", [])]
            is_breedable = "no-eggs" not in egg_group_names

            # Display name: "vulpix-alola" → show as-is
            display_name = variety_name

            pokemon = Pokemon(
                id=form_id,
                name=display_name,
                sprite_url=sprite_url,
                form_name=region,
                base_species_id=base_id,
                hp=stats.get("hp", 0),
                attack=stats.get("attack", 0),
                defense=stats.get("defense", 0),
                sp_attack=stats.get("sp_attack", 0),
                sp_defense=stats.get("sp_defense", 0),
                speed=stats.get("speed", 0),
                gender_rate=gender_rate,
                is_breedable=is_breedable,
                is_ditto=False,
            )
            db.add(pokemon)
            db.flush()

            # Link egg groups (same as base)
            from models import EggGroup
            egg_group_map = {eg.name: eg for eg in db.query(EggGroup).all()}
            for eg_name in egg_group_names:
                if eg_name in egg_group_map:
                    db.execute(
                        pokemon_egg_group.insert().values(
                            pokemon_id=form_id,
                            egg_group_id=egg_group_map[eg_name].id,
                        )
                    )

            # Process abilities (may differ from base!)
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
                        pokemon_id=form_id,
                        ability_id=ability_map[ab_name].id,
                        is_hidden=is_hidden,
                    )
                )

            added += 1
            existing_ids.add(form_id)
            print(f"  + #{form_id} {display_name} ({region}) — base: #{base_id} {species_name}")

            if added % 5 == 0:
                db.commit()

    db.commit()

    elapsed_total = time.time() - start_time
    print(f"\n  DONE!")
    print(f"  Regional forms added: {added}")
    print(f"  Time: {int(elapsed_total)}s")
    print(f"  Total Pokemon in DB: {db.query(Pokemon).count()}")

    db.close()


if __name__ == "__main__":
    main()
