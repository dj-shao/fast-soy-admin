# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FastSoyAdmin is a full-stack admin template with a **FastAPI** backend (Python) and **Vue3** frontend (TypeScript). The repo is a monorepo: backend lives at root (`/app`), frontend in `/web` (pnpm workspaces).

## Common Commands

### Backend

```bash
# Install dependencies (uses uv or pdm)
uv sync                        # or: pdm install
# Run dev server (port 9999)
python run.py
# Lint & format
ruff check app/                # lint
ruff format app/               # format
# Type check
pyright app/
# Tests
pytest tests/ -v
```

### Migrations (manual — no auto-migration on startup)

The app does **not** create or migrate tables on startup. Run these commands yourself when models change:

```bash
tortoise makemigrations        # generate migration files for schema changes
tortoise migrate               # apply pending migrations
```

On a fresh clone, run `tortoise makemigrations && tortoise migrate` before `python run.py`, otherwise Tortoise will error when querying non-existent tables.

### Frontend

```bash
cd web
pnpm install                  # install dependencies
pnpm dev                      # dev server (port 9527)
pnpm build                    # production build
pnpm lint                     # eslint
pnpm typecheck                # vue-tsc type check
```

### Docker

```bash
docker compose up -d          # full stack: nginx(:1880) + fastapi + redis
```

## Architecture

### Backend (`/app`)

Layered, modular architecture. The backend is split into two top-level packages:

- `app/system/` — built-in system module (auth, RBAC, users, roles, menus, APIs, routes)
- `app/business/` — user-land business modules, auto-discovered on startup

Each module has the same internal layout: `api/` → `controllers/` → `services/` → `models` + `schemas`.

#### Layers

