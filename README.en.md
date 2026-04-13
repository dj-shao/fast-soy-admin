<!-- markdownlint-disable MD033 MD041 -->

<p align="center">
  <a href="https://github.com/sleep1223/"><img src="web/public/favicon.svg" width="200" height="200" alt="github"></a>
</p>

<div align="center">

# FastSoyAdmin

<!-- prettier-ignore-start -->
<!-- markdownlint-disable-next-line MD036 -->

[![license](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![github stars](https://img.shields.io/github/stars/sleep1223/fast-soy-admin)](https://github.com/sleep1223/fast-soy-admin)
[![github forks](https://img.shields.io/github/forks/sleep1223/fast-soy-admin)](https://github.com/sleep1223/fast-soy-admin)
![python](https://img.shields.io/badge/python-3.12+-blue?logo=python&logoColor=edb641)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?logo=python&logoColor=edb641)

![Pydantic](https://img.shields.io/badge/Pydantic_v2-005571?logo=pydantic&logoColor=edb641)
![uv](https://img.shields.io/badge/uv-managed-blueviolet)
[![pyright](https://img.shields.io/badge/types-pyright-797952.svg?logo=python&logoColor=edb641)](https://github.com/Microsoft/pyright)
[![ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

[![DeepWiki](https://img.shields.io/badge/DeepWiki-sleep1223%2Ffast--soy--admin-blue?logo=data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHZpZXdCb3g9IjAgMCAzMiAzMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9IjMyIiBoZWlnaHQ9IjMyIiByeD0iOCIgZmlsbD0iIzFFOTBGRiIvPgo8cGF0aCBkPSJNOCAxMEgxMlYyMkg4VjEwWiIgZmlsbD0id2hpdGUiLz4KPHBhdGggZD0iTTE1IDEwSDE5VjIySDE1VjEwWiIgZmlsbD0id2hpdGUiIG9wYWNpdHk9IjAuNyIvPgo8cGF0aCBkPSJNMjIgMTBIMjZWMjJIMjJWMTBaIiBmaWxsPSJ3aGl0ZSIgb3BhY2l0eT0iMC40Ii8+Cjwvc3ZnPg==)](https://deepwiki.com/sleep1223/fast-soy-admin)

<span>English | <a href="./README.md">中文</a></span>

</div>

> [!NOTE]
> If `FastSoyAdmin` is helpful to you, please give us a ⭐️ on GitHub. Your support means the world to us!

## Introduction

[`FastSoyAdmin`](https://github.com/sleep1223/fast-soy-admin) is a production-ready, full-stack admin template. The frontend is built with Vue3, Vite7, TypeScript, Pinia, and UnoCSS; the backend is powered by FastAPI, Pydantic v2, and Tortoise ORM, with Redis for caching to accelerate API responses. The project comes with rich theme configurations, a complete RBAC permission system, automated file-based routing, and multi-language support. It is ideal as a starting scaffold for admin projects and a great resource for learning full-stack development best practices.

## Features

- **Full-Stack Tech Stack**: Backend with FastAPI + Pydantic v2 + Tortoise ORM; frontend with Vue3 + Vite7 + TypeScript + Pinia + UnoCSS — both using mainstream, modern technologies.
- **Complete Permission System**: Based on the RBAC model with strict separation of roles and permissions between frontend and backend. The backend performs secondary authorization at the API and button level, ensuring security and control.
- **Logging & Auditing**: Built-in request logging and operation log management for easy troubleshooting and audit trails.
- **Redis Cache Acceleration**: Integrated fastapi-cache2 + Redis to effectively improve API response speed.
- **Clear Project Structure**: Managed with pnpm monorepo; backend follows a layered architecture (Router → Controller → CRUD/Model), keeping the codebase clean and maintainable.
- **Strict Code Standards**: Frontend follows the [SoybeanJS specification](https://docs.soybeanjs.cn/zh/standard), with ESLint + oxlint + simple-git-hooks integration; backend uses [Ruff](https://docs.astral.sh/ruff/) + [Pyright](https://microsoft.github.io/pyright) to maintain consistent code style.
- **Full TypeScript Coverage**: Supports strict type checking to improve code maintainability and developer experience.
- **Rich Theme Configuration**: Built-in multiple theme options, deeply integrated with UnoCSS for easy UI customization.
- **Internationalization Support**: Built-in vue-i18n multi-language solution (Chinese / English), switch languages with one click.
- **Rich Pages & Components**: Built-in 403, 404, 500 error pages, integrated with ECharts, AntV, VChart and other visualization libraries, plus rich text editor, Markdown editor, and more.
- **Mobile Adaptation**: Responsive layout with full support for mobile access.
- **One-Click Docker Deployment**: Complete Docker Compose configuration (Nginx + FastAPI + Redis) — start the full stack with a single command.

## Related Links

- [Live Preview](https://fast-soy-admin.sleep0.de/)
- [Project Documentation](https://sleep1223.github.io/fast-soy-admin-docs/zh/)
- [Apifox API Documentation](https://apifox.com/apidoc/shared-7cd78102-46eb-4701-88b1-3b49c006504b)
- [GitHub Repository](https://github.com/sleep1223/fast-soy-admin)
- [SoybeanAdmin](https://gitee.com/honghuangdc/soybean-admin)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Tortoise ORM](https://tortoise.github.io)

## Screenshots

![](https://soybeanjs-1300612522.cos.ap-guangzhou.myqcloud.com/uPic/soybean-admin-v1-01.png)
![](https://soybeanjs-1300612522.cos.ap-guangzhou.myqcloud.com/uPic/soybean-admin-v1-02.png)

![](https://soybeanjs-1300612522.cos.ap-guangzhou.myqcloud.com/uPic/soybean-admin-v1-04.png)

![](https://soybeanjs-1300612522.cos.ap-guangzhou.myqcloud.com/uPic/soybean-admin-v1-06.png)
![](https://soybeanjs-1300612522.cos.ap-guangzhou.myqcloud.com/uPic/soybean-admin-v1-07.png)
![](https://soybeanjs-1300612522.cos.ap-guangzhou.myqcloud.com/uPic/soybean-admin-v1-08.png)

![](https://raw.githubusercontent.com/sleep1223/fast-soy-admin-docs/51832d41f1d951bd9d61a9bcfdf137deb81fd3c5/src/assets/QQ%E6%88%AA%E5%9B%BE20240517223056.jpg)
![](https://raw.githubusercontent.com/sleep1223/fast-soy-admin-docs/51832d41f1d951bd9d61a9bcfdf137deb81fd3c5/src/assets/QQ%E6%88%AA%E5%9B%BE20240517223123.jpg)

![](https://soybeanjs-1300612522.cos.ap-guangzhou.myqcloud.com/uPic/soybean-admin-v1-09.png)
![](https://soybeanjs-1300612522.cos.ap-guangzhou.myqcloud.com/uPic/soybean-admin-v1-10.png)
![](https://soybeanjs-1300612522.cos.ap-guangzhou.myqcloud.com/uPic/soybean-admin-v1-mobile.png)

## Quick Start

### Method 1: Docker Deployment (Recommended)

```bash
# Clone the project
git clone https://github.com/sleep1223/fast-soy-admin
cd fast-soy-admin

# Start all services
docker compose up -d

# View logs
docker compose logs -f        # All services
docker compose logs -f app    # FastAPI only
docker compose logs -f nginx  # Nginx only
docker compose logs -f web    # Frontend build only
```

Redeploy after updating code:

```bash
docker compose down && docker compose up -d
```

### Method 2: Local Development

**Requirements**

| Tool    | Version    |
| ------- | ---------- |
| Git     | -          |
| Python  | >= 3.12    |
| Node.js | >= 20.0.0  |
| uv      | ---------- |
| pnpm    | ---------- |

**Installation & Startup**

```bash
# Clone the project
git clone https://github.com/sleep1223/fast-soy-admin
cd fast-soy-admin

# Backend dependencies
uv sync  # or: pdm install / pip install -r requirements.txt

# Frontend dependencies (please use pnpm, as the project uses pnpm monorepo)
cd web && pnpm install

# Start backend (port 9999)
uv run python run.py

# Start frontend (port 9527, in a new terminal)
cd web && pnpm dev
```

**Build Frontend**

```bash
cd web && pnpm build
```

## Manually syncing frontend code

The `web/` directory is maintained in a separate repository: [fast-soy-admin-frontend](https://github.com/sleep1223/fast-soy-admin-frontend). The two repos share **no common ancestor** (`git merge-base` is empty), so `git merge` / `git cherry-pick` will not work. Use the workflow below instead.

### 1. Configure the upstream remote (one-time)

```bash
git remote add frontend https://github.com/sleep1223/fast-soy-admin-frontend.git
git fetch frontend
```

### 2. Check whether upstream has new commits

```bash
git fetch frontend

# Latest upstream commits
git log frontend/example --oneline -20

# Latest sync commit on this repo
git log --grep="upgrade frontend\|sync.*frontend" --format="%h %ci %s" | head -5
```

If the newest `frontend/example` commit is older than (or the same as) the last sync commit here, there is nothing to pull.

### 3. Work on an isolated branch

```bash
git switch -c chore/sync-frontend
```

### 4. Replace `web/` while preserving backend-specific files

`web/` in this repo already contains backend-specific additions (HR / Radar / business modules, tests, etc.) that do not exist upstream. Wholesale replacement would drop them. The recommended flow is "overwrite, then restore the backend-only files from `HEAD`":

```bash
# 4.1 Record current HEAD so we can restore files from it later
PREV=$(git rev-parse HEAD)

# 4.2 Clear web/ and import from upstream
git rm -rf web
git read-tree --prefix=web/ -u frontend/example

# 4.3 Restore backend-only files (paths that exist here but not upstream)
git restore --source=$PREV --staged --worktree -- \
    web/vitest.config.ts \
    web/src/components/common/ansi-traceback.vue \
    web/src/hooks/common/polling.ts \
    web/src/service/api/__tests__ \
    web/src/service/api/business \
    web/src/service/api/hr-manage.ts \
    web/src/service/api/monitor.ts \
    web/src/service/api/radar.ts \
    web/src/store/modules/business \
    web/src/typings/api/hr-manage.d.ts \
    web/src/typings/api/radar.d.ts \
    web/src/views/business \
    web/src/views/hr \
    web/src/views/manage/radar
```

You can regenerate the "local-only" file list with the following command (note that `frontend/example` has no `web/` prefix):

```bash
diff <(git ls-tree -r --name-only HEAD web/ | sed 's|^web/||' | sort) \
     <(git ls-tree -r --name-only frontend/example | sort) \
     | grep '^<' | sed 's|^< |web/|'
```

### 5. Merge files edited on both sides by hand

Some upstream files are also modified locally (e.g. `web/src/service/api/auth.ts`, `web/src/views/manage/role/**`, `web/src/typings/api/*.d.ts`). Step 4 will clobber them with the upstream version. Go through each one and re-apply the backend-facing changes:

```bash
# List files whose local version diverged from upstream
git diff --name-only $PREV -- web/

# Inspect the previous local version of a specific file as merge reference
git show $PREV:web/src/service/api/auth.ts
```

A side-by-side diff tool (or `git difftool $PREV -- web/<path>`) helps a lot here.

### 6. Validate locally

```bash
cd web
pnpm install         # lockfile may have changed
pnpm typecheck
pnpm lint
pnpm build           # smoke-test the production build
pnpm dev             # click through the key pages in a browser
```

Also run the backend (`python run.py`) and verify login, RBAC, HR, Radar etc. still work end-to-end.

### 7. Commit

Record the upstream commit you synced against — that becomes the starting point for the next sync:

```bash
git add web
git commit -m "chore(web): sync with fast-soy-admin-frontend@<upstream-short-sha>"
```

Then merge the branch back into `dev`.

## TODO

- [x] Optimize response speed using Redis
- [x] Deploy using Docker
- [ ] Integrate FastCRUD

## Contributing

We welcome [Pull Requests](https://github.com/sleep1223/fast-soy-admin/pulls) and [Issues](https://github.com/sleep1223/fast-soy-admin/issues/new). Any form of contribution is greatly appreciated.

## Contributors

Thanks to all the developers who have contributed to this project.

<a href="https://github.com/mizhexiaoxiao">
    <img src="https://github.com/mizhexiaoxiao.png?size=120" width="64" height="64" style="border-radius:50%;" />
</a>

<a href="https://github.com/soybeanjs.png">
    <img src="https://github.com/soybeanjs.png?size=120" width="64" height="64" style="border-radius:50%;" />
</a>

<a href="https://github.com/sleep1223/fast-soy-admin/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=sleep1223/fast-soy-admin" />
</a>

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=sleep1223/fast-soy-admin&type=Date)](https://star-history.com/#sleep1223/fast-soy-admin&Date)

## License

This project is licensed under the [MIT © 2024](./LICENSE) license. Free to use and modify. For commercial use, please retain the author's copyright information. The author provides no warranty or liability for the software.
