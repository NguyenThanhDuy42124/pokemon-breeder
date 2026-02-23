"""
seed_flags.py — Add is_baby / is_legendary / is_mythical flags from PokeAPI.

Usage:
    cd backend
    python seed_flags.py

This script:
1. Adds columns if missing (ALTER TABLE).
2. Fetches each species from PokeAPI (only 1-1025, forms inherit from base).
3. Updates the flags in the DB for both the base species and any linked forms.
"""

import sqlite3
import requests
import time
import sys

DB_PATH = "pokemon_breeding.db"
API = "https://pokeapi.co/api/v2/pokemon-species"

def ensure_columns(conn):
    """Add columns if they don't exist yet."""
    cursor = conn.execute("PRAGMA table_info(pokemon)")
    existing = {row[1] for row in cursor.fetchall()}
    for col in ("is_baby", "is_legendary", "is_mythical"):
        if col not in existing:
            conn.execute(f"ALTER TABLE pokemon ADD COLUMN {col} BOOLEAN DEFAULT 0")
            print(f"  Added column: {col}")
    conn.commit()


def main():
    conn = sqlite3.connect(DB_PATH)
    ensure_columns(conn)

    # Get all base species IDs (1-1025)
    rows = conn.execute(
        "SELECT id FROM pokemon WHERE id <= 1025 ORDER BY id"
    ).fetchall()
    total = len(rows)
    print(f"Updating flags for {total} base species...\n")

    updated = 0
    for idx, (pid,) in enumerate(rows, 1):
        try:
            resp = requests.get(f"{API}/{pid}", timeout=15)
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            data = resp.json()

            is_baby = 1 if data.get("is_baby", False) else 0
            is_legendary = 1 if data.get("is_legendary", False) else 0
            is_mythical = 1 if data.get("is_mythical", False) else 0

            # Update base species
            conn.execute(
                "UPDATE pokemon SET is_baby=?, is_legendary=?, is_mythical=? WHERE id=?",
                (is_baby, is_legendary, is_mythical, pid),
            )

            # Also update any regional forms linked to this base
            conn.execute(
                "UPDATE pokemon SET is_baby=?, is_legendary=?, is_mythical=? WHERE base_species_id=?",
                (is_baby, is_legendary, is_mythical, pid),
            )

            if is_baby or is_legendary or is_mythical:
                tag = []
                if is_baby:
                    tag.append("baby")
                if is_legendary:
                    tag.append("legendary")
                if is_mythical:
                    tag.append("mythical")
                print(f"  [{idx}/{total}] #{pid} → {', '.join(tag)}")
                updated += 1

            if idx % 50 == 0:
                conn.commit()
                print(f"  ... {idx}/{total} done")

            # Rate limit: ~100 requests/min to be polite
            time.sleep(0.3)

        except Exception as e:
            print(f"  [{idx}/{total}] #{pid} ERROR: {e}")
            time.sleep(1)

    conn.commit()
    conn.close()
    print(f"\nDone! Updated {updated} species with special flags.")


if __name__ == "__main__":
    main()
