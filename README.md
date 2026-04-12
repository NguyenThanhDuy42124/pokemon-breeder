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

## Runtime Auto-Sync After Pull

Backend da duoc setup de tu dong chay cac buoc sync khi server startup va khi `git pull` co commit moi:

- Auto update Pokemon core data (`auto_update.py`)
- Auto seed Smogon builds (SQLite cache)
- Auto seed move-learning/egg-move data

Cau hinh bang bien moi truong:

- `AUTO_RUNTIME_SYNC=1` bat/tat orchestration tong
- `AUTO_SMOGON_SYNC=1` bat/tat Smogon seed
- `AUTO_SMOGON_FROM_INDEX=0` neu =1 se quet tat ca format trong index
- `AUTO_SMOGON_PRESET=core|expanded|genX-core|genX-expanded` preset format theo gen
- `AUTO_SMOGON_GENERATION=1..9` gen mac dinh khi format duoc nhap dang alias (`ou,uu,bh,vgc`...)
- `AUTO_SMOGON_FORMATS=ou,uu,ru,nu,ubers,lc,...` danh sach format seed khi khong dung from-index/preset
- `AUTO_MOVE_SYNC=1` bat/tat move-learning seed
- `AUTO_MOVE_SYNC_ALL=1` neu =1 se quet toan bo Pokemon cho move-learning
- `AUTO_MOVE_SYNC_LIMIT=1025` limit khi `AUTO_MOVE_SYNC_ALL=0`
- `AUTO_RUNTIME_SYNC_TIMEOUT_SEC=1800` timeout cho moi script seed

Preset Smogon hien co:

- `core`: nhom format pho bien cho gen duoc chon boi `--generation`
- `expanded`: bo mo rong cho gen duoc chon boi `--generation`
- `genX-core`, `genX-expanded`: preset co dinh cho mot gen cu the (vd: `gen6-core`)
- `stage1` (index-driven): `ou` + tat ca `vgc*` cua Gen1..Gen9
- `stage2` (index-driven): `stage1` + `uu/ru/nu` cho Gen8-Gen9
- `stage3` (index-driven): `stage2` + toan bo `gen9nationaldex*`

Mac dinh runtime hien tai:

- Neu khong set gi them, server se tu dong dung `AUTO_SMOGON_PRESET=stage1` de seed theo index (an toan hon cho host yeu).

Quy uoc format Smogon:

- Mau ten chuan: `gen[the_he][ten_format][phien_ban neu co]`
- Vi du: `gen9ou`, `gen8vgc2022`, `gen7randombattle`, `gen6vgc2016`
- De lay day du danh sach song Gen1-Gen9: `--from-index` (doc tu `index.json`)

Vi du seed nhanh:

- `python backend/seed_smogon_builds.py --generation 9 --preset core`
- `python backend/seed_smogon_builds.py --preset gen8-core`
- `python backend/seed_smogon_builds.py --preset gen7-expanded`
- `python backend/seed_smogon_builds.py --formats "ou,uu,ru,nu,1v1,doubles,ag,bh,vgc"`
- `python backend/seed_smogon_builds.py --preset stage1`
- `python backend/seed_smogon_builds.py --preset stage2`
- `python backend/seed_smogon_builds.py --preset stage3`
- `python backend/seed_smogon_builds.py --from-index`  # nap full theo danh sach song index.json

Chien luoc host 1GB RAM:

- Giai doan 1: `--from-index` KHONG dung; seed `ou` + `vgc` cho cac gen can tra cuu
- Giai doan 2: bo sung `uu,ru,nu` cho Gen 8-9
- Giai doan 3: bo sung National Dex / OM lon neu can

Luu y cho host yeu (1 vCPU, 1GB RAM):

- Nen bat dau voi `AUTO_SMOGON_FROM_INDEX=0` va chi seed mot so format can dung.
- Sau khi seed day du 1 lan, he thong se nho commit da sync va bo qua lan chay lai neu code khong doi.

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
