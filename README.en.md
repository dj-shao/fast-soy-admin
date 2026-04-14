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

- **Backend**: FastAPI · Pydantic v2 · Tortoise ORM · Redis
- **Frontend**: Vue3 · Vite7 · TypeScript · Naive UI · UnoCSS · Pinia
- **Code generator**: `make cli-init` → write models → `make cli-gen` → generates schemas / controllers / API / frontend views (with i18n snippets)

Great as a starting point for internal tools and as a learning reference for modern full-stack development.

## Features

- **RBAC** · menu / API / button level permissions; super admin bypasses all checks
- **CLI code generation** · one command turns Tortoise models into a full CRUD stack (backend + frontend + i18n)
- **Automatic routing** · Elegant Router derives frontend routes from files; dynamic routes are injected from the backend
- **Auto module discovery** · drop a package under `app/business/` and it is loaded at startup, no registration
- **Redis caching** · fastapi-cache2 + Redis for faster API responses
- **Unified responses** · every endpoint returns `{code, msg, data}`; automatic snake_case ↔ camelCase
- **Strict typing** · vue-tsc on the frontend, basedpyright on the backend
- **i18n** · vue-i18n with zh / en; the CLI emits i18n snippets for new modules
- **One-command Docker** · Nginx + FastAPI + Redis out of the box

## Links

- [Live preview](https://fast-soy-admin.sleep0.de/)
- [Documentation](https://sleep1223.github.io/fast-soy-admin-docs/en/)
- [Development Guide](https://sleep1223.github.io/fast-soy-admin-docs/en/backend/development)
- [Commands Reference](https://sleep1223.github.io/fast-soy-admin-docs/en/backend/commands)
- [Apifox API docs](https://apifox.com/apidoc/shared-7cd78102-46eb-4701-88b1-3b49c006504b)

## Getting started

### Requirements

| Tool | Version |
|---|---|
| Python | >= 3.12 |
| Node.js | >= 20 |
| uv · pnpm · make | latest |

### Docker (recommended)

```bash
git clone https://github.com/sleep1223/fast-soy-admin.git
cd fast-soy-admin
make up              # docker compose up -d
```

Open `http://localhost:1880`.

### Local development

```bash
git clone https://github.com/sleep1223/fast-soy-admin.git
cd fast-soy-admin
make install-all     # install backend + frontend dependencies
make initdb          # first-time database initialization
make dev             # start backend (:9999) and frontend (:9527) together
```

## Common commands

All frequently used commands are wrapped in `Makefile`. Run `make help` to see the full list.

| Command | Purpose |
|---|---|
| `make dev` | Run backend + frontend dev servers together |
| `make check-all` | Run all backend + frontend quality gates (before committing) |
| `make mm` | Make + apply database migrations |
| `make cli-init MOD=xxx` | Scaffold a new business module |
| `make cli-gen MOD=xxx` | Generate backend code from `models.py` |
| `make up` / `make down` / `make logs` | Docker lifecycle |

See the [Commands Reference](https://sleep1223.github.io/fast-soy-admin-docs/en/backend/commands) for the complete list.

## Adding a new business module

End-to-end example for an `inventory` module:

```bash
make cli-init MOD=inventory                                       # 1. scaffold
$EDITOR app/business/inventory/models.py                          # 2. define Tortoise models
make cli-gen MOD=inventory                                        # 3. generate backend
uv run python -m app.cli gen-web inventory --cn-name Inventory    # 4. generate frontend
make mm                                                           # 5. run migrations
make dev                                                          # 6. verify
```

Full walkthrough and field type mappings: [Development Guide](https://sleep1223.github.io/fast-soy-admin-docs/en/backend/development).

## Response codes

All endpoints share the shape `{"code": "xxxx", "msg": "...", "data": ...}`. Code ranges:

| Range | Meaning | Frontend behavior |
|---|---|---|
| `0000` | Success | Normal processing |
| `1xxx` | Internal errors (validation, DB, serialization) | Auto toast by the framework |
| `21xx` | Authentication failure | Redirect to login or auto-refresh token |
| `22xx` | Authorization failure (RBAC) | Show error toast |
| `23xx` | Resource conflict (unique constraint) | Show error toast |
| `24xx` | Generic business failure | Show error toast |
| `4000–9999` | User-defined | Handled by callers |

See [Response Codes](https://sleep1223.github.io/fast-soy-admin-docs/en/backend/codes).

## Frontend sync

`web/` is maintained in a separate repo, [fast-soy-admin-frontend](https://github.com/sleep1223/fast-soy-admin-frontend), which has **no common ancestor** with this one. Keeping it in sync requires a manual flow — look at previous commits prefixed with `chore(web): sync with fast-soy-admin-frontend@...` for the canonical recipe.

## Screenshots

![](https://soybeanjs-1300612522.cos.ap-guangzhou.myqcloud.com/uPic/soybean-admin-v1-01.png)
![](https://soybeanjs-1300612522.cos.ap-guangzhou.myqcloud.com/uPic/soybean-admin-v1-04.png)
![](https://soybeanjs-1300612522.cos.ap-guangzhou.myqcloud.com/uPic/soybean-admin-v1-07.png)

## Roadmap

- [x] Redis caching
- [x] One-command Docker deploy
- [x] CLI code generator (backend + frontend)
- [ ] FastCRUD integration

## Contributing

[Pull requests](https://github.com/sleep1223/fast-soy-admin/pulls) and [issues](https://github.com/sleep1223/fast-soy-admin/issues/new) are both welcome.

<a href="https://github.com/sleep1223/fast-soy-admin/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=sleep1223/fast-soy-admin" />
</a>

## License

[MIT © 2024](./LICENSE)
