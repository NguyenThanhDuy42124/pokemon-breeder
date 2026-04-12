"""
main.py – FastAPI application entry point.

=== ALL API ENDPOINTS ===

  GET  /                              Health check
  GET  /api/pokemon/search?q=pika     Autocomplete search
  GET  /api/pokemon/{id}              Full Pokémon details
  GET  /api/pokemon/{id}/compatible   Compatible breeding partners
  POST /api/breeding/calculate        Breeding probability calculator
  GET  /api/natures                   All 25 natures
  GET  /api/egg-groups                All 15 egg groups

=== HOW TO RUN ===
  cd backend
  uvicorn main:app --reload

Then open http://localhost:8000/docs to see & test all APIs!
"""

from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from contextlib import asynccontextmanager
import os
import logging
import json
import threading
import datetime
import subprocess
from database import SessionLocal
from models import Pokemon, EggGroup, Nature, Ability, SmogonBuild, pokemon_ability
from schemas import (
    PokemonSchema,
    PokemonSearchResult,
    NatureSchema,
    EggGroupSchema,
    AbilitySchema,
    BreedingRequest,
    BreedingResponse,
    FormInfo,
    SmogonBuildSchema,
    PlannerRequest,
    PlannerResponse,
    PlannerStepSchema,
)
from breeding import calculate_breeding
from auto_update import check_and_update
from planner import generate_roadmap
from runtime_sync import run_runtime_sync

# ── Server state tracking ──────────────────────────────────
SERVER_STARTED_AT = datetime.datetime.utcnow().isoformat()
SERVER_VERSION = "1.0.0"
LAST_UPDATE_CHECK = None
LAST_GIT_PULL = None

# Auto-update interval: every 10 minutes (600 seconds)
AUTO_UPDATE_INTERVAL = int(os.environ.get("AUTO_UPDATE_INTERVAL", 600))

# Configure logging with timestamp
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, datefmt=LOG_DATEFMT)

# Apply same format to uvicorn loggers so access logs show timestamps
for _uv_logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
    _uv_logger = logging.getLogger(_uv_logger_name)
    for _handler in _uv_logger.handlers:
        _handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATEFMT))
    if not _uv_logger.handlers:
        _h = logging.StreamHandler()
        _h.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATEFMT))
        _uv_logger.addHandler(_h)


# ── Lifespan: runs auto-update on startup + periodic scheduler ──────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run auto-update check on startup and schedule periodic updates."""
    global LAST_UPDATE_CHECK, LAST_GIT_PULL
    stop_event = threading.Event()

    def run_initial_update():
        global LAST_UPDATE_CHECK
        try:
            ensure_db_columns()
            check_and_update()
            ensure_performance_indexes()
            sync_result = run_runtime_sync(reason="startup")
            logging.getLogger("auto_update").info(f"runtime sync (startup): {sync_result}")
            LAST_UPDATE_CHECK = datetime.datetime.utcnow().isoformat()
        except Exception as e:
            logging.getLogger("auto_update").error(f"Startup update failed: {e}")

    def periodic_update_loop():
        """Periodically pull from git and run auto-update."""
        global LAST_UPDATE_CHECK, LAST_GIT_PULL
        logger = logging.getLogger("auto_update")
        while not stop_event.is_set():
            stop_event.wait(AUTO_UPDATE_INTERVAL)
            if stop_event.is_set():
                break
            try:
                logger.info("=== Periodic Update: Pulling latest code... ===")
                git_result = git_pull()
                LAST_GIT_PULL = datetime.datetime.utcnow().isoformat()
                if git_result:
                    logger.info(f"Git pull result: {git_result}")
                # Re-check DB for new Pokemon
                ensure_db_columns()
                check_and_update()
                ensure_performance_indexes()

                # Run full runtime sync only when pull fetched new commits.
                pull_changed = bool(git_result) and ("already up to date" not in git_result.lower())
                if pull_changed:
                    sync_result = run_runtime_sync(reason="post-pull")
                    logger.info(f"runtime sync (post-pull): {sync_result}")

                LAST_UPDATE_CHECK = datetime.datetime.utcnow().isoformat()
                logger.info(f"=== Periodic Update Complete at {LAST_UPDATE_CHECK} ===")
            except Exception as e:
                logger.error(f"Periodic update failed: {e}")

    # Run initial update in background
    thread = threading.Thread(target=run_initial_update, daemon=True)
    thread.start()

    # Start periodic update loop
    periodic_thread = threading.Thread(target=periodic_update_loop, daemon=True)
    periodic_thread.start()

    yield

    # Signal the periodic loop to stop
    stop_event.set()


