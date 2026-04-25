# CLAUDE.md

本文件为 Claude Code（claude.ai/code）在本仓库中协作时提供指引。

## 项目概览

FastSoyAdmin 是一套全栈后台管理模板，后端使用 **FastAPI**（Python），前端使用 **Vue3**（TypeScript）。整个仓库是一个 monorepo：后端代码在 `/app`，前端在 `/web`（pnpm workspace）；部署配置在 `/deploy`，Tortoise 迁移在 `/migrations`。

完整文档见 [llms-full.md](llms-full.md) 与在线文档 <https://sleep1223.github.io/fast-soy-admin-docs/>。

## 常用命令

所有命令都封装在根目录 `Makefile`。运行 `make` 或 `make help` 列出全部命令。

### 一次性

```bash
make install-all            # 同装后端 (uv sync) + 前端 (pnpm install)
make initdb                 # 首次初始化数据库（建表 + 基础数据）
```

> 启动时**不会**自动迁移。新克隆的仓库先 `make initdb`。此后每次模型变更手动跑 `make mm`。

### 开发

```bash
make dev                    # 并行启动后端 :9999 + 前端 :9527，Ctrl+C 一起停
make run                    # 仅后端
make web-dev                # 仅前端
```

### 数据库迁移

```bash
make makemigrations         # 生成迁移
make migrate                # 应用迁移
make mm                     # == makemigrations + migrate
make dbhistory              # 迁移历史
```

### CLI 代码生成（开发业务模块首选方式）

```bash
make cli-init MOD=xxx                      # 生成模块骨架，仅含 models.py
# 编辑 app/business/xxx/models.py 定义模型
make cli-gen-all MOD=xxx CN=中文名          # 一次生成后端 + 前端 CRUD（也可分两步跑 cli-gen / cli-gen-web）
make mm                                    # 迁移
```

### 质量门禁（提交前必跑）

```bash
make check-all              # 后端 + 前端全部检查
```

细分：

```bash
make fmt                    # 后端 ruff check --fix + format
make typecheck              # 后端 basedpyright (standard 模式)
make test                   # 后端 pytest -v
make web-lint               # 前端 eslint + oxlint
make web-typecheck          # 前端 vue-tsc
```

### Docker

```bash
make up                     # docker compose up -d（nginx :1880 + fastapi :9999 + redis）
make logs
make down
```

## 架构

### 后端（`/app`）

两个顶层包：

- `app/system/` — 内置系统模块（认证、RBAC、用户、角色、菜单、API、字典、监控）
- `app/business/<name>/` — 业务模块，启动时自动发现

每个模块内部保持相同分层：`api/` → `services/` → `controllers/` → `models` + `schemas`。

#### 分层职责

| 层 | 写什么 | 不写什么 |
|---|---|---|
| `api/` | URL 接线、鉴权依赖、调 service/controller 的薄包装，返回 `Success`/`Fail` | 业务规则、跨模型、事务 |
| `services/` | 事务、多模型编排、Redis、状态机、审计、事件 | HTTP（Request/Response） |
| `controllers/` | `XxxController(CRUDBase)`、`build_search`；单模型 CRUD | 跨模型编排、事务、缓存、事件派发、外部 IO |
| `models/` | 表字段、索引、关系、Mixin | 业务校验 |
| `schemas/` | `XxxCreate/XxxUpdate/XxxSearch`，字段级校验 | 跨资源 |

#### 依赖方向

- `app/core/` 不依赖 system / business
- `app/system/` 仅依赖 `app/core/`
- `app/business/<x>/` 依赖 `app/utils`（稳定对外入口），**不得**反向 import `app.system.*`（少数显式暴露的 service 如 `ensure_menu` / `ensure_role` 除外），**不得**互相 import 兄弟业务模块——跨模块用事件总线（`emit` / `on`）

#### 关键文件

