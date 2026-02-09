# Pokemon Breeding Calculator

A full-stack web app that calculates **exact probabilities** for Pokemon Gen 9 breeding outcomes — IVs, Natures, and Abilities — using combinatorics (no RNG/Monte Carlo).

## Tech Stack

| Layer    | Technology                         |
| -------- | ---------------------------------- |
| Backend  | Python 3.10 + FastAPI + SQLAlchemy |
| Database | MySQL 8                            |
| Frontend | React 19 (Create React App)        |
| Math     | Exact combinatorics / DP           |

## Features

- **IV Probability Calculator** — Destiny Knot, Power Items, or no items
- **Nature Inheritance** — Everstone logic (one parent, both, or none)
- **Ability Inheritance** — Gen 9 rules (HA/regular, Ditto breeding)
- **Pokemon Autocomplete Search** — search by name with sprite previews
- **Breeding Compatibility** — shared egg groups + Ditto support
- **Beginner-Friendly Explanations** — every result includes a human-readable breakdown

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- MySQL 8 running on `localhost:3306`

### 1. Database Setup

```sql
CREATE DATABASE IF NOT EXISTS pokemon_breeding
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. Backend

```bash
cd backend

# Create virtual environment
python -m venv ../venv
../venv/Scripts/activate   # Windows
# source ../venv/bin/activate  # Linux/Mac

# Install dependencies
pip install fastapi uvicorn sqlalchemy pymysql alembic pydantic requests

# Update database password in database.py and alembic.ini if needed
# Default: root:12345@localhost/pokemon_breeding

# Run migrations
alembic upgrade head

# Seed data (Gen 1 = 151 Pokemon)
python seed.py --gen 1
# Or all generations:
# python seed.py --all

# Start server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm start
```

Open http://localhost:3000 in your browser.

## API Endpoints

| Method | Path                          | Description                    |
| ------ | ----------------------------- | ------------------------------ |
| GET    | `/`                           | Health check                   |
| GET    | `/api/pokemon/search?q=char`  | Search Pokemon by name         |
| GET    | `/api/pokemon/{id}`           | Pokemon details (stats, abilities, egg groups) |
| GET    | `/api/pokemon/{id}/compatible`| Breeding-compatible partners   |
| POST   | `/api/breeding/calculate`     | Calculate IV/nature/ability probabilities |
| GET    | `/api/natures`                | List all 25 natures            |
| GET    | `/api/egg-groups`             | List all 15 egg groups         |

## How the Math Works

The calculator uses **exact combinatorics** rather than Monte Carlo simulation:

1. **Determine inherited count**: 3 (base), 5 (Destiny Knot), adjusted by Power Items
2. **Identify forced stats**: Power Items guarantee specific stat inheritance
3. **Enumerate combinations**: for each way to pick remaining inherited stats, calculate probability that all target IVs land 31
4. **Free stats**: non-inherited stats each have 1/32 chance of being 31
5. **Sum across all target counts** (0-6 perfect IVs) — probabilities always sum to exactly 100%

## Project Structure

```
pokemon-breeder/
  backend/
    main.py          # FastAPI app + all endpoints
    breeding.py      # Core probability engine
    models.py        # SQLAlchemy ORM models
    schemas.py       # Pydantic request/response models
    database.py      # DB connection config
    seed.py          # PokeAPI data fetcher
    alembic/         # Database migrations
  frontend/
    src/
      App.js         # Main layout + state
      api.js         # Backend API service
      components/
        PokemonSearch.js   # Autocomplete search
        ParentPanel.js     # Parent config (IVs, items, nature, ability)
        ResultsPanel.js    # Probability table + explanations
```

## License

Educational project. Pokemon data from [PokeAPI](https://pokeapi.co/).
