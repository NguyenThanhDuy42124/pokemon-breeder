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
import threading
from database import SessionLocal
from models import Pokemon, EggGroup, Nature, Ability, pokemon_ability
from schemas import (
    PokemonSchema,
    PokemonSearchResult,
    NatureSchema,
    EggGroupSchema,
    AbilitySchema,
    BreedingRequest,
    BreedingResponse,
)
from breeding import calculate_breeding
from auto_update import check_and_update

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


# ── Lifespan: runs auto-update on startup ──────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run auto-update check in background on startup."""
    def run_update():
        try:
            check_and_update()
        except Exception as e:
            logging.getLogger("auto_update").error(f"Startup update failed: {e}")

    # Run in background thread so server starts immediately
    thread = threading.Thread(target=run_update, daemon=True)
    thread.start()
    yield


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
    query = db.query(Pokemon).filter(Pokemon.is_breedable == True)

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
                    Pokemon.is_ditto == True,
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
            {"id": p.id, "name": p.name, "sprite_url": p.sprite_url}
            for p in results
        ],
    }


# ════════════════════════════════════════════════════════════
# API 2: GET POKEMON DETAILS
# ════════════════════════════════════════════════════════════

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
            .filter(Pokemon.is_breedable == True, Pokemon.is_ditto == False)
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
            Pokemon.is_breedable == True,     # must be breedable
        )
        .order_by(Pokemon.id)
        .all()
    )

    # Always include Ditto as an option
    ditto = db.query(Pokemon).filter(Pokemon.is_ditto == True).first()
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

    return result


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