- `app/__init__.py` — 应用工厂、中间件注册、lifespan、多 worker init 协调
- `app/core/init_app.py` — 中间件列表、异常处理器、路由挂载、数据库注册
- `app/core/base_schema.py` — `SchemaBase`、`PageQueryBase`、`Success`/`Fail`/`SuccessExtra`、`CommonIds`、`OfflineByRoleRequest`、`make_optional`、`ResponseModel`/`PageResponseModel`
- `app/core/base_model.py` — `BaseModel` / `AuditMixin` / `TreeMixin` / `SoftDeleteMixin`、`StatusType`
- `app/core/crud.py` — `CRUDBase`、`get_db_conn(model)`
- `app/core/router.py` — `CRUDRouter` 工厂 + `SearchFieldConfig`
- `app/core/dependency.py` — `DependAuth`、`DependPermission`、`require_buttons(...)`、`require_roles(...)`
- `app/core/autodiscover.py` — 扫描 `app/business/*` 加载模型、路由、初始化数据、独立 DB
- `app/core/ctx.py` — ContextVars（`CTX_USER_ID` / `CTX_ROLE_CODES` / `CTX_BUTTON_CODES` / `CTX_X_REQUEST_ID` 等）
- `app/core/config.py` — Pydantic Settings；Tortoise ORM 配置
- `app/core/code.py` — 全部业务码
- `app/core/exceptions.py` — `BizError`、`SchemaValidationError`、全局处理器
- `app/core/data_scope.py` — 行级 `build_scope_filter(scope, user_id, department_id, ...)`
- `app/core/events.py` — 事件总线（`emit` / `on`）
- `app/core/state_machine.py` — 轻量状态机
- `app/core/sqids.py` — `SqidId`、`SqidPath`、`encode_id` / `decode_id`
- `app/utils/__init__.py` — **业务模块统一 import 入口**（从这里一次导入 `CRUDBase, CRUDRouter, Success, Fail, SchemaBase, DependPermission, require_buttons, BizError, Code, SqidId, emit, StateMachine, get_db_conn, radar_log, ...`）
- `app/system/services/init_helper.py` — `ensure_menu`、`ensure_role`、`reconcile_menu_subtree`、`refresh_api_list`、`refresh_all_cache`
- `app/system/radar/` — 内置 Radar 监控面板（`/manage/radar/*`）

### 前端（`/web`）

Vue3 + Vite + Naive UI + Elegant Router + Pinia + UnoCSS + Alova。

- `web/src/views/` — 页面组件（Elegant Router 按文件结构自动生成路由）
- `web/src/service/api/` — Alova API 封装（按后端模块一个文件，函数命名 `fetchXxx`）
- `web/src/typings/api/` — 对应的 TS 类型（`Api.<Module>.<Type>`）
- `web/src/store/modules/` — Pinia：`auth` / `route` / `tab` / `theme` / `app`
- `web/src/router/` — Elegant Router 配置 + 守卫
- `web/src/locales/` — vue-i18n（zh-CN / en-US）
- `web/src/hooks/` — `useNaivePaginatedTable`、`useTableOperate`、`useRouterPush`、`hasAuth`
- `web/packages/` — 内部子包（alova / axios / hooks / utils / color / uno-preset）

### 数据库

- 默认 SQLite（`app_system.sqlite3`）；支持 Postgres / MySQL / SQL Server
- ORM：Tortoise ORM（仓库 `/tortoise-orm/` 下有 vendored 副本，通过 uv/pdm 的本地依赖引入）
- 迁移：Tortoise 内置工具，手动执行（见上文）
- 缓存：fastapi-cache2 + Redis
- 多库：业务模块可在自己的 `config.py` 声明独立 `DB_URL`，autodiscover 注册独立连接 `conn_<biz>`；跨模型事务用 `get_db_conn(Model)` 取连接名，**不要硬编码** `"conn_system"`

## 业务模块开发（autodiscover）

