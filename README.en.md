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

A batteries-included full-stack admin template — usable as an internal-tools scaffold and as a reference for modern full-stack development.

- **Backend** — FastAPI · Pydantic v2 · Tortoise ORM · Redis
- **Frontend** — Vue3 · Vite7 · TypeScript · Naive UI · UnoCSS · Pinia · Alova · Elegant Router
- **Infra** — Docker Compose (Nginx + FastAPI + Redis), multi-worker startup lock, fastapi-guard, built-in Radar dashboard
- **Code generator** — `cli-init` to scaffold, write `models.py`, `cli-gen-all` to emit backend + frontend CRUD

## Highlights

**AI-native**

- **AI-coding friendly** — ships with [CLAUDE.md](CLAUDE.md) + [llms.txt](llms.txt) / [llms-full.md](llms-full.md) feeding Claude Code / Cursor / Copilot the full architecture, layering rules, API conventions, response codes and PR checklist; agents produce code that matches project conventions out of the box
- **Generator as the AI workbench** — `cli-gen-all` collapses "add a table" into one command; the agent only owns `models.py` and override diffs, the rest is emitted by the CLI

**Engineering velocity**

- **End-to-end CLI codegen** — one command turns a Tortoise model into full backend (schemas / controllers / api) + frontend (views / service / typings / i18n) CRUD
- **CRUDRouter + `@crud.override`** — the factory emits 6 standard routes; only override diffs. "No aggregate roots" boundary is explicit to prevent abstraction bloat

**Extensible architecture**

- **Autodiscovered modules** — drop a package into `app/business/<name>/` and routes, models, and init data register themselves; modules are decoupled, cross-module talk goes via the event bus (`emit` / `on`)
- **Multi-database friendly** — modules can declare their own `DB_URL` and get a dedicated `conn_<biz>`; transactions always go through `in_transaction(get_db_conn(Model))`
- **Multi-worker startup coordination** — a Redis leader lock serializes `init_menus → refresh_api_list → init_data → refresh_cache`, so K8s replicas don't double-reconcile

**Security & permissions**

- **Three-tier RBAC + row-level `data_scope`** — menu / API / button checks plus `all / department / self / custom` data scope; button checks live in services, not just in UI
- **Menu / role IaC reconciliation** — `ensure_menu` / `reconcile_menu_subtree` / `refresh_api_list` give three explicit semantics so you know which subtrees are code-owned and which are user-editable
- **Sqid public IDs** — auto-increment IDs never leak; enumeration-safe

**Contracts & typing**

- **Unified responses** — `{code, msg, data}` with HTTP 200 + snake_case ↔ camelCase; `BizError` propagates business failures with unique codes
- **End-to-end type safety** — basedpyright (standard) on the backend, vue-tsc on the frontend, both gated in CI
- **Statically checked i18n** — generator output merges via `import.meta.glob`; `App.I18n.GeneratedPages` lets `vue-tsc` validate every `$t` key

**Observability & resilience**

- **Built-in Radar dashboard** — `/manage/radar/*` for real-time request / SQL / exception / permission-deny logs
- **fastapi-guard** — rate limiting + IP banning; blocks brute-force and scanner traffic automatically
- **Redis cache + graceful fallback** — role permissions, constant routes and `token_version` are cached; queries fall back to the DB if Redis is down
- **State machine / event bus** — first-class primitives for workflows like tickets, approvals, orders

**Deployment**

- **One-command Docker** — Nginx + FastAPI + Redis pre-wired; `docker compose up -d` and you're live

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
| `main` | Default; includes the HR example (`app/business/hr/` — employees / departments / tags) |
| `slim` | Clean skeleton with no business examples (in preparation) |

> Want a clean start now? Delete `app/business/hr/` before launching — autodiscover will skip it.

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

> Migrations do **not** run automatically; the container's SQLite is **not** volume-mounted by default. For production, switch to an external DB or mount a volume for `app_system.sqlite3`. See the [deployment guide](https://sleep1223.github.io/fast-soy-admin-docs/en/backend/deployment).

### Local development

```bash
git clone https://github.com/sleep1223/fast-soy-admin.git
cd fast-soy-admin
make install-all     # uv sync + pnpm install
make initdb          # first-time: create tables + seed
make dev             # backend (:9999) + frontend (:9527) in parallel, Ctrl+C stops both
```

## Common Commands

All commands are wrapped in `Makefile`. Run `make help` for the full list.

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

```bash
make cli-init MOD=inventory                       # 1. scaffold the module
$EDITOR app/business/inventory/models.py          # 2. define Tortoise models
make cli-gen-all MOD=inventory CN=Inventory       # 3. generate backend + frontend CRUD (i18n auto-merged)
make mm                                           # 4. run migrations
make dev                                          # 5. verify
make check-all                                    # 6. pre-commit
```

Walkthrough and field type mappings: [Development guide](https://sleep1223.github.io/fast-soy-admin-docs/en/backend/development).

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

Layers: `api/` → `services/` → `controllers/` → `models + schemas`. Business modules **must not** reverse-import `app.system.*` (except a few explicitly exposed services) and **must not** import sibling modules — cross-module talk uses the event bus. See [architecture](https://sleep1223.github.io/fast-soy-admin-docs/en/backend/architecture).

## Switching databases

Change `DB_URL` in `.env` and run `make initdb`. SQLite / PostgreSQL / MySQL / SQL Server supported.

Only the SQLite driver ships by default; install extras as needed:

```bash
uv sync --extra postgres     # PostgreSQL (asyncpg)
uv sync --extra mysql        # MySQL (asyncmy)
uv sync --extra mssql        # SQL Server (asyncodbc)
uv sync --extra oracle       # Oracle (asyncodbc)
```

A module can declare its own `DB_URL` in `config.py`; autodiscover registers it as `conn_<biz>`. For cross-model transactions, use `get_db_conn(Model)` to pick the connection. See [switch database](https://sleep1223.github.io/fast-soy-admin-docs/en/backend/database).

## Response Codes

All endpoints return `{"code": "xxxx", "msg": "...", "data": ...}` with HTTP status always 200.

| Range       | Meaning                                  | Typical frontend behavior           |
| ----------- | ---------------------------------------- | ----------------------------------- |
| `0000`      | Success                                  | Normal processing                   |
| `1xxx`      | Internal / serialization error           | Auto-toasted by the framework       |
| `21xx`      | Auth failure (token / session)           | Logout / modal / auto token refresh |
| `22xx`      | Authorization failure (RBAC / button)    | Show error toast                    |
| `23xx`      | Resource conflict (unique constraint)    | Show error toast                    |
| `24xx`      | Generic business failure                 | Show error toast                    |
| `25xx`      | Rate-limit / security                    | Show error toast                    |
| `26xx`      | Schema required-field fallback           | Show error toast                    |
| `4000–9999` | User-defined (modules start at `4000`)   | Handled by callers                  |

See [response codes](https://sleep1223.github.io/fast-soy-admin-docs/en/backend/codes).

## Frontend sync

`web/` is maintained in a separate repo, [fast-soy-admin-frontend](https://github.com/sleep1223/fast-soy-admin-frontend), with **no common ancestor**. Upstream sync is a manual `git subtree` workflow — see commits prefixed `chore(web): sync with fast-soy-admin-frontend@...`.

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

[Pull requests](https://github.com/sleep1223/fast-soy-admin/pulls) and [issues](https://github.com/sleep1223/fast-soy-admin/issues/new) welcome.

<a href="https://github.com/sleep1223/fast-soy-admin/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=sleep1223/fast-soy-admin" />
</a>

## License

[MIT © 2024](./LICENSE)