def git_pull():
    """Run 'git pull' in the project root. Returns output string or None."""
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run(
            ["git", "pull"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = (result.stdout or "").strip()
        if result.returncode != 0:
            err = (result.stderr or "").strip()
            logging.getLogger("auto_update").warning(f"git pull error: {err}")
            return f"ERROR: {err}"
        return output
    except Exception as e:
        logging.getLogger("auto_update").warning(f"git pull exception: {e}")
        return None


def ensure_db_columns():
    """Ensure new columns exist in the DB (safe ALTER TABLE for SQLite)."""
    import sqlite3
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pokemon_breeding.db")
    if not os.path.exists(db_path):
        return
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("PRAGMA table_info(pokemon)")
        existing = {row[1] for row in cursor.fetchall()}
        new_cols = [
            ("form_name", "VARCHAR(50)"),
            ("base_species_id", "INTEGER"),
            ("is_baby", "BOOLEAN DEFAULT 0"),
            ("is_legendary", "BOOLEAN DEFAULT 0"),
            ("is_mythical", "BOOLEAN DEFAULT 0"),
        ]
        for col_name, col_type in new_cols:
            if col_name not in existing:
                conn.execute(f"ALTER TABLE pokemon ADD COLUMN {col_name} {col_type}")
                logging.getLogger("auto_update").info(f"Added missing column: {col_name}")
        conn.commit()
        conn.close()
    except Exception as e:
        logging.getLogger("auto_update").warning(f"ensure_db_columns error: {e}")


def ensure_performance_indexes():
    """Create SQLite indexes needed for low-latency planner/build lookups."""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pokemon_breeding.db")
    if not os.path.exists(db_path):
        return
    try:
        import sqlite3

        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = {row[0] for row in cursor.fetchall()}

        index_plan = {
            "smogon_builds": [
                "CREATE INDEX IF NOT EXISTS idx_smogon_pokemon_id ON smogon_builds (pokemon_id)",
                "CREATE INDEX IF NOT EXISTS idx_smogon_generation ON smogon_builds (generation)",
                "CREATE INDEX IF NOT EXISTS idx_smogon_format ON smogon_builds (format)",
                "CREATE INDEX IF NOT EXISTS idx_smogon_format_name ON smogon_builds (format_name)",
                "CREATE INDEX IF NOT EXISTS idx_smogon_pokemon_slug ON smogon_builds (pokemon_slug)",
            ],
            "move": [
                "CREATE INDEX IF NOT EXISTS idx_move_slug ON move (normalized_name)",
            ],
            "pokemon_moves": [
                "CREATE INDEX IF NOT EXISTS idx_pm_lookup ON pokemon_moves (pokemon_id, move_id, is_egg_move)",
            ],
            "pokemon_move_learn": [
                "CREATE INDEX IF NOT EXISTS idx_pml_lookup ON pokemon_move_learn (pokemon_id, move_id, learn_method, generation)",
            ],
        }

        for table_name, statements in index_plan.items():
            if table_name not in existing_tables:
                continue
            for sql in statements:
                conn.execute(sql)
        conn.commit()
        conn.close()
    except Exception as e:
        logging.getLogger("auto_update").warning(f"ensure_performance_indexes error: {e}")


# ── Create the FastAPI app ──────────────────────────────────
app = FastAPI(
    title="Pokémon Breeding Calculator API",
    description="Gen 9 breeding mechanics calculator",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS Middleware ─────────────────────────────────────────
# Allows the React frontend to talk to this backend (dev + production).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # allow all origins for deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global Exception Handler ───────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unexpected errors and return a clean JSON response."""
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
    )


# ── Database Dependency ─────────────────────────────────────
# FastAPI calls this automatically whenever an endpoint needs `db`.
def get_db():
    db = SessionLocal()
    try:
        yield db         # give the session to the endpoint
    finally:
        db.close()       # always close when done


# ════════════════════════════════════════════════════════════
# API 0: HEALTH CHECK
# ════════════════════════════════════════════════════════════

@app.get("/api/health", tags=["Health"])
def root():
    """Quick check that the server is running."""
    return {"status": "ok", "message": "Pokémon Breeding Calculator API"}


@app.get("/api/server/status", tags=["Health"])
def server_status():
    """
    Server status endpoint. Frontend polls this to detect restarts.
    Returns startup time, last update check, and last git pull time.
    """
    return {
        "started_at": SERVER_STARTED_AT,
        "version": SERVER_VERSION,
        "last_update_check": LAST_UPDATE_CHECK,
        "last_git_pull": LAST_GIT_PULL,
        "update_interval_seconds": AUTO_UPDATE_INTERVAL,
    }


# ════════════════════════════════════════════════════════════
# API 1: POKEMON AUTOCOMPLETE SEARCH
# ════════════════════════════════════════════════════════════

@app.get(
    "/api/pokemon/search",
    response_model=list[PokemonSearchResult],
    tags=["Pokemon"],
)
def search_pokemon(
    q: str = Query(..., min_length=1, description="Search query (e.g. 'pika')"),
    limit: int = Query(10, ge=1, le=50, description="Max results"),
    db: Session = Depends(get_db),
):
    """
    Search Pokémon by name prefix.

    HOW IT WORKS:
    - The frontend calls this as the user types in the search box.
    - Returns lightweight results (id, name, sprite) for a dropdown.
    - Matches anywhere in the name: "char" → charmander, charmeleon, charizard.

    EXAMPLE:
      GET /api/pokemon/search?q=pika
      → [{"id": 25, "name": "pikachu", "sprite_url": "..."}]
    """
    results = (
        db.query(Pokemon)
        .filter(Pokemon.name.contains(q.lower()))
        .order_by(Pokemon.id)
        .limit(limit)
        .all()
    )
    return results


# ── Region ID ranges for browse filtering ───────────────────
REGION_RANGES = {
    "kanto": (1, 151),
    "johto": (152, 251),
    "hoenn": (252, 386),
    "sinnoh": (387, 493),
    "unova": (494, 649),
    "kalos": (650, 721),
    "alola": (722, 809),
    "galar": (810, 905),
    "paldea": (906, 1025),
}


# ════════════════════════════════════════════════════════════
# API 1b: BROWSE / FILTER POKEMON (advanced search panel)
# ════════════════════════════════════════════════════════════

@app.get("/api/pokemon/browse", tags=["Pokemon"])
def browse_pokemon(
    name: str = Query(None, description="Filter by name substring"),
    egg_group_id: int = Query(None, description="Filter by a single egg group ID"),
    egg_group_ids: str = Query(None, description="Comma-separated egg group IDs (for compatibility lock)"),
    region: str = Query(None, description="Region name (kanto, johto, hoenn, ...)"),
    limit: int = Query(50, ge=1, le=200, description="Max results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
):
    """
    Browse all Pokémon with advanced filters.
    Used by the frontend browse panel and instant search dropdown.

    Filters can be combined:
      GET /api/pokemon/browse?name=char&region=kanto&egg_group_id=1&limit=20

    Returns { total, pokemon: [...] }
    """
    query = db.query(Pokemon)

    if name and name.strip():
        query = query.filter(Pokemon.name.contains(name.lower().strip()))

    if egg_group_id:
        query = query.filter(Pokemon.egg_groups.any(EggGroup.id == egg_group_id))

    if egg_group_ids:
        ids = [int(x) for x in egg_group_ids.split(",") if x.strip().isdigit()]
        if ids:
            # Include Pokémon in these egg groups OR Ditto (breeds with anything)
            query = query.filter(
                or_(
                    Pokemon.egg_groups.any(EggGroup.id.in_(ids)),
                    Pokemon.is_ditto.is_(True),
                )
            )

    if region and region.lower() in REGION_RANGES:
        start, end = REGION_RANGES[region.lower()]
        query = query.filter(Pokemon.id >= start, Pokemon.id <= end)

    total = query.count()
    results = query.order_by(Pokemon.id).offset(offset).limit(limit).all()

    return {
        "total": total,
        "pokemon": [
            {
                "id": p.id,
                "name": p.name,
                "sprite_url": p.sprite_url,
                "is_breedable": p.is_breedable,
                "is_baby": p.is_baby,
                "is_legendary": p.is_legendary,
                "is_mythical": p.is_mythical,
            }
            for p in results
        ],
    }


@app.get(
    "/api/pokemon/{pokemon_id}/smogon-builds",
    response_model=list[SmogonBuildSchema],
    tags=["Pokemon"],
)
def get_smogon_builds(
    pokemon_id: int,
    generation: str = Query(None, description="Filter by generation, ex: gen9"),
    format_name: str = Query(None, description="Filter by format name, ex: ou, monotype"),
    format_id: str = Query(None, description="Optional exact format id, ex: gen9ou"),
    db: Session = Depends(get_db),
):
    """
    Returns cached Smogon build templates for the selected Pokemon.
    Data is fully local (SQLite) after seeding, no runtime Smogon request.
    """
    builds_query = db.query(SmogonBuild).filter(SmogonBuild.pokemon_id == pokemon_id)
    if format_id:
        builds_query = builds_query.filter(SmogonBuild.format == format_id)

    if generation:
        builds_query = builds_query.filter(SmogonBuild.generation == generation)
    if format_name:
        builds_query = builds_query.filter(SmogonBuild.format_name == format_name)

    builds = builds_query.order_by(SmogonBuild.format.asc(), SmogonBuild.build_name.asc()).all()

    result = []
    for b in builds:
        parsed_generation = b.generation or "unknown"
        parsed_format_name = b.format_name or "unknown"

        try:
            moves = json.loads(b.moves_json or "[]")
        except Exception:
            moves = []
        try:
            target_ivs = json.loads(b.target_ivs_json or "[true, true, true, true, true, true]")
        except Exception:
            target_ivs = [True, True, True, True, True, True]

        result.append(
            SmogonBuildSchema(
                id=b.id,
                pokemon_id=b.pokemon_id,
                format=b.format,
                generation=parsed_generation,
                format_name=parsed_format_name,
                build_name=b.build_name,
                source_url=b.source_url,
                nature=b.nature,
                ability=b.ability,
                item=b.item,
                moves=moves,
                target_ivs=target_ivs,
                requires_hidden_ability=b.requires_hidden_ability,
            )
        )

    return result


@app.get(
    "/api/pokemon/{pokemon_id}/smogon-options",
    tags=["Pokemon"],
)
def get_smogon_build_options(
    pokemon_id: int,
    generation: str = Query(None, description="Optional generation filter, ex: gen9"),
    db: Session = Depends(get_db),
):
    """
    Returns available generations and formats for this Pokemon.
    Used by frontend to lazy-load build options before requesting full build rows.
    """
    base_query = db.query(SmogonBuild).filter(SmogonBuild.pokemon_id == pokemon_id)
    all_rows = base_query.all()
    generations = sorted({(row.generation or "unknown") for row in all_rows})

    format_query = base_query
    if generation:
        format_query = format_query.filter(SmogonBuild.generation == generation)
    format_rows = format_query.all()
    formats = sorted({(row.format_name or "unknown") for row in format_rows})

    return {"generations": generations, "formats": formats}


# ════════════════════════════════════════════════════════════
# API 2: GET POKEMON DETAILS
# ════════════════════════════════════════════════════════════

@app.get(
    "/api/pokemon/{pokemon_id}/forms",
    response_model=list[FormInfo],
    tags=["Pokemon"],
)
def get_pokemon_forms(pokemon_id: int, db: Session = Depends(get_db)):
    """
    Get available regional forms for a base Pokemon.
    Returns the base form + any regional variants (Alolan, Galarian, etc.)
    Only returns forms if regional variants actually exist.
    """
    # Check if this pokemon IS a regional form → use its base_species_id
    pokemon = db.query(Pokemon).filter(Pokemon.id == pokemon_id).first()
    if not pokemon:
        return []

    base_id = pokemon.base_species_id or pokemon_id

    # Find all regional forms of this base species
    forms = (
        db.query(Pokemon)
        .filter(Pokemon.base_species_id == base_id)
        .order_by(Pokemon.id)
        .all()
    )

    if not forms:
        return []  # No regional forms exist

    # Include the base form first
    base = db.query(Pokemon).filter(Pokemon.id == base_id).first()
    result = []
    if base:
        result.append(FormInfo(id=base.id, name=base.name, form_name=None, sprite_url=base.sprite_url))

    for f in forms:
        result.append(FormInfo(id=f.id, name=f.name, form_name=f.form_name, sprite_url=f.sprite_url))

    return result


@app.get(
    "/api/pokemon/{pokemon_id}",
    response_model=PokemonSchema,
    tags=["Pokemon"],
)
def get_pokemon(pokemon_id: int, db: Session = Depends(get_db)):
    """
    Get full details for one Pokémon: stats, abilities, egg groups.

    HOW IT WORKS:
    - Called when the user selects a Pokémon from the autocomplete.
    - Returns everything the UI needs to display the parent card.
    - Uses `joinedload` to fetch abilities and egg_groups in ONE query
      (instead of making 3 separate queries — much faster).

    EXAMPLE:
      GET /api/pokemon/25
      → {"id": 25, "name": "pikachu", "hp": 35, "attack": 55, ...
         "abilities": [{"id": 9, "name": "static"}, ...],
         "egg_groups": [{"id": 5, "name": "ground"}, {"id": 6, "name": "fairy"}]}
    """
    pokemon = (
        db.query(Pokemon)
        .options(joinedload(Pokemon.egg_groups))
        .filter(Pokemon.id == pokemon_id)
        .first()
    )

    if not pokemon:
        raise HTTPException(status_code=404, detail="Pokémon not found")

    # Query abilities WITH is_hidden from the association table
    ability_rows = (
        db.query(Ability.id, Ability.name, pokemon_ability.c.is_hidden)
        .join(pokemon_ability, Ability.id == pokemon_ability.c.ability_id)
        .filter(pokemon_ability.c.pokemon_id == pokemon_id)
        .all()
    )

    # Build response manually to include is_hidden
    result = PokemonSchema.model_validate(pokemon)
    result.abilities = [
        AbilitySchema(id=a.id, name=a.name, is_hidden=a.is_hidden)
        for a in ability_rows
    ]
    return result


# ════════════════════════════════════════════════════════════
# API 3: COMPATIBLE BREEDING PARTNERS
# ════════════════════════════════════════════════════════════

@app.get(
    "/api/pokemon/{pokemon_id}/compatible",
    response_model=list[PokemonSearchResult],
    tags=["Breeding"],
)
def get_compatible_parents(pokemon_id: int, db: Session = Depends(get_db)):
    """
    Given a Pokémon, return all valid breeding partners.

    BREEDING RULES (Gen 9):
    1. Two Pokémon can breed if they share at least one Egg Group.
    2. Ditto can breed with ANY breedable Pokémon (except another Ditto).
    3. Pokémon in the "Undiscovered" egg group CANNOT breed at all.
    4. Two Ditto CANNOT breed together.

    EXAMPLE:
      GET /api/pokemon/25/compatible
      → [{"id": 26, "name": "raichu"}, {"id": 35, "name": "clefairy"}, ...,
         {"id": 132, "name": "ditto"}]
    """
    parent = (
        db.query(Pokemon)
        .options(joinedload(Pokemon.egg_groups))
        .filter(Pokemon.id == pokemon_id)
        .first()
    )

    if not parent:
        raise HTTPException(status_code=404, detail="Pokémon not found")

    if not parent.is_breedable:
        raise HTTPException(
            status_code=400,
            detail=f"{parent.name} is in the Undiscovered egg group and cannot breed.",
        )

    # --- If selected Pokémon IS Ditto ---
    # Ditto can breed with anything breedable EXCEPT another Ditto
    if parent.is_ditto:
        compatible = (
            db.query(Pokemon)
            .filter(Pokemon.is_breedable.is_(True), Pokemon.is_ditto.is_(False))
            .order_by(Pokemon.id)
            .all()
        )
        return compatible

    # --- Normal case: find Pokémon with shared Egg Groups ---
    egg_group_ids = [eg.id for eg in parent.egg_groups]

    compatible = (
        db.query(Pokemon)
        .filter(
            Pokemon.egg_groups.any(EggGroup.id.in_(egg_group_ids)),
            Pokemon.id != pokemon_id,        # exclude self
            Pokemon.is_breedable.is_(True),     # must be breedable
        )
        .order_by(Pokemon.id)
        .all()
    )

    # Always include Ditto as an option
    ditto = db.query(Pokemon).filter(Pokemon.is_ditto.is_(True)).first()
    if ditto and ditto not in compatible:
        compatible.append(ditto)

    return compatible


# ════════════════════════════════════════════════════════════
# API 4: BREEDING PROBABILITY CALCULATOR
# ════════════════════════════════════════════════════════════

@app.post(
    "/api/breeding/calculate",
    response_model=BreedingResponse,
    tags=["Breeding"],
)
def breeding_calculate(req: BreedingRequest, db: Session = Depends(get_db)):
    """
    Calculate the probability of getting offspring with perfect IVs.

    HOW THE FRONTEND USES THIS:
    1. User selects Parent A and Parent B.
    2. User marks which IVs are perfect (31) for each parent.
    3. User selects held items (Destiny Knot, Power Items, etc.).
    4. User clicks "Calculate".
    5. This API returns a table of probabilities.

    EXAMPLE REQUEST:
      POST /api/breeding/calculate
      {
        "parent_a_id": 25,
        "parent_b_id": 132,
        "parent_a_ivs": [true, true, true, true, true, false],
        "parent_b_ivs": [true, true, true, true, false, false],
        "held_item_a": "destiny_knot",
        "held_item_b": "none"
      }

    EXAMPLE RESPONSE:
      {
        "parent_a": "pikachu",
        "parent_b": "ditto",
        "held_item_a": "destiny_knot",
        "held_item_b": "none",
        "inherited_count": 5,
        "results": [
          {"perfect_iv_count": 3, "probability": 0.123, "percentage": "12.30%", ...},
          {"perfect_iv_count": 4, "probability": 0.456, "percentage": "45.60%", ...},
          ...
        ]
      }
    """
    # ── Validate IV lists ──
    if len(req.parent_a_ivs) != 6 or len(req.parent_b_ivs) != 6:
        raise HTTPException(
            status_code=400,
            detail="parent_a_ivs and parent_b_ivs must each have exactly 6 booleans.",
        )

    # ── Fetch parents from DB ──
    parent_a = db.query(Pokemon).filter(Pokemon.id == req.parent_a_id).first()
    parent_b = db.query(Pokemon).filter(Pokemon.id == req.parent_b_id).first()

    if not parent_a:
        raise HTTPException(status_code=404, detail="Parent A not found")
    if not parent_b:
        raise HTTPException(status_code=404, detail="Parent B not found")

    # ── Validate breeding compatibility ──
    if not parent_a.is_breedable:
        raise HTTPException(status_code=400, detail=f"{parent_a.name} cannot breed.")
    if not parent_b.is_breedable:
        raise HTTPException(status_code=400, detail=f"{parent_b.name} cannot breed.")

    a_is_ditto = parent_a.is_ditto
    b_is_ditto = parent_b.is_ditto

    if a_is_ditto and b_is_ditto:
        raise HTTPException(status_code=400, detail="Two Ditto cannot breed together.")

    if not a_is_ditto and not b_is_ditto:
        a_groups = {eg.id for eg in parent_a.egg_groups}
        b_groups = {eg.id for eg in parent_b.egg_groups}
        if not a_groups & b_groups:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"{parent_a.name} and {parent_b.name} share no egg groups "
                    f"and cannot breed together."
                ),
            )

    # ── Delegate to breeding logic ──
    result = calculate_breeding(
        parent_a_name=parent_a.name,
        parent_b_name=parent_b.name,
        parent_a_ivs=req.parent_a_ivs,
        parent_b_ivs=req.parent_b_ivs,
        held_item_a=req.held_item_a,
        held_item_b=req.held_item_b,
        # Nature / Ability / Ditto info (Phase 4)
        parent_a_nature=req.parent_a_nature,
        parent_b_nature=req.parent_b_nature,
        parent_a_ability=req.parent_a_ability,
        parent_b_ability=req.parent_b_ability,
        parent_a_ability_hidden=req.parent_a_ability_hidden,
        parent_b_ability_hidden=req.parent_b_ability_hidden,
        breeding_with_ditto=req.breeding_with_ditto,
        target_ivs=req.target_ivs,
        lang=req.lang,
    )

    # ── Determine offspring species ──
    # Rule: offspring is the non-Ditto parent's species.
    # In normal ♂×♀ breeding, offspring is the female's species.
    if a_is_ditto:
        offspring = parent_b
    elif b_is_ditto:
        offspring = parent_a
    else:
        # Normal breeding: female parent determines species.
        # Use user-selected gender if provided, else guess by gender_rate.
        a_gender = req.parent_a_gender  # "male", "female", or None
        b_gender = req.parent_b_gender
        if a_gender == "female":
            offspring = parent_a
        elif b_gender == "female":
            offspring = parent_b
        elif a_gender == "male":
            offspring = parent_b
        elif b_gender == "male":
            offspring = parent_a
        else:
            # Fallback: higher gender_rate = more likely female
            if parent_a.gender_rate >= parent_b.gender_rate:
                offspring = parent_a
            else:
                offspring = parent_b

    result.offspring_name = offspring.name
    result.offspring_id = offspring.id
    result.offspring_sprite_url = offspring.sprite_url

    return result


@app.post(
    "/api/planner/roadmap",
    response_model=PlannerResponse,
    tags=["Breeding"],
)
def planner_roadmap(req: PlannerRequest, db: Session = Depends(get_db)):
    """
    Rule-based breeding roadmap generator.
    No AI inference; deterministic if/else logic + cached helpers.
    """
    steps = generate_roadmap(
        db=db,
        pokemon_id=req.pokemon_id,
        parent_a_id=req.parent_a_id,
        parent_b_id=req.parent_b_id,
        parent_a_ivs=req.parent_a_ivs,
        parent_b_ivs=req.parent_b_ivs,
        target_nature=req.target_nature,
        target_ability=req.target_ability,
        target_ivs=req.target_ivs,
        target_moves=req.target_moves,
        requires_hidden_ability=req.requires_hidden_ability,
        generation=req.generation,
        lang=req.lang,
    )
    return PlannerResponse(steps=[PlannerStepSchema(**s) for s in steps])


# ════════════════════════════════════════════════════════════
# API 5: LIST ALL NATURES
# ════════════════════════════════════════════════════════════

@app.get(
    "/api/natures",
    response_model=list[NatureSchema],
    tags=["Reference Data"],
)
def list_natures(db: Session = Depends(get_db)):
    """
    Return all 25 Pokémon natures.
    Useful for the frontend dropdown (Everstone passes nature to offspring).
    """
    return db.query(Nature).order_by(Nature.id).all()


# ════════════════════════════════════════════════════════════
# API 6: LIST ALL EGG GROUPS
# ════════════════════════════════════════════════════════════

@app.get(
    "/api/egg-groups",
    response_model=list[EggGroupSchema],
    tags=["Reference Data"],
)
def list_egg_groups(db: Session = Depends(get_db)):
    """
    Return all 15 egg groups.
    Useful for understanding breeding compatibility.
    """
    return db.query(EggGroup).order_by(EggGroup.id).all()


# ════════════════════════════════════════════════════════════
# SERVE REACT FRONTEND (Production)
# ════════════════════════════════════════════════════════════

# If the React build folder exists, serve it as static files.
# This allows deploying frontend + backend as a SINGLE app.
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "build")

if os.path.isdir(STATIC_DIR):
    # Serve static assets (JS, CSS, images) at /static
    app.mount("/static", StaticFiles(directory=os.path.join(STATIC_DIR, "static")), name="static-assets")

    # Serve React index.html for all non-API routes (SPA fallback)
    from fastapi.responses import FileResponse

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_react(full_path: str):
        """Serve React app for any non-API route."""
        file_path = os.path.join(STATIC_DIR, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