业务模块放在 `app/business/<module_name>/`。启动时 `autodiscover.py` 扫描所有含 `__init__.py` 的子目录（`_` 前缀目录会被跳过），按约定加载：

| 约定 | 提供的能力 |
|---|---|
| `app/business/<name>/models.py` 或 `models/` | Tortoise 模型 → 注册到 `TORTOISE_ORM["apps"]` |
| `app/business/<name>/api/` 或 `api.py` | 必须导出 `router: APIRouter` → 挂载到 `/api/v1/business/<name>/*` |
| `app/business/<name>/init_data.py` | 可选 `async def init()` → 系统初始化后、缓存刷新前执行 |
| `app/business/<name>/config.py` 中声明 `DB_URL` | 注册独立连接 `conn_<name>` 与独立 app |

推荐目录（参考 `app/business/hr/`）：

```
app/business/<name>/
├── __init__.py
├── config.py          # BIZ_SETTINGS（可选，独立库、环境变量）
├── ctx.py             # 模块上下文变量
├── dependency.py      # 模块专属依赖
├── models.py          # Tortoise 模型
├── schemas.py         # Pydantic schema（继承 SchemaBase）
├── controllers.py     # CRUDBase 子类
├── services.py        # 多模型编排
├── init_data.py       # async def init()：菜单 / 角色 / 种子数据
└── api/
    ├── __init__.py    # 导出汇总后的 router
    ├── manage.py
    └── my.py
```

### 典型新增业务模块流程

```bash
make cli-init MOD=inventory                       # 生成 models.py 骨架
# 编辑 app/business/inventory/models.py
make cli-gen-all MOD=inventory CN=库存管理         # 生成后端 + 前端 CRUD
# 按生成文件头注释合并 i18n 片段到 web/src/locales/langs/
# 处理前端外键 / 自定义枚举的 TODO（options 数据源）
make mm                                           # 迁移
make dev                                          # 验证
make check-all                                    # 提交前
```

### 启动时初始化与对账

每次启动由 Redis leader worker 执行：`init_menus()` → `refresh_api_list()` → `init_users()` → 依次调用各业务模块的 `init_data.init()` → `refresh_all_cache()`。

**不同数据类型的同步语义：**

| 类型 | 同步方式 | 改字段 | 新增 | 删除 | 重命名 |
|---|---|---|---|---|---|
| **API** | `refresh_api_list()` 全量对账 | ✅ | ✅ | ✅ | ✅（删旧建新） |
| **菜单 / 按钮** | `ensure_menu()` upsert + 可选 `reconcile_menu_subtree()` | ✅ | ✅ | ⚠️ 需启用对账 | ⚠️ 需启用对账 |
| **角色** | `ensure_role()` upsert；`menus/buttons/apis` clear-and-readd | ✅ | ✅ | ❌ 走迁移 | ❌ 走迁移 |
| **业务种子数据** | `_safe_update_or_create` 按唯一键 | ✅ | ✅ | ❌ 走迁移 | ❌ 走迁移 |

关键约定：

- **漂移告警**：`ensure_role` 引用的 `route_name` / `button_code` / `(method, path)` 无法解析时会 log.warning——务必立即修复，否则角色权限会静默缺失
- **IaC 模式**：一旦对某子树启用 `reconcile_menu_subtree()`，该子树成为单一数据源，通过 Web UI 手工创建在该子树下的菜单 / 按钮会在下次重启时被清除
- 需要允许用户动态创建菜单的子树，**不要**对它调用 `reconcile_menu_subtree()`

