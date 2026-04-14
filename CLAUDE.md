# CLAUDE.md

本文件为 Claude Code（claude.ai/code）在本仓库中协作时提供指引。

## 项目概览

FastSoyAdmin 是一套全栈后台管理模板，后端使用 **FastAPI**（Python），前端使用 **Vue3**（TypeScript）。本仓库是一个 monorepo：后端代码位于仓库根目录下的 `/app`，前端位于 `/web`（通过 pnpm workspaces 管理）。

## 常用命令

### 后端

```bash
# 安装依赖（推荐使用 uv 或 pdm）
uv sync                        # 或：pdm install
# 启动开发服务器（端口 9999）
python run.py
# 代码检查与格式化
ruff check app/                # lint
ruff format app/               # format
# 类型检查
basedpyright app/
# 单元测试
pytest tests/ -v
```

### 数据库迁移（手动执行，启动时不会自动迁移）

应用在启动时**不会**自动建表或执行迁移。模型变更时请手动运行：

```bash
tortoise makemigrations        # 为模型变更生成迁移文件
tortoise migrate               # 应用未执行的迁移
```

在全新克隆的仓库上，请先运行 `tortoise makemigrations && tortoise migrate` 再执行 `python run.py`，否则 Tortoise 在查询不存在的表时会报错。

### 前端

```bash
cd web
pnpm install                  # 安装依赖
pnpm dev                      # 开发服务器（端口 9527）
pnpm build                    # 生产构建
pnpm lint                     # eslint
pnpm typecheck                # vue-tsc 类型检查
```

### Docker

```bash
docker compose up -d          # 全栈启动：nginx(:1880) + fastapi + redis
```

## 架构

### 后端（`/app`）

分层、模块化架构。后端拆分为两个顶层包：

- `app/system/` — 内置系统模块（认证、RBAC、用户、角色、菜单、API、路由）
- `app/business/` — 用户层业务模块，启动时自动发现

每个模块内部保持相同的目录结构：`api/` → `controllers/` → `services/` → `models` + `schemas`。

#### 分层

