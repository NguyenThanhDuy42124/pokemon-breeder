# Ghi Chep He Thong Hien Tai (Pokemon Breeder)

Tai lieu nay mo ta trang thai hien tai cua du an theo tung file/chuc nang de de bao tri, debug va mo rong.

## 1) Tong quan kien truc

- Backend: FastAPI + SQLAlchemy + SQLite (`backend/`)
- Frontend: React CRA (`frontend/src/`), build static o `frontend/build/`
- DB local: `backend/pokemon_breeding.db`
- Deploy 1 process: Uvicorn phuc vu ca API va static frontend

## 2) Root files

- `app.py`: Entry point cho PikaMC/Pterodactyl, force sync GitHub bang `git fetch` + `git reset --hard origin/master`, sau do chay Uvicorn trong `backend`.
- `start.py`: Entry point thay the, cai `backend/requirements.txt` truoc khi chay Uvicorn.
- `Procfile`: Lenh deploy cho Railway/Render/Heroku (`web: cd backend && uvicorn main:app ...`).
- `README.md`: Huong dan setup/chay local/deploy tong quan.
- `requirements.txt`: Dependencies cap root (tuong thich host).
- `.gitignore`: Loai tru file tam/cache/env.

## 3) Backend (`backend/`)

### Core
- `backend/main.py`: API chinh + CORS + static serving + scheduler cap nhat dinh ky.
  - `/api/health`: health check.
  - `/api/server/status`: tra ve `started_at`, `last_update_check`, `last_git_pull`, interval.
  - `/api/pokemon/search`: autocomplete.
  - `/api/pokemon/browse`: browse/filter theo ten, egg-group, region, pagination.
  - `/api/pokemon/{id}/forms`: lay danh sach regional forms.
  - `/api/pokemon/{id}`: chi tiet Pokemon (stats/ability/egg groups + flags).
  - `/api/pokemon/{id}/compatible`: doi tac breed hop le.
  - `/api/breeding/calculate`: tinh xac suat IV/nature/ability + du doan offspring.
  - `/api/natures`, `/api/egg-groups`: du lieu tham chieu.
  - Lifespan: startup update + periodic git pull + DB check.
- `backend/models.py`: SQLAlchemy models.
  - `Pokemon`: stats, gender_rate, is_breedable, is_ditto, regional fields (`form_name`, `base_species_id`), flags (`is_baby`, `is_legendary`, `is_mythical`).
  - `EggGroup`, `Ability`, `Nature`.
  - Bang lien ket: `pokemon_egg_group`, `pokemon_ability`.
- `backend/schemas.py`: Pydantic schemas request/response.
  - `PokemonSchema`, `PokemonSearchResult`, `FormInfo`.
  - `BreedingRequest`, `BreedingResponse`, cac schema ket qua.
- `backend/database.py`: Cau hinh engine/session SQLite + bat foreign_keys.
- `backend/breeding.py`: Logic tinh toan breeding (Gen 9), xac suat exact bang combinatorics.

### Data update / seed
- `backend/seed.py`: Seed base species (Gen 1-9), natures, egg groups, abilities.
- `backend/seed_forms.py`: Seed regional forms (alola/galar/hisui/paldea), gan `base_species_id`.
- `backend/seed_flags.py`: Seed `is_baby/is_legendary/is_mythical` tu PokeAPI.
- `backend/auto_update.py`: Auto-check PokeAPI de bo sung Pokemon moi (an toan, idempotent).
- `backend/pokemon_breeding.db`: SQLite data hien tai (species + forms + quan he).

### Alembic
- `backend/alembic.ini`: Cau hinh Alembic.
- `backend/alembic/env.py`: Runtime migration context.
- `backend/alembic/script.py.mako`: Template migration.
- `backend/alembic/README`: Ghi chu Alembic.
- `backend/alembic/versions/89706d7555ba_initial_schema.py`: Migration khoi tao schema.

### Dependencies
- `backend/requirements.txt`: FastAPI, SQLAlchemy, Uvicorn, requests, v.v.