完整说明见 [在线文档 / 启动初始化与对账](https://sleep1223.github.io/fast-soy-admin-docs/backend/init-data)。

## API 约定

所有 system / business 模块的 HTTP 接口强制遵循同一套约定；偏离请先讨论。

### 响应格式

```json
{ "code": "0000", "msg": "OK", "data": { ... } }
```

HTTP status 恒 200。必须用 `app.utils` 的 `Success` / `SuccessExtra` / `Fail`——**不要**返回裸 dict；**不要**输出 snake_case 字段（`SchemaBase` 自动 camelCase）。

### 路径与方法

| 操作 | 方法 + 路径 | Body / Params |
|---|---|---|
| 列表 / 搜索 | `POST /resources/search` | Body 继承 `PageQueryBase` |
| 单条查询 | `GET /resources/{id}` | — |
| 创建 | `POST /resources` | Body: `XxxCreate` |
| 更新 | `PATCH /resources/{id}` | Body: `XxxUpdate` |
| 单条删除 | `DELETE /resources/{id}` | — |
| 批量删除 | `DELETE /resources` | Body: `CommonIds` |
| 子资源 | `GET/PATCH /resources/{id}/sub` | — |
| 派生查询 | `GET /resources/tree` / `/options` / `/pages` | — |
| 实例动作 | `POST /resources/{id}/action-name` | 视情况 |
| 集合动作 | `POST /resources/batch-offline` 等 | Body |

**不要**带尾斜杠。多词路径 **kebab-case**。资源名 **复数**。搜索一律 `POST /search`，不要 `GET ?...=...`。

### 字段命名

- 请求 / 响应一律 **camelCase**；Pydantic `validate_by_name=True` 兼容 snake_case
- 分页字段：`current`（默认 1）/ `size`（默认 10，上限 1000）/ `orderBy`（`["-createdAt", "id"]` 形式）

### 资源 ID 一律 sqid

对外 ID 都是 sqid 字符串（不是自增 int）。Pydantic 中用 `SqidId`，FastAPI 路径参数用 `SqidPath`：

```python
from app.utils import SqidId, SqidPath, SchemaBase

class DepartmentUpdate(SchemaBase):
    parent_id: SqidId | None = None

@router.get("/departments/{item_id}")
async def get_dept(item_id: SqidPath):
    ...
```

### CRUDRouter（不要手写样板路由）

`app/core/router.py` 的 `CRUDRouter` 一次生成 6 条标准路由。自定义某条路由用 `@crud.override(...)`，**不要**在 router 上重新声明同路径（会被 `_OrderedRouter` 排序后遮蔽）。

```python
from app.utils import CRUDRouter, SearchFieldConfig, require_buttons

dept_crud = CRUDRouter(
    prefix="/departments",
    controller=department_controller,
    create_schema=DepartmentCreate,
    update_schema=DepartmentUpdate,
    list_schema=DepartmentSearch,
    search_fields=SearchFieldConfig(
        contains_fields=["name", "code"],
        exact_fields=["status"],
    ),
    summary_prefix="部门",
    soft_delete=True,
    tree_endpoint=True,
    action_dependencies={
        "create": [require_buttons("B_HR_DEPT_CREATE")],
        "update": [require_buttons("B_HR_DEPT_EDIT")],
        "delete": [require_buttons("B_HR_DEPT_DELETE")],
        "batch_delete": [require_buttons("B_HR_DEPT_DELETE")],
    },
)

@dept_crud.override("list")
async def _list(obj_in: DepartmentSearch):
    q = department_controller.build_search(obj_in, contains_fields=["name"])
    total, items = await department_controller.list(
        page=obj_in.current, page_size=obj_in.size, search=q, order=["-id"],
    )
    return SuccessExtra(data={"records": [await i.to_dict() for i in items]},
                       total=total, current=obj_in.current, size=obj_in.size)

router = dept_crud.router
```

#### CRUDRouter 适用边界（避免抽象上瘾）

CRUDRouter 是给**贫血资源**用的——字典、标签、部门、分类这种纯 CRUD 表。聚合根（用户、角色、订单、工单等带状态、带副作用的资源）**不要硬塞进 CRUDRouter**。

满足以下任一条件，立刻把该资源改写为显式 `@router.post(...)` + `services/`，不要继续 `@crud.override`：

- override 数 ≥ 3（标准 6 路由覆盖一半，抽象已无收益）
- 任一 override 内出现 `in_transaction` / `redis` / 跨模型写
- 资源是聚合根或带状态机
- 写操作有副作用（发通知、写审计、触发事件、失效缓存）

**`@crud.override` 内禁止出现的内容**（必须下沉到 `services/`）：

- `in_transaction(...)` —— 事务编排是 service 的事
- `request.app.state.redis` / 任何 Redis 客户端调用
- 跨模型的 `create` / `update` / `delete`（含 `m2m.add` / `m2m.clear`）
- 调用其他模块的 service / 发事件 / 写审计

**正确范式**：override 只做"参数转发 + 包响应"，业务在 service 里：

```python
# services/users.py
async def create_user_with_roles(redis, user_in: UserCreate) -> User:
    if await user_controller.get_by_email(user_in.user_email):
        raise BizError(code=Code.DUPLICATE_USER_EMAIL, msg="该邮箱已被注册")
    async with in_transaction(get_db_conn(User)):
        user = await user_controller.create(obj_in=user_in)
        await user_controller.update_roles_by_code(user, user_in.by_user_role_code_list)
    return user

# api/users.py
@crud.override("create")
async def _create_user(user_in: UserCreate, request: Request):
    user = await create_user_with_roles(request.app.state.redis, user_in)
    return Success(msg="创建成功", data={"createdId": encode_id(user.id)})
```

参考实现：[app/system/api/users.py](app/system/api/users.py) + [app/system/services/user.py](app/system/services/user.py)、[app/system/api/apis.py](app/system/api/apis.py) + [app/system/services/api.py](app/system/services/api.py)。

### 鉴权

- `DependAuth` — 仅 JWT 校验（登录态）
- `DependPermission` — 在 `DependAuth` 之上按 `(method, path)` 校验 `role.apis`（业务接口默认）
- `require_buttons("B_X", ..., require_all=False)` — 任一通过（缺失 `2203`）
- `require_roles(...)` — 同上但针对角色（码 `2204` / `2205`）
- `R_SUPER` 自动跳过所有权限校验

### 行级 data_scope

涉及行级权限的列表接口必须 `@crud.override("list")` 内用 `build_scope_filter(scope, user_id, department_id, ...)` 拼查询。业务角色种子必须显式声明 `data_scope`（`all` / `department` / `self` / `custom`），不要依赖默认。

### 响应码

| 码段 | 含义 |
|---|---|
| `0000` | 成功 |
| `1xxx` | 系统内部错误（异常、入参校验） |
| `2100–2106` | 认证（`INVALID_TOKEN` / `TOKEN_EXPIRED` / `ACCOUNT_DISABLED` / `SESSION_INVALIDATED` 等） |
| `2200–2207` | 授权（`PERMISSION_DENIED` / `MISSING_BUTTON_PERMISSION` / `SUPER_ADMIN_ONLY` 等） |
| `2300–2305` | 资源冲突（`DUPLICATE_*`） |
| `2400–2406` | 通用业务失败（`WRONG_CREDENTIALS` / `OLD_PASSWORD_WRONG` 等） |
| `2500–2502` | 限流 / 安全（`RATE_LIMITED` / `IP_BANNED`） |
| `2600–2608` | Schema 必填（`PARAM_REQUIRED` / `USERNAME_REQUIRED` 等） |
| `4000–9999` | 项目自定义（业务模块码必须从 `4000` 起，不得占用 `2xxx`）。HR 业务模块示例：`4000–4007` |

**每个失败场景分配唯一业务码**（追加到 `app/core/code.py` 末尾），避免反复 `Code.FAIL` 兜底。抛异常推荐 `raise BizError(code=Code.X, msg="...")`（任意层穿透）；`return Fail(...)` 仅在 api 层用；Schema 校验器用 `SchemaValidationError`（**不是** `ValueError`）。

完整响应码表见 `app/core/code.py` 或 [在线文档 / 响应码](https://sleep1223.github.io/fast-soy-admin-docs/backend/codes)。

## 强制约定清单（PR review checklist）

1. 必须用 `Success` / `SuccessExtra` / `Fail`；不要返回裸 dict、不要手拼 snake_case
2. 业务 schema 继承 `SchemaBase`；分页继承 `PageQueryBase`；ID 用 `SqidId`/`SqidPath`；整型用 `Int16/32/64`；Update schema 用 `make_optional`
3. 标准 6 路由必须 `CRUDRouter`；自定义用 `@crud.override`；不要绕过 `_OrderedRouter`
4. `controllers` / `services` 不要 import `fastapi.Request` / `Response`
5. 写接口必须挂按钮权限；业务角色种子必须显式 `data_scope`
6. 不要靠"前端隐藏按钮"做安全；不要在业务里直接判 `role_code == "..."`（用 `has_role_code` / `has_button_code`）
7. 模型继承 `BaseModel + AuditMixin`；文件头 `# pyright: reportIncompatibleVariableOverride=false`；字段加 `description="..."`；类 docstring 写中文名；`Meta.table = biz_<module>_<entity>`；**每个 `ForeignKeyField` / `OneToOneField` 上方显式声明 `<name>_id: int`（或 `int | None`）注解**；创建/更新/比较一律用 `obj.<name>_id`，访问关系对象字段必须先 `prefetch_related(...)` 或 `await obj.<name>`（否则循环里触发 N+1、或把未 prefetch 的关系对象直接赋给 FK 导致运行时错误）
8. 业务模块 import 入口统一 `from app.utils import ...`
9. 跨业务模块联动用事件总线（`emit` / `on`），不要直接 import 兄弟模块
10. 事务用 `in_transaction(get_db_conn(Model))`；**不要**硬编码连接名；事务内**不要**做 HTTP / Redis / 队列
11. 不要 `raise HTTPException`；用 `BizError` / `SchemaValidationError`
12. 业务自有缓存按 `<module>_<resource>:<scope>` 命名，读 → miss → 查 → 写 TTL，变更时主动失效；不要给分页接口加全局 `@cache(...)`
13. 关键节点 / 权限拒绝用 `radar_log(...)`；高频调试 `log.debug`；不要 `print(...)`
14. 所有函数加类型注解；`make check-all` 必须全绿（ruff + basedpyright + pytest + eslint + oxlint + vue-tsc）
15. `@crud.override` 内禁止出现 `in_transaction` / `request.app.state.redis` / 跨模型写 / 事件 / 审计——这些必须在 `services/` 实现，api 层只做参数转发与响应封装；override 数 ≥ 3 或资源是聚合根时，应改为显式 `@router.post(...)` + `services/`，不要硬塞 CRUDRouter

## 配置

- `.env` — `SECRET_KEY`、`DB_URL`、`REDIS_URL`、`CORS_ORIGINS`、`APP_DEBUG`、`JWT_*` 时间、`GUARD_*`、`PROXY_HEADERS_ENABLED`、`LOG_INFO_RETENTION`
- `ruff.toml` — 行宽 200，规则 E/F/I，双引号
- `pyproject.toml` 的 `[tool.basedpyright]` — `app/` 启用 standard 模式
- 前端 `.env` — `VITE_SERVICE_SUCCESS_CODE` / `VITE_SERVICE_LOGOUT_CODES` / `VITE_SERVICE_MODAL_LOGOUT_CODES` / `VITE_SERVICE_EXPIRED_TOKEN_CODES` / `VITE_OTHER_SERVICE_BASE_URL`

## 部署

Nginx 托管构建后的前端静态资源 + 反代 `/api/*` 到 FastAPI（:9999），Redis 提供缓存。编排在 `docker-compose.yml`，相关 Dockerfile / nginx.conf 在 `/deploy/`。

# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
