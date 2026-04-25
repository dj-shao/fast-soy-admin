<!-- markdownlint-disable MD033 MD041 -->

<p align="center">
  <a href="https://github.com/sleep1223/"><img src="web/public/favicon.svg" width="180" height="180" alt="FastSoyAdmin"></a>
</p>

<div align="center">

# FastSoyAdmin

[![license](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![github stars](https://img.shields.io/github/stars/sleep1223/fast-soy-admin)](https://github.com/sleep1223/fast-soy-admin)
![python](https://img.shields.io/badge/python-3.12+-blue?logo=python&logoColor=edb641)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?logo=fastapi&logoColor=edb641)
![Pydantic](https://img.shields.io/badge/Pydantic_v2-e92063?logo=pydantic&logoColor=edb641)
![uv](https://img.shields.io/badge/uv-managed-blueviolet)
[![basedpyright](https://img.shields.io/badge/types-basedpyright-797952.svg?logo=python&logoColor=edb641)](https://github.com/DetachHead/basedpyright)
[![ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

<span>English | <a href="./README.md">中文</a></span>

**A batteries-included full-stack admin template: FastAPI + Vue3**

</div>

## Overview

FastSoyAdmin is a ready-to-use full-stack admin scaffold:

- **Backend** — FastAPI · Pydantic v2 · Tortoise ORM · Redis
- **Frontend** — Vue3 · Vite7 · TypeScript · Naive UI · UnoCSS · Pinia · Alova · Elegant Router
- **Infra** — Docker Compose (Nginx + FastAPI + Redis), multi-worker startup lock, fastapi-guard rate limiting, built-in Radar dashboard
- **Code generator** — `make cli-init` to scaffold, write `models.py`, `make cli-gen-all` to emit backend + frontend CRUD (i18n is auto-merged from `_generated/<module>/`; no manual edits to the language packs)

Great as a starting point for internal tools, and as a reference for modern full-stack development.

## Highlights

- **Complete RBAC** — three permission layers (menu / API / button) + row-level `data_scope` (all / department / self / custom)
- **Autodiscovered business modules** — drop a package in `app/business/<name>/`; routes, models, and init data register themselves. Modules are decoupled — cross-module communication uses the event bus.
- **CLI code generation** — turn Tortoise models into full backend + frontend CRUD in one command; generated i18n files merge in via `import.meta.glob` with TypeScript declaration merging keeping `$t` keys statically checked
- **Dynamic routing** — menu / API / button permissions are managed on the backend; routes are delivered per role after login
- **Unified responses** — every endpoint returns `{code, msg, data}` with HTTP status always 200; snake_case ↔ camelCase auto-conversion
- **Redis cache** — role permissions, constant routes, and token versions all cached; falls back to DB on outage
- **Strict typing** — vue-tsc on the frontend, basedpyright (standard) on the backend
- **i18n** — vue-i18n zh / en; CLI-emitted module i18n is consumed automatically and `$t` keys are typed via declaration merging
- **Production-ready** — built-in Radar request / SQL / exception tracing, fastapi-guard, Sqid resource IDs, state machine, event bus
- **One-command Docker** — Nginx + FastAPI + Redis out of the box

## Links

- [Live preview](https://fast-soy-admin.sleep0.de/)
- [Documentation](https://sleep1223.github.io/fast-soy-admin-docs/en/)
- [Quick start](https://sleep1223.github.io/fast-soy-admin-docs/en/guide/quick-start)
- [Development guide](https://sleep1223.github.io/fast-soy-admin-docs/en/backend/development)
- [Commands reference](https://sleep1223.github.io/fast-soy-admin-docs/en/backend/commands)
- [Apidog API docs](https://fast-soy-admin.apidog.io)

## Branches

| Branch | Purpose |
| --- | --- |
| `main` | Default branch, **includes examples** (`app/business/hr/` — a full reference module: employees / departments / tags) |
| `slim` | Clean template skeleton with no business example modules (coming soon — easier starting point for a fresh project) |

> `slim` is still in preparation. For now, if you want a clean start, simply delete `app/business/hr/` before launching — autodiscover will skip it.

## Getting Started

### Requirements

| Tool             | Version |
| ---------------- | ------- |
| Python           | >= 3.12 |
| Node.js          | >= 20   |
| uv · pnpm · make | latest  |

### Docker (recommended)

```bash
git clone https://github.com/sleep1223/fast-soy-admin.git
cd fast-soy-admin
make up                                                       # docker compose up -d
docker compose exec app uv run python -m app.cli initdb       # first-run: create tables + seed
docker compose restart app
```

Open `http://localhost:1880`.

> Migrations do **not** run automatically at startup. The container's SQLite file is **not** volume-mounted by default — for production, switch to an external DB or mount a volume for `app_system.sqlite3`. See the [deployment guide](https://sleep1223.github.io/fast-soy-admin-docs/en/backend/deployment).

### Local development

```bash
git clone https://github.com/sleep1223/fast-soy-admin.git
cd fast-soy-admin
make install-all     # uv sync + pnpm install
make initdb          # first-time: create tables + seed
make dev             # backend (:9999) + frontend (:9527) in parallel, Ctrl+C stops both
```

## Common Commands

All frequently used commands are wrapped in `Makefile`. Run `make help` for the full list.

| Command                                | Purpose                                               |
| -------------------------------------- | ----------------------------------------------------- |
| `make dev`                             | Run backend + frontend dev servers together           |
| `make check-all`                       | Run all backend + frontend quality gates (pre-commit) |
| `make mm`                              | `makemigrations` + `migrate`                          |
| `make cli-init MOD=xxx`                | Scaffold a new business module                        |
| `make cli-gen MOD=xxx`                 | Generate backend code from `models.py`                |
| `make cli-gen-web MOD=xxx CN=name`     | Generate frontend code from `models.py`               |
| `make cli-gen-all MOD=xxx CN=name`     | Generate both at once                                 |
| `make up` / `make down` / `make logs`  | Docker lifecycle                                      |

See the [commands reference](https://sleep1223.github.io/fast-soy-admin-docs/en/backend/commands) for the complete list.

## Adding a new business module

End-to-end example for an `inventory` module:

```bash
make cli-init MOD=inventory                       # 1. scaffold (models.py only)
$EDITOR app/business/inventory/models.py          # 2. define Tortoise models
make cli-gen-all MOD=inventory CN=Inventory       # 3. generate backend + frontend CRUD
# 4. merge the three .md i18n stubs under web/src/locales/langs/_generated/inventory/
make mm                                           # 5. run migrations
make dev                                          # 6. verify
make check-all                                    # 7. pre-commit
```

Full walkthrough and field type mappings: [Development guide](https://sleep1223.github.io/fast-soy-admin-docs/en/backend/development).

## Architecture

```
app/
├── core/          # Framework infra (CRUDBase / CRUDRouter / Schema / auth / cache / events / Sqids)
├── system/        # System modules (auth / user / role / menu / api / dictionary / radar)
├── business/      # Business modules (autodiscovered)
│   └── hr/        #   Reference module
├── cli/           # Code generator
└── utils/         # Unified re-export surface for business modules
web/src/
├── views/         # Pages (Elegant Router source)
├── service/api/   # Alova HTTP wrappers
├── typings/api/   # TS types
├── store/modules/ # Pinia
├── router/        # Elegant Router + guards
└── locales/       # vue-i18n
```

Layers: `api/` → `services/` → `controllers/` → `models + schemas`. Business modules must **not** reverse-import `app.system.*` (except for a few explicitly exposed services) and must **not** import sibling modules — cross-module communication uses the event bus. See [architecture](https://sleep1223.github.io/fast-soy-admin-docs/en/backend/architecture).

## Switching databases

Change `DB_URL` in `.env` and run `make initdb`. SQLite / PostgreSQL / MySQL / SQL Server are supported out of the box.

Only the **SQLite** driver is installed by default; switching to another database requires installing the matching extra:

```bash
uv sync --extra postgres     # PostgreSQL (asyncpg)
uv sync --extra mysql        # MySQL (asyncmy)
uv sync --extra mssql        # SQL Server (asyncodbc)
uv sync --extra oracle       # Oracle (asyncodbc)
```

A business module can also declare its own `DB_URL` in its `config.py`; autodiscover registers it as a dedicated connection `conn_<biz>`. For cross-model transactions, use `get_db_conn(Model)` to pick the correct connection. See [switch database](https://sleep1223.github.io/fast-soy-admin-docs/en/backend/database).

## Response Codes

All endpoints share the shape `{"code": "xxxx", "msg": "...", "data": ...}` with HTTP status always 200. Code ranges:

| Range       | Meaning                                         | Typical frontend behavior          |
| ----------- | ----------------------------------------------- | ---------------------------------- |
| `0000`      | Success                                         | Normal processing                  |
| `1xxx`      | Internal errors (validation, DB, serialization) | Auto-toasted by the framework      |
| `21xx`      | Authentication failure                          | Logout / modal / auto token refresh |
| `22xx`      | Authorization failure (RBAC / button / role / super-admin) | Show error toast        |
| `23xx`      | Resource conflict (unique constraint)           | Show error toast                   |
| `24xx`      | Generic business failure                        | Show error toast                   |
| `25xx`      | Rate-limit / security                           | Show error toast                   |
| `26xx`      | Schema required-field fallback                  | Show error toast                   |
| `4000–9999` | User-defined (business module codes start at `4000`; HR sample: `4000–4007`) | Handled by callers |

See [response codes](https://sleep1223.github.io/fast-soy-admin-docs/en/backend/codes).

## Frontend sync

`web/` is maintained in a separate repository, [fast-soy-admin-frontend](https://github.com/sleep1223/fast-soy-admin-frontend), which has **no common ancestor** with this repo. Upstream sync is a manual `git subtree` workflow — see the commits prefixed with `chore(web): sync with fast-soy-admin-frontend@...`.

## Screenshots

![Home - Chinese](https://sleep1223.github.io/fast-soy-admin-docs/screenshots/home-zh.png)
![Home - English](https://sleep1223.github.io/fast-soy-admin-docs/screenshots/home-en.png)
![Radar - Dashboard](https://sleep1223.github.io/fast-soy-admin-docs/screenshots/radar-dashboard.png)
![Radar - Requests](https://sleep1223.github.io/fast-soy-admin-docs/screenshots/radar-requests.png)
![Radar - SQL](https://sleep1223.github.io/fast-soy-admin-docs/screenshots/radar-sql.png)
![Radar - Exceptions](https://sleep1223.github.io/fast-soy-admin-docs/screenshots/radar-exceptions.png)

## TODO

- [x] Redis caching
- [x] One-command Docker deploy
- [x] CLI code generator (backend + frontend)
- [x] Built-in Radar dashboard (requests / SQL / exceptions / audit)
- [ ] `slim` clean branch
- [ ] End-to-end tests

## Contributing

[Pull requests](https://github.com/sleep1223/fast-soy-admin/pulls) and [issues](https://github.com/sleep1223/fast-soy-admin/issues/new) are both welcome.

<a href="https://github.com/sleep1223/fast-soy-admin/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=sleep1223/fast-soy-admin" />
</a>

## License

[MIT © 2024](./LICENSE)