## 4) Frontend source (`frontend/src/`)

### App shell
- `frontend/src/index.js`: React root mount + wrappers.
- `frontend/src/App.js`: Main container, language/theme, parent states, server restart banner, trigger calculate.
- `frontend/src/App.css`: Theme + toan bo style components.
- `frontend/src/index.css`: CSS base.
- `frontend/src/i18n.js`: Dich EN/VI + context `useLanguage`.
- `frontend/src/api.js`: Service layer goi backend APIs.

### Components
- `frontend/src/components/PokemonSearch.js`: Search/autocomplete + browse trigger.
- `frontend/src/components/AdvancedSearchPanel.js`: Browse/filter + pagination + nhay trang bang input so.
- `frontend/src/components/ParentPanel.js`: Chon parent, region form, gender, warning unbreedable, IV/item/nature/ability.
- `frontend/src/components/ResultsPanel.js`: Hien ket qua xac suat va phan offspring prediction.
- `frontend/src/components/TipsPanel.js`: Panel huong dan/tips.

### Test/util
- `frontend/src/App.test.js`: Test mau CRA.
- `frontend/src/reportWebVitals.js`: Web-vitals helper.
- `frontend/src/setupTests.js`: Setup jest/testing-library.
- `frontend/src/logo.svg`: Tai nguyen CRA.

## 5) Frontend public (`frontend/public/`)

- `frontend/public/index.html`: HTML shell.
- `frontend/public/manifest.json`: PWA metadata.
- `frontend/public/robots.txt`: Robots config.
- `frontend/public/favicon.ico`, `logo192.png`, `logo512.png`: Assets icon.
- `frontend/public/images/`: Thu muc anh bo sung (hien dang rong hoac phu thuoc deploy).

## 6) Frontend build output (`frontend/build/`) - hien tai

- `frontend/build/index.html`: Ban da build de deploy.
- `frontend/build/asset-manifest.json`: Mapping file hash.
- `frontend/build/manifest.json`, `robots.txt`, `favicon.ico`, `logo192.png`, `logo512.png`.
- `frontend/build/static/css/main.a72cb3c6.css`
- `frontend/build/static/css/main.a72cb3c6.css.map`
- `frontend/build/static/js/main.76494682.js`
- `frontend/build/static/js/main.76494682.js.map`
- `frontend/build/static/js/main.76494682.js.LICENSE.txt`
- `frontend/build/static/js/453.20359781.chunk.js`
- `frontend/build/static/js/453.20359781.chunk.js.map`

Luu y: ten file hash trong `build/static/*` se thay doi moi lan `npm run build`.

## 7) Tinh nang hien tai dang co

- Tinh xac suat breeding IV (Gen 9), co target IV.
- Nature inheritance (Everstone), ability inheritance (hidden/non-hidden).
- Offspring prediction theo Ditto/gender logic.
- Regional forms selector (Alola/Galar/Hisui/Paldea) va reload stat/ability theo form.
- Hien Pokemon unbreedable (baby/legendary/mythical/undiscovered) + warning do.
- Browse panel co lock theo egg-group partner + pagination + nhap so trang de nhay nhanh.
- Auto-update startup + periodic update (git pull + DB checks).
- Frontend banner thong bao server restart/reconnect.

## 8) Van hanh nhanh

- Local backend:
  - `cd backend`
  - `python -m uvicorn main:app --reload --port 8000`
- Local frontend:
  - `cd frontend`
  - `npm start`
- Build frontend:
  - `cd frontend`
  - `npm run build`
- Seed bo sung:
  - `python backend/seed_forms.py`
  - `python backend/seed_flags.py`

## 9) Ghi chu bao tri

- DB SQLite can duoc backup truoc khi chay script seed lon.
- Tren host, can dam bao script startup chay dung file entry (`app.py` hoac `start.py`) theo moi truong.
- Neu cap nhat frontend, can build lai de dong bo `frontend/build/` cho deployment kieu static-included.