- **api/** — FastAPI 路由层，作为轻量的 HTTP 适配器。接收请求、调用 service/controller、返回 `Success`/`Fail`。
- **controllers/** — 继承自 `app.core.crud` 的 `CRUDBase`。只负责单资源的 CRUD 以及 `build_search`。不做跨资源编排，也不产生单表以外的副作用。
- **services/** — 多模型编排、缓存、Redis 写入、事务、审计日志。所有非平凡逻辑都放在这里。
- **models** — Tortoise ORM 模型，统一继承 `app.core.base_model.BaseModel`（提供审计字段）。
- **schemas** — Pydantic v2 模型，统一继承 `app.core.base_schema.SchemaBase`，自动实现 `snake_case ↔ camelCase` 的别名转换。

#### 关键文件

- `app/__init__.py` — 应用工厂、中间件注册、生命周期钩子
- `app/core/`：
  - `init_app.py` — 中间件列表、异常处理器、路由挂载、数据库注册
  - `base_schema.py` — `SchemaBase`、`PageQueryBase`、`Success`/`Fail`/`SuccessExtra`、`CommonIds`、`OfflineByRoleRequest`
  - `base_model.py` — ORM 基类，提供 `created_at`/`updated_at`/`created_by`/`updated_by` 审计字段
  - `crud.py` — `CRUDBase` 泛型类以及用于事务的 `get_db_conn(model)` 辅助函数
  - `router.py` — `CRUDRouter` 工厂，批量生成标准 CRUD 路由并支持 override 钩子
  - `dependency.py` — `DependAuth`（JWT 认证）和 `DependPermission`（RBAC 鉴权），均作为 FastAPI 依赖项
  - `autodiscover.py` — 扫描 `app/business/*` 下的模型、路由与初始化数据
  - `middlewares.py` — 请求 ID、后台任务、异常美化等中间件
  - `ctx.py` — 上下文变量（`CTX_USER_ID`、`CTX_ROLE_CODES`、`CTX_BUTTON_CODES` 等）
  - `config.py` — 从 `.env` 加载的 Pydantic Settings；Tortoise ORM 配置也在此
- `app/utils/__init__.py` — 面向业务模块的公共导入出口（`from app.utils import CRUDBase, CRUDRouter, Success, Fail, SchemaBase, DependPermission, get_db_conn, ...`）。业务代码应从这里导入，而不要直接访问 `app.core.*`。
- `app/system/`：
  - `api/` — `auth`、`users`、`roles`、`menus`、`apis`、`route`、`health` 等路由
  - `controllers/` — `user`、`role`、`menu`、`api`
  - `services/` — `auth`（令牌失效、模拟登录、登录流程）、`user`（用户创建）、`captcha`、`monitor`、`init_helper`
  - `models/admin.py` — User、Role、Menu、Api、Button
  - `schemas/` — `users.py`、`admin.py`、`login.py`
  - `security.py` — 密码哈希（argon2）、JWT 生成
  - `radar/` — fastapi-radar 集成（请求/查询捕获、Dashboard）

### 前端（`/web`）

Vue3 + Vite + Naive UI + Elegant Router + Pinia

- `web/src/views/` — 页面组件
- `web/src/service/api/` — API 请求封装（按后端模块一个文件）
- `web/src/store/` — Pinia 状态管理
- `web/src/router/` — Elegant Router 配置（根据文件结构自动生成路由）
- `web/src/locales/` — 国际化翻译
- `web/src/typings/api/` — 与后端 schema 对应的 TypeScript 接口定义
- `web/packages/` — 内部 monorepo 子包（alova、axios、hooks、utils、color、uno-preset）

### 数据库

- 默认：SQLite（`app_system.sqlite3`）
- ORM：Tortoise ORM（仓库 `/tortoise-orm/` 下有一份 vendored 副本，通过 uv/pdm 的本地依赖引入）
- 迁移：Tortoise 内置工具，需手动执行（见上文"数据库迁移"）
- 缓存：通过 fastapi-cache2 接入 Redis

## 业务模块（自动发现）

业务模块位于 `app/business/<module_name>/`。启动时 `app/core/autodiscover.py` 会扫描所有含 `__init__.py` 的子目录，并尝试按约定加载：

| 约定 | 提供的能力 |
|---|---|
| `app/business/<name>/models.py` 或 `models/` | Tortoise 模型 → 注册到 `TORTOISE_ORM["apps"]` |
| `app/business/<name>/api/` 或 `api.py` | 必须导出 `router: APIRouter` → 挂载到 `/api/v1/business/` |
| `app/business/<name>/init_data.py` | 可选的 `async def init()` → 在系统初始化之后、缓存刷新之前执行 |

**模块目录约定**（可参考 `app/business/hr/`）：

```
app/business/<name>/
├── __init__.py
├── config.py          # BIZ_SETTINGS，按模块隔离的 Pydantic Settings
├── ctx.py             # 本模块的上下文变量（按需）
├── dependency.py      # 本模块的 FastAPI 依赖
├── models.py          # Tortoise 模型
├── schemas.py         # Pydantic schema（继承 SchemaBase）
├── controllers.py     # CRUDBase 子类（单资源）
├── services.py        # 多模型编排
├── init_data.py       # async def init() → 创建默认数据、菜单、权限
└── api/
    ├── __init__.py    # 必须导出汇总子路由后的 `router`
    ├── manage.py
    └── my.py
```

`app/business/` 下以 `_` 开头的目录会被跳过。业务模块内部不得从 `app.system.*` 反向导入——只允许单向依赖（system → 不知道 business）。

### 启动时的初始化与对账

每次启动时，由 Redis leader worker 执行：`init_menus()` → `refresh_api_list()` → `init_users()` → 依次调用各业务模块的 `init_data.init()` → `refresh_all_cache()`。

**不同数据类型的同步语义：**
- **API** — `refresh_api_list()` 会对照 FastAPI 实际路由做全量对账（新增、删除过期、更新元数据），无需手动维护。
- **菜单 / 按钮** — `ensure_menu()` 仅做 upsert。若还要清理**已移除**的条目，需在模块的 `_init_menu_data()` 末尾调用 `reconcile_menu_subtree(root_route=..., declared_route_names=..., declared_button_codes=...)`。该调用将删除严格限定在 `root_route` 下的 BFS 子树范围内，不会波及兄弟模块。参考实现见 [app/business/hr/init_data.py](app/business/hr/init_data.py)。
- **角色** — `ensure_role()` 会 upsert 角色主体，并对 `menus`/`buttons`/`apis` 的授权做"清空后重新关联"。从 seed 列表里**删除**一个角色**不会**删除对应的 `Role` 行——这需要走迁移。
- **业务种子数据** — 通过 `_safe_update_or_create` 按唯一键 upsert。删除同样需要走迁移。

**漂移告警：** 当声明的 `route_name` / `button_code` / `(method, path)` 无法解析时，`ensure_role` 会输出 warning——务必修复，这通常意味着 seed 列表与重命名或删除后的代码脱节了。

**一旦启用 `reconcile_menu_subtree`，该子树就会被视为 Infrastructure-as-Code**：通过 Web UI 手工创建在该子树下的菜单/按钮会在下次重启时被清除。如果你需要允许用户动态创建菜单，就**不要**对那个子树调用 `reconcile_menu_subtree`。

完整说明见 [fast-soy-admin-docs/src/backend/init-data.md](fast-soy-admin-docs/src/backend/init-data.md)。

## API 约定

所有 system 与 business 模块的 HTTP 接口都遵循同一套约定，属于强制规范；若确有必要偏离，请先讨论后再合入。

### 响应格式

任何成功响应都形如 `{"code": "0000", "msg": "OK", "data": {...}}`。请使用来自 `app.core.base_schema` 的 `Success` / `SuccessExtra` / `Fail`。**不要**返回裸 dict，也不要输出 snake_case 字段——`SchemaBase` 的别名生成器会通过 `model_dump(by_alias=True)` 自动产出 camelCase。

### 路径与方法约定

| 操作 | 方法 + 路径 | Body / Params |
|---|---|---|
| 列表/搜索 | `POST /resources/search` | Body: `XxxSearch`（继承 `PageQueryBase`） |
| 单条查询 | `GET /resources/{id}` | — |
| 创建 | `POST /resources` | Body: `XxxCreate` |
| 更新 | `PATCH /resources/{id}` | Body: `XxxUpdate` |
| 单条删除 | `DELETE /resources/{id}` | — |
| 批量删除 | `DELETE /resources` | Body: `{ids: [...]}`（使用 `CommonIds`） |
| 子资源查询 | `GET /resources/{id}/sub` | — |
| 子资源更新 | `PATCH /resources/{id}/sub` | Body |
| 派生查询 | `GET /resources/tree`、`GET /resources/pages` | — |
| 实例动作 | `POST /resources/{id}/action-name` | 视情况带 Body |
| 集合动作 | `POST /resources/batch-offline`、`POST /resources/refresh` | Body |

**不要**带尾斜杠。多词路径使用 kebab-case（如 `batch-offline`、`constant-routes`）。资源名统一使用复数形式。

### 请求/响应字段命名

- 请求体和 query 参数使用 **camelCase**（即别名形式）。由于 Pydantic 开启了 `validate_by_name=True`，snake_case 也能被接受，但前端始终发送 camelCase。
- 响应 `data` 字段也使用 **camelCase**。请使用 `schema.model_dump(by_alias=True)` 或 `model.to_dict()`（后者内部已处理）。**不要**手工拼 snake_case 的响应字典。
- 分页字段统一为：`current` / `size`（默认 `current=1, size=10`）。

### CRUDRouter

`app/core/router.py` 导出了 `CRUDRouter` —— 一个批量生成 6 个标准路由的工厂。当某条路由需要自定义逻辑时，请使用 `override=` 钩子，而不要手写重复的路由：

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

## Gate Checks（质量门禁）

修改代码后，收尾前请跑对应的检查：

### 后端

```bash
ruff check app/               # lint
ruff format app/              # format
basedpyright app              # 类型检查
pytest tests/ -v              # 单元测试
```

### 前端

```bash
cd web
pnpm lint                     # eslint
pnpm typecheck                # vue-tsc 类型检查
```

## 配置

- `.env` — SECRET_KEY、APP_DEBUG、CORS、Redis URL、数据库路径
- `ruff.toml` — 行宽 200，规则 E/F/I，使用双引号
- basedpyright 对 `app/` 目录启用 standard 模式（配置节 `[tool.basedpyright]`）

## 部署

Nginx 负责托管构建后的前端静态资源，并将 `/api/*` 反向代理到 FastAPI 后端（端口 9999），Redis 提供缓存。整体通过 `docker-compose.yml` 编排，配置文件位于 `/deploy/`。