- **api/** — FastAPI routers, thin HTTP adapters. Accept request, call service/controller, return `Success`/`Fail`.
- **controllers/** — Subclass `CRUDBase` from `app.core.crud`. Single-resource CRUD + `build_search`. No cross-resource orchestration, no side effects beyond the single table.
- **services/** — Multi-model orchestration, caching, Redis writes, transactions, audit logging. This is where anything non-trivial lives.
- **models** — Tortoise ORM models inheriting `app.core.base_model.BaseModel` (adds audit fields).
- **schemas** — Pydantic v2, all inherit `app.core.base_schema.SchemaBase` which provides automatic `snake_case ↔ camelCase` aliasing.

#### Key files

- `app/__init__.py` — App factory, middleware registration, lifespan hooks
- `app/core/`:
  - `init_app.py` — Middleware list, exception handlers, router mounting, DB registration
  - `base_schema.py` — `SchemaBase`, `PageQueryBase`, `Success`/`Fail`/`SuccessExtra`, `CommonIds`, `OfflineByRoleRequest`
  - `base_model.py` — ORM base with `created_at`/`updated_at`/`created_by`/`updated_by`
  - `crud.py` — `CRUDBase` generic + `get_db_conn(model)` helper for transactions
  - `router.py` — `CRUDRouter` factory for standard CRUD routes with override hooks
  - `dependency.py` — `DependAuth` (JWT auth) and `DependPermission` (RBAC) as FastAPI dependencies
  - `autodiscover.py` — Scans `app/business/*` for models, routers, and init data
  - `middlewares.py` — Request ID, background tasks, pretty errors
  - `ctx.py` — Context variables (`CTX_USER_ID`, `CTX_ROLE_CODES`, `CTX_BUTTON_CODES`, ...)
  - `config.py` — Pydantic Settings loaded from `.env`; Tortoise ORM config lives here
- `app/utils/__init__.py` — Public import surface for business modules (`from app.utils import CRUDBase, CRUDRouter, Success, Fail, SchemaBase, DependPermission, get_db_conn, ...`). Business code should import from here, not reach into `app.core.*`.
- `app/system/`:
  - `api/` — `auth`, `users`, `roles`, `menus`, `apis`, `route`, `health` routers
  - `controllers/` — `user`, `role`, `menu`, `api`
  - `services/` — `auth` (token invalidation, impersonation, login), `user` (user creation), `captcha`, `monitor`, `init_helper`
  - `models/admin.py` — User, Role, Menu, Api, Button
  - `schemas/` — `users.py`, `admin.py`, `login.py`
  - `security.py` — Password hashing (argon2), JWT create
  - `radar/` — fastapi-radar integration (request/query capture, dashboard)

### Frontend (`/web`)

Vue3 + Vite + Naive UI + Elegant Router + Pinia

- `web/src/views/` — Page components
- `web/src/service/api/` — API service calls (one file per backend module)
- `web/src/store/` — Pinia stores
- `web/src/router/` — Elegant Router config (generates routes from file structure)
- `web/src/locales/` — i18n translations
- `web/src/typings/api/` — TS interface definitions matching backend schemas
- `web/packages/` — Internal monorepo packages (alova, axios, hooks, utils, color, uno-preset)

### Database

- Default: SQLite (`app_system.sqlite3`)
- ORM: Tortoise ORM (a vendored copy lives at `/tortoise-orm/` — used via uv/pdm local dep)
- Migrations: Tortoise built-in, run manually (see "Migrations" above)
- Caching: Redis via fastapi-cache2

## Business Modules (autodiscover)

Business modules live in `app/business/<module_name>/`. On startup, `app/core/autodiscover.py` scans for any subdirectory with an `__init__.py` and tries to load:

| Convention | What it provides |
|---|---|
| `app/business/<name>/models.py` or `models/` | Tortoise models → registered via `TORTOISE_ORM["apps"]` |
| `app/business/<name>/api/` or `api.py` | Must export `router: APIRouter` → mounted at `/api/v1/business/` |
| `app/business/<name>/init_data.py` | Optional `async def init()` → runs after system init, before cache refresh |

**Module layout convention** (copy from `app/business/hr/`):

```
app/business/<name>/
├── __init__.py
├── config.py          # BIZ_SETTINGS, per-module pydantic settings
├── ctx.py             # Per-module context vars (if needed)
├── dependency.py      # Per-module FastAPI dependencies
├── models.py          # Tortoise models
├── schemas.py         # Pydantic schemas (inherit SchemaBase)
├── controllers.py     # CRUDBase subclasses (single-resource)
├── services.py        # Multi-model orchestration
├── init_data.py       # async def init() → creates default rows, menus, permissions
└── api/
    ├── __init__.py    # must export `router` aggregating sub-routers
    ├── manage.py
    └── my.py
```

Directories under `app/business/` that start with `_` are skipped. Do not import business module internals from `app.system.*` — only the other way around.

### Startup init & reconciliation

On every startup, the Redis leader worker runs: `init_menus()` → `refresh_api_list()` → `init_users()` → each business `init_data.init()` → `refresh_all_cache()`.

**Sync semantics by data type:**
- **APIs** — `refresh_api_list()` does a full reconcile against FastAPI routes (adds new, deletes stale, updates metadata). Nothing to do manually.
- **Menus / Buttons** — `ensure_menu()` is upsert-only. To also clean up *removed* entries, call `reconcile_menu_subtree(root_route=..., declared_route_names=..., declared_button_codes=...)` at the end of the module's `_init_menu_data()`. This scopes deletion strictly to the BFS subtree under `root_route`, so it never touches sibling modules. See [app/business/hr/init_data.py](app/business/hr/init_data.py) for the pattern.
- **Roles** — `ensure_role()` upserts the role row and does clear-and-readd on `menus`/`buttons`/`apis` grants. **Removing** a role from the seed list does NOT delete the `Role` row — that needs a migration.
- **Business seed data** — `_safe_update_or_create` by unique key. Removal requires a migration.

**Drift warnings:** `ensure_role` now logs a warning when a declared `route_name` / `button_code` / `(method, path)` can't be resolved — always fix these, they indicate a seed list that's out of sync with renamed/deleted code.

**Enabling `reconcile_menu_subtree` means the subtree becomes Infrastructure-as-Code**: menus/buttons created manually via the Web UI under that subtree will be wiped on the next restart. If you need dynamic user-created menus, don't call `reconcile_menu_subtree` on that subtree.

Full details: [fast-soy-admin-docs/src/backend/init-data.md](fast-soy-admin-docs/src/backend/init-data.md).

## API Conventions

All system and business HTTP APIs follow the same conventions. These are enforced; deviations should be discussed before merging.

### Response format

Every successful response is `{"code": "0000", "msg": "OK", "data": {...}}`. Use `Success` / `SuccessExtra` / `Fail` from `app.core.base_schema`. Never return naked dicts or snake_case keys — the `SchemaBase` alias generator produces camelCase output automatically via `model_dump(by_alias=True)`.

### Path & method conventions

| Operation | Method + Path | Body / Params |
|---|---|---|
| List/search | `POST /resources/search` | Body: `XxxSearch` (extends `PageQueryBase`) |
| Get one | `GET /resources/{id}` | — |
| Create | `POST /resources` | Body: `XxxCreate` |
| Update | `PATCH /resources/{id}` | Body: `XxxUpdate` |
| Delete one | `DELETE /resources/{id}` | — |
| Delete many | `DELETE /resources` | Body: `{ids: [...]}` (use `CommonIds`) |
| Sub-resource get | `GET /resources/{id}/sub` | — |
| Sub-resource update | `PATCH /resources/{id}/sub` | Body |
| Derived query | `GET /resources/tree`, `GET /resources/pages` | — |
| Instance action | `POST /resources/{id}/action-name` | — or Body |
| Collection action | `POST /resources/batch-offline`, `POST /resources/refresh` | Body |

**No trailing slashes.** Use kebab-case for multi-word paths (`batch-offline`, `constant-routes`). Resource names are plural.

### Request/response field naming

- Request bodies and query params are **camelCase** (the alias form). Pydantic accepts both thanks to `validate_by_name=True`, but the frontend always sends camelCase.
- Response `data` is **camelCase**. Use `schema.model_dump(by_alias=True)` or `model.to_dict()` (which already does this). Never hand-build snake_case response dicts.
- Pagination fields: `current` / `size` (default `current=1, size=10`).

### CRUDRouter

`app/core/router.py` exposes `CRUDRouter` — a factory that wires the 6 standard routes. Use `override=` hooks (not hand-rolled duplicates) when a route needs custom logic:

```python
from app.core.router import CRUDRouter, SearchFieldConfig

crud = CRUDRouter(
    prefix="/roles",
    controller=role_controller,
    create_schema=RoleCreate,
    update_schema=RoleUpdate,
    list_schema=RoleSearch,
    search_fields=SearchFieldConfig(contains_fields=["role_name", "role_code"]),
    summary_prefix="角色",
)

@crud.override("create")
async def custom_create(role_in: RoleCreate, request: Request):
    ...
    return Success(...)

router = crud.router
```

## Gate Checks

After modifying code, run the corresponding checks before finishing:

### Backend

```bash
ruff check app/               # lint
ruff format app/              # format
pyright app                   # type check (strict mode)
pytest tests/ -v              # tests
```

### Frontend

```bash
cd web
pnpm lint                     # eslint
pnpm typecheck                # vue-tsc type check
```

## Configuration

- `.env` — SECRET_KEY, APP_DEBUG, CORS, Redis URL, DB path
- `ruff.toml` — Line length 200, rules E/F/I, double quotes
- Pyright strict mode on `app/` directory

## Deployment

Nginx serves the built frontend and proxies `/api/*` to the FastAPI backend (port 9999). Redis provides caching. All orchestrated via `docker-compose.yml` with configs in `/deploy/`.
