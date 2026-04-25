# FastSoyAdmin

FastSoyAdmin 是一套开箱即用的全栈后台管理模板。本文档是面向 LLM 的"单文件自包含上下文"，整合自 [在线文档站](https://sleep1223.github.io/fast-soy-admin-docs/)，用于快速建立项目全貌理解。

- **后端**：FastAPI · Pydantic v2 · Tortoise ORM · Redis · Argon2 · PyJWT · Sqids · Granian · fastapi-guard
- **前端**：Vue3 · Vite7 · TypeScript · Naive UI · Pinia · UnoCSS · Alova · Elegant Router · vue-i18n
- **基础设施**：Docker Compose（Nginx + FastAPI + Redis）· 多 worker 启动锁 · 内置 Radar 请求 / SQL / 异常 Dashboard

## 链接

- 源码：https://github.com/sleep1223/fast-soy-admin
- 在线预览：https://fast-soy-admin.sleep0.de/
- 文档站：https://sleep1223.github.io/fast-soy-admin-docs/
- API 文档（Apifox）：https://apifox.com/apidoc/shared-7cd78102-46eb-4701-88b1-3b49c006504b
- 前端上游：https://github.com/soybeanjs/soybean-admin
- 协议：MIT

---

## 1. 分支

| 分支 | 用途 |
|---|---|
| `main` | 默认分支，**带示例**（`app/business/hr/` 员工 / 部门 / 标签全套参考实现） |
| `slim` | 纯净模板骨架，不含业务示例模块（**即将提供**） |

未发布前如需无示例起步，直接删除 `app/business/hr/` 即可——`autodiscover` 下次启动自动跳过。

---

## 2. 快速开始

### 2.1 环境要求

| 工具 | 版本 |
|---|---|
| Git | — |
| Python | ≥ 3.12 |
| Node.js | ≥ 20.0.0 |
| uv | 最新 |
| pnpm | ≥ 10.5 |
| make | 任意 |

所有常用命令封装在根目录 `Makefile`，运行 `make` 或 `make help` 列出全部。

### 2.2 Docker 部署（推荐）

```bash
git clone https://github.com/sleep1223/fast-soy-admin
cd fast-soy-admin
make up                                                       # docker compose up -d
docker compose exec app uv run python -m app.cli initdb       # 首次必须手动建表 + 基础数据
docker compose restart app
```

启动三个容器：Nginx (`:1880` 反代 + 静态资源)、FastAPI (`:9999`)、Redis (`:6379`)。

**注意**：

- 启动时**不会**自动迁移；全新库必须 `initdb`，后续模型变更走 `migrate`。
- `initdb` 必须在容器里跑（容器使用 `.env.docker`，宿主机跑会写到宿主机 SQLite 文件）。
- 默认 `docker-compose.yml` **未给 SQLite 挂卷**——`down` / `--build` 会丢。生产要么切外部数据库，要么挂卷到 `app_system.sqlite3`。

### 2.3 本地开发

```bash
make install-all  # 后端 uv sync + 前端 pnpm install
make initdb       # 首次建表 + 基础数据（之后不再需要）
make dev          # 并行启动后端 :9999 + 前端 :9527，Ctrl+C 一起停
```

分别启动：`make run`（仅后端）/ `make web-dev`（仅前端）。

---

## 3. 顶层仓库结构

```
fast-soy-admin/
├── app/                       # 后端（FastAPI）
│   ├── __init__.py            # App 工厂、lifespan、多 worker init 协调
│   ├── core/                  # 框架基础设施（不含业务）
│   ├── system/                # 内置系统模块（auth / user / role / menu / api / dict / radar）
│   ├── business/              # 业务模块（autodiscover 自动加载）
│   │   └── hr/                #   参考实现：员工 / 部门 / 标签
│   ├── cli/                   # 代码生成器（init / gen / gen-web / initdb）
│   └── utils/                 # 业务开发者的统一 import 入口
├── web/                       # 前端（Vue3 + Vite）
│   ├── src/
│   │   ├── views/             # 页面组件（Elegant Router 源）
│   │   ├── service/api/       # Alova API 封装
│   │   ├── typings/api/       # TS 类型声明
│   │   ├── store/modules/     # Pinia 状态管理
│   │   ├── router/            # Elegant Router + 守卫
│   │   ├── layouts/           # 基础布局
│   │   ├── locales/           # vue-i18n（zh-CN / en-US）
│   │   ├── hooks/             # 组合式函数
│   │   └── theme/             # 主题设置
│   └── packages/              # 内部子包（alova / axios / hooks / utils / color / uno-preset）
├── deploy/                    # Docker 与 Nginx 配置
├── migrations/                # Tortoise ORM 迁移文件（按 DB app 分目录）
├── tests/                     # 后端 pytest
├── Makefile                   # 所有命令的统一入口
└── docker-compose.yml
```

---

## 4. 后端架构

### 4.1 包边界与依赖方向

| 包 | 职责 | 依赖方向 |
|---|---|---|
| `app/core/` | 框架基础设施 | 不依赖 system / business |
| `app/system/` | 内置系统模块（认证、RBAC、字典、监控） | 仅依赖 `app/core/` |
| `app/business/<x>/` | 业务模块 | 依赖 `app/utils`；**不得依赖兄弟业务模块**，不得反向依赖 `app.system.*`（少数显式暴露的 service 除外，如 `ensure_menu` / `ensure_role`） |
| `app/utils/` | 业务开发者对外稳定入口 | 重新导出 `app/core/*` 与少量 `app/system/*` 符号 |
| `app/cli/` | 代码生成器 | 离线使用，不进入运行时 |

跨业务模块联动通过[事件总线](#101-事件总线)解耦。

### 4.2 分层

```
HTTP Request
    │
    ▼
api/        ← FastAPI 路由：薄 HTTP 适配器，校验 + 调 service/controller + Success/Fail
    │
    ▼
services/   ← 多模型编排、事务、缓存、审计、事件、状态机
    │
    ▼
controllers/ ← CRUDBase 子类，单资源 CRUD + build_search
    │
    ▼
models / schemas
    Tortoise ORM 模型 + Pydantic Schema
```

| 层 | 写什么 | 不写什么 |
|---|---|---|
| `api/` | URL 接线、鉴权依赖、调 service/controller 的薄包装，返回 `Success` / `Fail` | 业务规则、跨模型、事务 |
| `services/` | 事务、多模型、Redis、状态机、审计、事件 | HTTP（Request / Response） |
| `controllers/` | `XxxController(CRUDBase)`、`build_search`；单模型 CRUD | 跨模型编排、事务、缓存、事件、外部 IO |
| `models/` | 表字段、索引、关系、Mixin | 业务校验 |
| `schemas/` | `XxxCreate` / `XxxUpdate` / `XxxSearch`，字段级校验 | 跨资源 |

### 4.3 请求生命周期

入站中间件（`app/core/middlewares.py` + `make_middlewares()`）：

1. `CORSMiddleware`
2. `PrettyErrorsMiddleware` — 异常输出美化
3. `BackgroundTaskMiddleware` — 把 FastAPI `BackgroundTasks` 注入 `CTX_BG_TASKS`
4. `RequestIDMiddleware` — 注入 `X-Request-ID` 到响应头与 `CTX_X_REQUEST_ID`
5. `RadarMiddleware`（条件启用）— 捕获请求 / SQL / 异常到 Radar Dashboard
6. `fastapi-guard`（条件启用）— 限流 / 自动封禁

路由分发：

- `/api/v1/auth/*` — 认证（公开）
- `/api/v1/route/*` — 路由元数据（constant-routes / user-routes）
- `/api/v1/system-manage/*` — 系统模块（用户 / 角色 / 菜单 / API / 字典）
- `/api/v1/business/<module>/*` — 业务模块（autodiscover 自动挂载）

依赖注入：

- `DependAuth` — JWT 解码 → 校验 token 版本号 → 加载用户与角色 / 按钮权限到 ContextVars
- `DependPermission` — 在 `DependAuth` 之上，按 `(method, path)` 精确比对 `role.apis`
- `require_buttons(...)` / `require_roles(...)` — 工厂依赖，按需挂在路由上

响应：一律返回 `Success` / `SuccessExtra` / `Fail`（`JSONResponse` 子类，自动 camelCase）。

### 4.4 启动生命周期

```
create_app()
  ├─ register_db(app)                # Tortoise.init(config=TORTOISE_ORM)
  ├─ register_exceptions(app)        # BizError / DoesNotExist / IntegrityError / ValidationError
  ├─ register_routers(app, prefix="/api")          # 系统模块
  ├─ discover_business_routers()     # /api/v1/business/<name>/...
  └─ setup_radar(app)                # 可选

lifespan(app)
  ├─ init_redis() → app.state.redis
  ├─ FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
  ├─ delete _INIT_LOCK_KEY / _INIT_DONE_KEY
  ├─ _run_init_data(app)             # 多 worker 中仅 leader 执行
  │    ├─ init_menus()               # 系统菜单种子（仅在 Menu 表为空时插入）
  │    ├─ refresh_api_list()         # FastAPI 路由 ↔ Api 表全量对账
  │    ├─ init_users()               # 系统角色 + 默认账号 + 字典
  │    ├─ for each business init():  # 业务模块 init_data.init()
  │    └─ refresh_all_cache()        # 角色权限 / 常量路由刷到 Redis
  ├─ startup_radar()                 # 可选
  └─ yield
       ↓ shutdown
  └─ close_redis()
```

### 4.5 多 worker 启动锁

生产环境通常 4 个 granian worker。启动时通过 Redis 分布式锁 `app:init_lock` 协调：

- Leader（`SET app:init_lock 1 NX EX 120` 成功者）执行完整 init，然后 `SET app:init_done 1 EX 120`
- 其他 worker 轮询 `app:init_done`，最长等 150s 后即使没等到也启动
- 每次进程启动前 leader 先 `DEL` 锁，因此每次重启都会真的跑一次 init

### 4.6 多数据库连接

- 默认所有模型挂在主连接 `conn_system`
- 业务模块在自己的 `config.py` 声明独立 `DB_URL` 时，autodiscover 会注册独立连接 `conn_<biz>` 与独立 app
- 跨模型事务用 `get_db_conn(Model)` 取连接名，**不要硬编码** `"conn_system"`

### 4.7 RBAC 数据模型

```
User ←M2M→ Role ←M2M→ Menu      (菜单权限：决定前端可见的路由)
                ←M2M→ Button    (按钮权限：决定页面内可执行的操作)
                ←M2M→ Api       (接口权限：决定可调用的后端接口)
                FK    Menu      (角色首页 by_role_home)
              field   data_scope (行级数据范围：all / department / self / custom)
```

- 超级管理员 `R_SUPER`（`app.core.constants.SUPER_ADMIN_ROLE`）跳过所有权限校验
- API 权限由 `refresh_api_list()` 自动维护（按 `(method, path)` 全量对账）
- 菜单 / 按钮由各模块 `init_data.py` 通过 `ensure_menu()` 声明，可选 `reconcile_menu_subtree()` 做 IaC 对账
- 按钮编码约定 `B_<MODULE>_<RESOURCE>_<ACTION>`（如 `B_HR_EMP_CREATE`）

### 4.8 行级数据权限（data_scope）

涉及行级权限的列表接口必须在 `@crud.override("list")` 内用 `build_scope_filter(scope, user_id, department_id, ...)` 拼查询。业务角色种子**必须显式声明** `data_scope`（`all` / `department` / `self` / `custom`），不要依赖默认（否则默认 `all` = 全可见）。

### 4.9 缓存模型

| 数据 | Redis Key | TTL | 谁写 |
|---|---|---|---|
| 常量路由 | `constant_routes` | 永久 | `refresh_all_cache` |
| 角色菜单 ID | `role:{code}:menus` | 永久 | `load_role_permissions` |
| 角色 API | `role:{code}:apis` | 永久 | 同上 |
| 角色按钮 | `role:{code}:buttons` | 永久 | 同上 |
| 角色数据范围 | `role:{code}:data_scope` | 永久 | 同上 |
| 用户角色 | `user:{uid}:roles` | 永久 | `load_user_roles` |
| 用户首页 | `user:{uid}:role_home` | 永久 | 同上 |
| Token 版本 | `token_version:{uid}` | 永久 | 修改密码 / 强制下线 |
| 业务自有缓存 | 按 `<module>_<resource>:<scope>` 自定义 | 模块自定 | 模块自定 |

---

## 5. API 约定

### 5.1 路由前缀

| 前缀 | 用途 |
|---|---|
| `/api/v1/auth` | 认证（公开） |
| `/api/v1/route` | 路由（constant-routes / user-routes） |
| `/api/v1/system-manage/*` | 系统模块（用户 / 角色 / 菜单 / API / 字典） |
| `/api/v1/business/<module>/*` | 业务模块 |

### 5.2 响应格式

```json
{ "code": "0000", "msg": "OK", "data": { ... } }
```

HTTP status 恒 200。字段命名一律 **camelCase**——`SchemaBase` 的 `alias_generator=to_camel_case` 自动处理；`Model.to_dict()` 同样输出 camelCase。**禁止**返回裸 dict、**禁止**手工拼 snake_case。

### 5.3 路径与方法

| 操作 | 方法 + 路径 | Body / Params |
|---|---|---|
| 列表 / 搜索 | `POST /resources/search` | Body 继承 `PageQueryBase` |
| 单条查询 | `GET /resources/{id}` | — |
| 创建 | `POST /resources` | Body: `XxxCreate` |
| 更新 | `PATCH /resources/{id}` | Body: `XxxUpdate` |
| 单条删除 | `DELETE /resources/{id}` | — |
| 批量删除 | `DELETE /resources` | Body: `CommonIds`（`{ids: [...]}`） |
| 子资源 | `GET/PATCH /resources/{id}/sub` | — |
| 派生查询 | `GET /resources/tree` / `/options` / `/pages` | — |
| 实例动作 | `POST /resources/{id}/action-name` | 视情况 |
| 集合动作 | `POST /resources/batch-offline` 等 | Body |

约束：

- **不要**带尾斜杠（`/users` ✅，`/users/` ❌）
- 多词路径 **kebab-case**（`/batch-offline`、`/constant-routes`、`/user-routes`）
- 资源名 **复数**（`/users`、`/roles`、`/departments`）
- "搜索"统一用 `POST /resources/search`，不要 `GET ?...=...`

### 5.4 分页

请求体继承 `PageQueryBase`：

| 字段 | 默认 | 说明 |
|---|---|---|
| `current` | `1` | 页码（≥ 1） |
| `size` | `10` | 每页数量（1–1000） |
| `orderBy` | `null` | 排序字段列表，`-` 前缀降序，例 `["-createdAt", "id"]` |

响应体：

```json
{ "code": "0000", "msg": "OK", "data": { "records": [...], "total": 42, "current": 1, "size": 10 } }
```

### 5.5 资源 ID 一律 sqid

对外 ID 都是 sqid 字符串（如 `Yc7vN3kE`），**不是**自增 int。Pydantic 用 `SqidId`，FastAPI 路径参数用 `SqidPath`：

```python
from app.utils import SqidId, SqidPath, SchemaBase

class DepartmentUpdate(SchemaBase):
    parent_id: SqidId | None = None          # body 字段

@router.get("/departments/{item_id}")
async def get_dept(item_id: SqidPath):       # 路径参数
    ...
```

- `SqidId`：校验时解码成 int，序列化时再编码回 sqid
- `SqidPath`：只解码、不参与序列化输出
- sqid 字母表由 `SECRET_KEY` 派生——轮换 SECRET_KEY 会使所有对外 sqid 链接失效

### 5.6 CRUDRouter — 不要手写样板路由

```python
from app.utils import CRUDRouter, SearchFieldConfig, require_buttons

dept_crud = CRUDRouter(
    prefix="/departments",
    controller=department_controller,
    create_schema=DepartmentCreate,
    update_schema=DepartmentUpdate,
    list_schema=DepartmentSearch,
    search_fields=SearchFieldConfig(
        contains_fields=["name", "code"],   # 模糊匹配
        exact_fields=["status"],            # 精确匹配
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

@dept_crud.override("list")                 # 自定义 list
async def _list(obj_in: DepartmentSearch):
    q = department_controller.build_search(obj_in, contains_fields=["name"])
    total, items = await department_controller.list(
        page=obj_in.current, page_size=obj_in.size, search=q, order=["-id"],
    )
    return SuccessExtra(
        data={"records": [await i.to_dict() for i in items]},
        total=total, current=obj_in.current, size=obj_in.size,
    )

router = dept_crud.router
```

- 可覆盖的 key：`list` / `get` / `create` / `update` / `remove` / `batch_remove`
- **不要**在 router 上重新声明同路径（会被 `_OrderedRouter` 排序后遮蔽）
- `_OrderedRouter` 每次 `add_api_route` 后自动把不含 `{...}` 的路径排到前面，避免 `GET /resources/{id}` 遮蔽 `GET /resources/tree`

标准 CRUD 之外的接口（如 `POST /warehouses/batch-offline`）直接写在 `router` 上，**不要**塞进 `CRUDRouter`。

#### 适用边界（避免抽象上瘾）

`CRUDRouter` 只服务**贫血资源**——字典、标签、部门、分类这种纯 CRUD 表。聚合根（用户、角色、订单、工单等带状态、带副作用的资源）**不要硬塞**。满足以下任一条件，立刻改写为显式 `@router.post(...)` + `services/`：

- override 数 ≥ 3（标准 6 路由覆盖一半，抽象已无收益）
- 任一 override 内出现 `in_transaction` / `redis` / 跨模型写
- 资源是聚合根或带状态机
- 写操作有副作用（发通知、写审计、触发事件、失效缓存）

**`@crud.override` 内禁止出现的内容**（必须下沉到 `services/`）：

- `in_transaction(...)` —— 事务编排是 service 的事
- `request.app.state.redis` / 任何 Redis 客户端调用
- 跨模型的 `create` / `update` / `delete`（含 `m2m.add` / `m2m.clear`）
- 调用其他模块的 service / 发事件 / 写审计

正确范式 —— override 只做"参数转发 + 包响应"，业务在 service 里：

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

参考实现：`app/system/api/users.py` + `app/system/services/user.py`、`app/system/api/apis.py` + `app/system/services/api.py`。

### 5.7 鉴权依赖

| 依赖 | 用途 |
|---|---|
| `DependAuth` | 仅 JWT 校验（登录态） |
| `DependPermission` | 在 `DependAuth` 之上按 `(method, path)` 校验 `role.apis`（业务接口默认挂在 router 上） |
| `require_buttons("B_X", ..., require_all=False)` | 任一通过（码 `2203`） |
| `require_buttons(..., require_all=True)` | 全部通过（码 `2202`） |
| `require_roles(...)` | 同上但针对角色（码 `2204` / `2205`） |

`R_SUPER` 自动跳过所有权限校验。

### 5.8 响应封装

| 类 | 用途 | 典型场景 |
|---|---|---|
| `Success(data=...)` | 单条 / 无分页 | get / create / update |
| `SuccessExtra(data={"records": [...]}, total, current, size)` | 分页 | list / search |
| `Fail(code=Code.X, msg="...")` | 业务失败 | 规则不通过 |
| `Custom(code, status_code, msg, data, **kwargs)` | 任意 | 极少数自定义 status_code 场景 |

OpenAPI 生成准确响应模型：在路由上加 `response_model=ResponseModel[UserOut]` 或 `PageResponseModel[UserOut]`。

### 5.9 关键端点速查

#### 认证（`/api/v1/auth`，公开）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/login` | 用户名密码登录 |
| POST | `/captcha` | 发送手机验证码 |
| POST | `/code-login` | 验证码登录 |
| POST | `/register` | 注册（默认角色 `R_USER`） |
| POST | `/refresh-token` | 刷新 access token |
| GET | `/user-info` | 当前用户信息 + 角色 + 按钮（`DependAuth`） |
| PATCH | `/password` | 修改密码（`DependAuth`，会递增 token 版本） |
| POST | `/impersonate/{user_id}` | 超级管理员模拟登录（`DependPermission` + 超管校验） |

#### 路由（`/api/v1/route`）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/constant-routes` | 公共路由（登录页 / 错误页等，从 Redis） |
| GET | `/user-routes` | 当前用户可见的菜单树（`DependAuth`） |
| GET | `/exists?name=xxx` | 校验路由名是否存在（`DependAuth`） |

#### 系统管理（`/api/v1/system-manage`，全部 `DependPermission`）

每个资源都遵循标准 6 路由：

| 资源 | 前缀 | 备注 |
|---|---|---|
| 用户 | `/users` | `create / update` 走 `@override` 注入密码哈希 + 角色关联 |
| 角色 | `/roles` | 含 `GET /roles/{id}/menus`、`PATCH /roles/{id}/menus` 等子资源 |
| 菜单 | `/menus` | 含 `GET /menus/tree`、`GET /menus/pages` |
| API | `/apis` | 含 `POST /apis/refresh`（手动触发对账） |
| 字典 | `/dictionaries` | 含 `GET /dictionaries/{type}/options`（带 5 分钟 Redis 缓存） |

---

## 6. 响应码

所有接口（含 200 / 4xx / 5xx）统一返回 `{"code": "xxxx", "msg": "...", "data": ...}`，HTTP 状态码恒为 200，业务结果由 `code` 字段承载。源码：`app/core/code.py`。

### 码段划分

| 码段 | 含义 |
|---|---|
| `0000` | 成功 |
| `1000–1999` | 系统内部错误（异常捕获、入参校验失败） |
| `2000–2999` | 框架内置业务错误（认证、授权、资源冲突、Schema 必填等） |
| `3000–3999` | 框架预留 |
| `4000–9999` | 项目 / 业务模块自定义码（业务模块码必须从 `4000` 起，**不得**占用 `2xxx`） |

### 1xxx — 系统内部错误

| 码 | 常量 | 说明 |
|---|---|---|
| `1000` | `INTERNAL_ERROR` | 通用 / 未处理异常 |
| `1100` | `INTEGRITY_ERROR` | 唯一键 / 外键约束冲突 |
| `1101` | `NOT_FOUND` | 记录不存在（`DoesNotExist`） |
| `1200` | `REQUEST_VALIDATION` | 请求参数 / 请求体校验失败（FastAPI 层） |
| `1201` | `RESPONSE_VALIDATION` | 响应序列化失败 |

`1200` 的 `data.errors` 每条形如 `{field, message, type}`，由 `_format_validation_error` 把 Pydantic v2 的英文错误翻译成中文。

### 21xx — 认证（前端有特殊处理）

| 码 | 常量 | 说明 | 前端行为 |
|---|---|---|---|
| `2100` | `INVALID_TOKEN` | Token 缺失 / 解码失败 / 格式无效 | 跳转登录 |
| `2101` | `INVALID_SESSION` | Token 类型错误 / 用户不存在 | 跳转登录 |
| `2102` | `ACCOUNT_DISABLED` | 用户账号已禁用 | 弹窗后登出 |
| `2103` | `TOKEN_EXPIRED` | access token 已过期 | 自动刷新 token |
| `2104` | `REFRESH_TOKEN_MISSING` | 刷新令牌缺失 | — |
| `2105` | `NOT_REFRESH_TOKEN` | 传入的不是刷新令牌 | — |
| `2106` | `SESSION_INVALIDATED` | `token_version` 已递增，旧 token 失效 | 跳转登录 |

前端 `.env`：`VITE_SERVICE_LOGOUT_CODES=2100,2101`、`VITE_SERVICE_MODAL_LOGOUT_CODES=2102`、`VITE_SERVICE_EXPIRED_TOKEN_CODES=2103`。

### 22xx — 授权

| 码 | 常量 | 说明 |
|---|---|---|
| `2200` | `API_DISABLED` | 接口被管理员禁用 |
| `2201` | `PERMISSION_DENIED` | RBAC 接口权限不足 |
| `2202` | `MISSING_BUTTON_PERMISSION` | `require_buttons(..., require_all=True)` 缺指定按钮 |
| `2203` | `NEED_ANY_BUTTON_PERMISSION` | `require_buttons(...)` 任一按钮都不持有 |
| `2204` | `MISSING_ROLE` | `require_roles(..., require_all=True)` 缺指定角色 |
| `2205` | `NEED_ANY_ROLE` | `require_roles(...)` 任一角色都不持有 |
| `2206` | `SUPER_ADMIN_ONLY` | 仅超级管理员可操作 |
| `2207` | `USER_NO_ROLE` | 用户未绑定任何角色 |

### 23xx — 资源冲突

| 码 | 常量 | 说明 |
|---|---|---|
| `2300` | `DUPLICATE_RESOURCE` | 通用资源重复（兜底） |
| `2301` | `DUPLICATE_ROLE_CODE` | 角色编码已存在 |
| `2302` | `DUPLICATE_USER_EMAIL` | 邮箱已注册 |
| `2303` | `DUPLICATE_USER_PHONE` | 手机号已注册 |
| `2304` | `DUPLICATE_USER_NAME` | 用户名已存在 |
| `2305` | `DUPLICATE_MENU_ROUTE` | 菜单路由路径已存在 |

### 24xx — 通用业务失败

| 码 | 常量 | 说明 |
|---|---|---|
| `2400` | `FAIL` | 未归类失败（**尽量避免**，新增场景请加专属码） |
| `2401` | `WRONG_CREDENTIALS` | 用户名或密码错误 |
| `2402` | `CAPTCHA_INVALID` | 验证码错误或已过期 |
| `2403` | `CAPTCHA_SEND_FAILED` | 验证码发送失败 |
| `2404` | `PHONE_NOT_REGISTERED` | 手机号未注册 |
| `2405` | `OLD_PASSWORD_WRONG` | 修改密码时原密码错误 |
| `2406` | `TARGET_USER_NOT_FOUND` | 操作目标用户不存在（如模拟登录） |

### 25xx — 限流 / 安全

| 码 | 常量 | 说明 |
|---|---|---|
| `2500` | `RATE_LIMITED` | 请求过于频繁 |
| `2501` | `IP_BANNED` | IP 已被临时封禁 |
| `2502` | `ACCESS_DENIED` | 被安全策略拦截 |

### 26xx — Schema 必填校验

| 码 | 常量 | 说明 |
|---|---|---|
| `2600` | `PARAM_REQUIRED` | 通用必填兜底 |
| `2601` | `USERNAME_REQUIRED` | 用户名不能为空 |
| `2602` | `PASSWORD_REQUIRED` | 密码不能为空 |
| `2603` | `USER_ROLE_REQUIRED` | 用户至少需要一个角色 |
| `2604–2608` | `USER_EMAIL_REQUIRED` / `ROLE_NAME_REQUIRED` / `ROLE_CODE_REQUIRED` / `ROUTE_NAME_REQUIRED` / `ROUTE_PATH_REQUIRED` | 对应字段必填 |

### 40xx — HR 业务（业务模块码示例）

| 码 | 常量 | 说明 |
|---|---|---|
| `4000` | `HR_DEPARTMENT_REQUIRED` | 超级管理员创建员工需指定部门 |
| `4001` | `HR_MANAGER_REQUIRED` | 仅部门主管可创建员工 |
| `4002` | `HR_CREATE_FORBIDDEN` | 无权限创建员工 |
| `4003` | `HR_TAGS_EXCEED_LIMIT` | 员工标签数量超出上限 |
| `4004` | `HR_EMPLOYEE_NOT_IN_DEPT` | 该员工不在当前主管部门中 |
| `4005` | `HR_USER_NOT_EMPLOYEE` | 当前用户未关联员工信息 |
| `4006` | `HR_MANAGER_ONLY` | 仅部门主管可执行此操作 |
| `4007` | `HR_INVALID_TRANSITION` | 不允许的状态流转 |

> 业务模块约定：业务码统一从 `4000` 起（不得占用 `2xxx` 系统段），在 `app/core/code.py` 末尾追加本模块的码段（如 `41xx`、`42xx`），**不要**反复 `Code.FAIL`。每个失败场景一个唯一码。

### 抛出方式

```python
from app.utils import BizError, Code, Fail

# 推荐：抛异常（能在任意层穿透）
raise BizError(code=Code.HR_INVALID_TRANSITION, msg="不允许从 'resigned' 转换为 'active'")

# 替代：返回 Fail（仅在 api 层用）
return Fail(code=Code.OLD_PASSWORD_WRONG, msg="原密码错误")
```

`SchemaValidationError`（继承 `BizError`）专用于 Pydantic 校验器中抛出：它**不**继承 `ValueError`，能直达全局处理器。

---

## 7. Schema 基类

`app/core/base_schema.py`：

- `SchemaBase` — Pydantic `BaseModel` 子类，`alias_generator=to_camel_case`、`validate_by_name=True`；业务 schema 一律继承
- `PageQueryBase(SchemaBase)` — 带 `current` / `size` / `orderBy` 的分页请求体
- `Success(data=...)` / `SuccessExtra(data, total, current, size)` / `Fail(code, msg, ...)` / `Custom(...)` — `JSONResponse` 子类
- `CommonIds(SchemaBase)` — `{ids: list[SqidId]}`，批量删除请求体
- `OfflineByRoleRequest` — 按角色下线
- `make_optional(model)` — 生成更新 schema 的工具（所有字段变 `Optional`）
- `ResponseModel[T]` / `PageResponseModel[T]` — 给 OpenAPI Swagger UI 用的响应模型

## 8. 模型基类

`app/core/base_model.py`：

- `BaseModel` — Tortoise Model 基类，主键 id、`to_dict()`（camelCase）、`__repr__` 等
- `AuditMixin` — `created_at` / `updated_at` / `created_by` / `updated_by`（自动捕获 `CTX_USER_ID`）
- `TreeMixin` — `parent_id` / `path` / `level`，树形结构工具
- `SoftDeleteMixin` — 透明的 `deleted_at IS NULL` 过滤
- `StatusType` — 枚举 `enable` / `disable`

字段约定：

- 继承 `BaseModel, AuditMixin`
- 文件头 `# pyright: reportIncompatibleVariableOverride=false`
- 字段必加 `description="..."`
- 类 docstring 写中文名（`"""仓库"""`）
- `Meta.table = "biz_<module>_<entity>"`
- 每个 `ForeignKeyField` / `OneToOneField` 上方显式声明 `<name>_id: int`（或 `int | None`）注解
- 创建 / 更新 / 比较一律用 `obj.<name>_id`；访问关系对象字段必须先 `prefetch_related(...)` 或 `await obj.<name>`

## 9. CRUDBase / CRUDRouter

`app/core/crud.py` 的 `CRUDBase`：泛型单资源 CRUD 入口，支持分页、`build_search`、`get_or_none`、软删除等。

```python
class WarehouseController(CRUDBase[Warehouse, WarehouseCreate, WarehouseUpdate]):
    pass

warehouse_controller = WarehouseController(model=Warehouse)
```

`build_search(obj_in, contains_fields=[...], exact_fields=[...])` 按 `PageQueryBase` 字段自动构造 Tortoise Q 过滤器：

- `contains_fields` — `name__icontains=value`
- `exact_fields` — `status=value`
- 空 / None / 空列表自动跳过

`get_db_conn(Model)` 自动返回该模型所在的连接名（`conn_system` 或 `conn_<biz>`）。事务：

```python
from tortoise.transactions import in_transaction
from app.utils import get_db_conn

async with in_transaction(get_db_conn(Invoice)):
    await Invoice.create(...)
```

**事务内禁止 HTTP / Redis / 队列**。

---

## 10. Core 机制

### 10.1 事件总线

`app/core/events.py` 提供进程内事件总线 `emit(event_name, **kwargs)` / `@on(event_name)`，用于业务模块之间**解耦通信**。业务模块**不得**直接 import 兄弟模块；跨模块联动走事件。

### 10.2 状态机

`app/core/state_machine.py` 提供轻量状态机：声明允许的 state transitions，业务代码调 `transition.can(from, to)` 或直接 `transition.assert(from, to)`，非法状态流转抛 `BizError`。

### 10.3 Sqids

`app/core/sqids.py`：

- `encode_id(int) -> str` / `decode_id(str) -> int`
- `SqidId` — Pydantic 类型，body 字段用
- `SqidPath` — FastAPI 路径参数用

字母表由 `SECRET_KEY` 派生——轮换 SECRET_KEY 会使所有外部 sqid 链接失效。详见 FAQ。

### 10.4 BizError / 异常

`app/core/exceptions.py`：

- `BizError(code, msg)` — 业务异常，全局处理器捕获转成 `Fail`
- `SchemaValidationError(BizError)` — 专用于 Pydantic 校验器（不继承 `ValueError`）
- 全局处理器覆盖 `BizError` / `DoesNotExist` / `IntegrityError` / `ValidationError`

**不要** `raise HTTPException`；用 `BizError` / `SchemaValidationError`。

### 10.5 ContextVars

`app/core/ctx.py`：

- `CTX_USER_ID` — 当前请求用户 ID
- `CTX_ROLE_CODES` — 当前用户角色码集合
- `CTX_BUTTON_CODES` — 当前用户按钮码集合
- `CTX_X_REQUEST_ID` — 请求 ID（由中间件注入）
- `CTX_BG_TASKS` — 后台任务队列

`AuditMixin` 的 `created_by` / `updated_by` 自动从 `CTX_USER_ID` 取值。

### 10.6 Autodiscover

`app/core/autodiscover.py` 启动时扫描 `app/business/*`：

| 约定 | 提供的能力 |
|---|---|
| `app/business/<name>/models.py` 或 `models/` | Tortoise 模型 → 注册到 `TORTOISE_ORM["apps"]` |
| `app/business/<name>/api/` 或 `api.py` | 必须导出 `router: APIRouter` → 挂载到 `/api/v1/business/<name>/*` |
| `app/business/<name>/init_data.py` | 可选 `async def init()` → 系统初始化后、缓存刷新前执行 |
| `app/business/<name>/config.py` 中声明 `DB_URL` | 注册独立连接 `conn_<name>` 与独立 app |

临时屏蔽某模块：`mv app/business/xxx app/business/_xxx`（`_` 前缀目录会被跳过）。

### 10.7 Radar 内置监控

`app/system/radar/` 是参考 fastapi-radar 实现的内置 Dashboard，路径 `/manage/radar/*`：记录请求、SQL、异常、审计埋点。启用通过配置项开关。关键埋点 / 权限拒绝用 `radar_log(...)`；高频调试用 `log.debug`；**不要** `print(...)`。

### 10.8 密码 & JWT

- 密码哈希：Argon2（`app/system/security.py`）
- JWT：HS256，access 12h，refresh 7d
- Token 版本号：Redis `token_version:{uid}`，修改密码 / 模拟登录时 `INCR`，旧 token 在下一次请求返回 `2106 SESSION_INVALIDATED`

---

## 11. 业务模块开发

### 11.1 目录约定

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

### 11.2 新增模块流程

```bash
make cli-init MOD=inventory                       # 1. 生成骨架（仅 models.py）
$EDITOR app/business/inventory/models.py          # 2. 定义 Tortoise 模型
make cli-gen-all MOD=inventory CN=库存管理        # 3. 同时生成后端 + 前端 CRUD
# 4. 合并 web/src/locales/langs/_generated/inventory/ 的 3 个 .md 片段到对应源文件
# 5. 处理前端外键 / 自定义枚举的 TODO（options 数据源）
make mm                                           # 6. 迁移
make dev                                          # 7. 启动验证
make check-all                                    # 8. 提交前
```

### 11.3 启动时初始化与对账

启动由 Redis leader worker 执行：`init_menus()` → `refresh_api_list()` → `init_users()` → 依次调用各业务模块的 `init_data.init()` → `refresh_all_cache()`。

**不同数据类型的同步语义：**

| 类型 | 同步方式 | 改字段 | 新增 | 删除 | 重命名 |
|---|---|---|---|---|---|
| **API** | `refresh_api_list()` 全量对账 | ✅ | ✅ | ✅ | ✅（删旧建新） |
| **菜单 / 按钮** | `ensure_menu()` upsert + 可选 `reconcile_menu_subtree()` | ✅ | ✅ | ⚠️ 需启用对账 | ⚠️ 需启用对账 |
| **角色** | `ensure_role()` upsert；`menus / buttons / apis` clear-and-readd | ✅ | ✅ | ❌ 走迁移 | ❌ 走迁移 |
| **业务种子数据** | `_safe_update_or_create` 按唯一键 | ✅ | ✅ | ❌ 走迁移 | ❌ 走迁移 |

**关键约定**：

- **漂移告警**：`ensure_role` 引用的 `route_name` / `button_code` / `(method, path)` 无法解析时会 `log.warning`——务必立即修复，否则角色权限会静默缺失
- **IaC 模式**：一旦对某子树启用 `reconcile_menu_subtree()`，该子树成为单一数据源，通过 Web UI 手工创建在该子树下的菜单 / 按钮会在下次重启时被清除
- 需要允许用户动态创建菜单的子树，**不要**对它调用 `reconcile_menu_subtree()`

### 11.4 init_data.py 示例

```python
from app.system.services import ensure_menu, ensure_role, reconcile_menu_subtree

INVENTORY_MENU_CHILDREN = [
    {
        "menu_name": "仓库管理",
        "route_name": "inventory_warehouse",
        "route_path": "/inventory/warehouse",
        "component": "view.inventory_warehouse",
        "icon": "mdi:warehouse",
        "order": 1,
        "buttons": [
            {"button_code": "B_INV_CREATE", "button_desc": "创建仓库"},
        ],
    },
]

INVENTORY_ROLE_SEEDS = [
    {
        "role_name": "库存管理员",
        "role_code": "R_INV_MGR",
        "data_scope": DataScopeType.department,     # ← 必须显式
        "menus": ["home", "inventory", "inventory_warehouse"],
        "buttons": ["B_INV_CREATE"],
        "apis": [
            ("post", "/api/v1/business/inventory/warehouses"),
            ("post", "/api/v1/business/inventory/warehouses/search"),
        ],
    }
]


async def init():
    await ensure_menu(
        menu_name="库存管理",
        route_name="inventory",
        route_path="/inventory",
        icon="mdi:package-variant",
        order=9,
        children=INVENTORY_MENU_CHILDREN,
    )
    await reconcile_menu_subtree(
        root_route="inventory",
        declared_route_names={"inventory_warehouse"},
        declared_button_codes={"B_INV_CREATE"},
    )
    for role in INVENTORY_ROLE_SEEDS:
        await ensure_role(**role)
```

### 11.5 删除模块

直接删除 `app/business/<module>/` 整个目录即可，autodiscover 下次启动自动跳过。

> 数据库表**不会**被 Tortoise 自动删除。如需清理，手动 `DROP TABLE` 或写一次迁移。

---

## 12. CLI 代码生成

| Make 命令 | 作用 |
|---|---|
| `make cli-init MOD=xxx` | 创建业务模块骨架（只含 `models.py`） |
| `make cli-gen MOD=xxx` | 解析 `models.py`，生成后端 schemas / controllers / api / init_data / services |
| `make cli-gen-web MOD=xxx CN=中文名` | 解析 `models.py`，生成前端 service / typings / views / i18n 片段 |
| `make cli-gen-all MOD=xxx CN=中文名` | 一次跑完 cli-gen + cli-gen-web |

### 12.1 字段类型映射

| Tortoise 字段 | TS 类型 | 后端 schema | 前端表单 | 前端搜索 |
|---|---|---|---|---|
| `CharField` | `string` | `str` | `NInput` | `NInput` |
| `TextField` | `string` | `str` | `NInput type="textarea"` | `NInput` |
| `IntField` / `BigIntField` | `number` | `int` | `NInputNumber` | `NInputNumber` |
| `DecimalField` / `FloatField` | `number` | `Decimal` / `float` | `NInputNumber :precision="2"` | 跳过 |
| `BooleanField` | `boolean` | `bool` | `NSwitch` | — |
| `DateField` | `string` | `date` | `NDatePicker type="date"` | — |
| `DatetimeField` | `string` | `datetime` | `NDatePicker type="datetime"` | — |
| `CharEnumField(StatusType)` | `string` | `StatusType` | `NSelect statusTypeOptions` | 同左 |
| `CharEnumField(其他枚举)` | `string` | `str` | `NSelect` + TODO | 同左 |
| `ForeignKeyField` | `number` | `int` | `NSelect` + TODO | 同左 |

### 12.2 i18n 命名

- **模块中文名**：`init` 命令时输入，用于 `route.<module>` 和 `page.<module>` 顶层
- **模型中文名**：类 docstring（`"""仓库"""`）或 `Meta.table_description`
- **字段中文名**：`description="..."`，截断到第一个中英文句号之前
  - `description="仓库编号。全局唯一"` → 取 `仓库编号`
  - 空 / 未填 → fallback 为字段名本身

### 12.3 i18n 片段合并

生成物用 `.md` 扩展名、**不会**被 pnpm 构建直接加载，需要手动合并：

| 生成文件 | 合并到 | 合并到哪段 |
|---|---|---|
| `_generated/<mod>/zh-cn.md` | `web/src/locales/langs/zh-cn.ts` | `route` / `page` 对象 |
| `_generated/<mod>/en-us.md` | `web/src/locales/langs/en-us.ts` | `route` / `page` 对象 |
| `_generated/<mod>/app.d.ts.md` | `web/src/typings/app.d.ts` | `App.I18n.Schema.page` 子树 |

⚠️ **必须合并 `app.d.ts.md`**——不合并会导致 `$t('page.xxx...')` 编译报错。`route` 命名空间由 Elegant Router 自动补齐，不需要手动改类型。

---

## 13. 前端架构

### 13.1 技术栈

| 技术 | 版本 | 用途 |
|---|---|---|
| Vue | 3.5 | UI 框架 |
| Vite | 7 | 构建 |
| TypeScript | 5.9 | 类型 |
| Naive UI | 2.44 | 组件库 |
| Pinia | 3 | 状态管理 |
| UnoCSS | 66+ | 原子化 CSS |
| Alova | — | HTTP 客户端 |
| vue-router | 4 | 动态路由 |
| vue-i18n | 11 | 国际化 |
| Elegant Router | — | 由 `views/` 目录自动生成路由 |
| unplugin-icons | — | 按需注册图标 |

### 13.2 与后端的关系

前端**不**自己定义权限、不自己定义可见路由——这两类数据由后端按角色下发：

| 数据 | 来源 |
|---|---|
| 当前用户的角色 / 按钮权限 | `GET /api/v1/auth/user-info` |
| 公共路由（登录 / 错误页等） | `GET /api/v1/route/constant-routes` |
| 当前用户能看到的菜单树 | `GET /api/v1/route/user-routes` |
| 字典选项 | `GET /api/v1/system-manage/dictionaries/{type}/options` |

### 13.3 错误码映射

前端 `.env`：

| 变量 | 默认值 | 行为 |
|---|---|---|
| `VITE_SERVICE_SUCCESS_CODE` | `0000` | 视为成功，提取 `data` |
| `VITE_SERVICE_LOGOUT_CODES` | `2100,2101` | 直接登出 |
| `VITE_SERVICE_MODAL_LOGOUT_CODES` | `2102` | 弹窗提示后登出 |
| `VITE_SERVICE_EXPIRED_TOKEN_CODES` | `2103` | 自动用 refresh token 刷新并重试 |
| 其他 | — | 显示 `msg` 错误消息 |

### 13.4 关键 Hooks

- `useNaivePaginatedTable` — 表格数据（搜索 / 分页 / 加载态一体）
- `useTableOperate` — 表格 CRUD 操作
- `useRouterPush` — 路由跳转（带类型补全）
- `hasAuth` — 按钮权限判断

---

## 14. 切换数据库

`DB_URL` 在根目录 `.env`：

```dotenv
# SQLite（默认）
DB_URL="sqlite://app_system.sqlite3?busy_timeout=5000"

# PostgreSQL（默认驱动 asyncpg）
DB_URL="postgres://user:password@localhost:5432/fastsoyadmin"

# MySQL / MariaDB
DB_URL="mysql://root:password@localhost:3306/fastsoyadmin"

# SQL Server
DB_URL="mssql://sa:Password123@localhost:1433/fastsoyadmin?driver=ODBC%20Driver%2018%20for%20SQL%20Server&encrypt=no&trust_server_certificate=yes"
```

URL 语法速查：

| 引擎 | URL 示例 | 说明 |
|---|---|---|
| SQLite（相对路径） | `sqlite://app_system.sqlite3?busy_timeout=5000` | **两个斜杠**，相对项目根 |
| SQLite（绝对路径） | `sqlite:///var/data/db.sqlite3?journal_mode=WAL` | **三个斜杠**，后接绝对路径 |
| PostgreSQL | `postgres://user:pwd@host:5432/db` | 默认 asyncpg |
| MySQL | `mysql://user:pwd@host:3306/db` | 需 `aiomysql` 或 `asyncmy` |
| SQL Server | `mssql://sa:pwd@host:1433/db?driver=ODBC...` | 需 ODBC 驱动 |

驱动安装：`uv add asyncpg` / `uv add asyncmy` / `uv add asyncodbc`。

### 业务模块独立数据库

```python
# app/business/billing/config.py
from pydantic_settings import BaseSettings


class BillingSettings(BaseSettings):
    DB_URL: str = "postgres://user:pwd@billing-host:5432/billing"
    model_config = {"env_file": ".env", "extra": "ignore", "env_prefix": "BILLING_"}


BIZ_SETTINGS = BillingSettings()
```

autodiscover 发现 `DB_URL` 不同于主库时，在 `TORTOISE_ORM` 注册连接 `conn_billing` 并把该模块模型挂到新 app `billing` 下；相同则合并到默认连接。跨模型事务：

```python
async with in_transaction(get_db_conn(Invoice)):
    await Invoice.create(...)
```

每个连接有独立迁移目录：`migrations/app_system/` / `migrations/billing/`。

### 常见坑

- **连接池**：`postgres://...?maxsize=50&minsize=5`
- **SQLite 并发写**：`sqlite:///data/app.sqlite3?journal_mode=WAL&busy_timeout=5000`
- **时区**：Tortoise `use_tz=False, timezone=Asia/Shanghai`（默认）；PostgreSQL 建议 `use_tz=True` 并统一 UTC

---

## 15. 部署

### 15.1 Docker Compose（推荐）

```bash
git clone https://github.com/sleep1223/fast-soy-admin
cd fast-soy-admin
docker compose up -d
```

| 服务 | 端口 | 说明 |
|---|---|---|
| nginx | 1880 | 前端 + API 反向代理 |
| app | 9999 | FastAPI 后端 |
| redis | 6379 | 缓存层 |

### 15.2 日志

```bash
docker compose logs -f          # 所有服务
docker compose logs -f app      # 仅后端
make logs                       # == docker compose logs -f
```

### 15.3 首次部署（initdb）

`make up` **不会自动建表**。新库首次启动后端会报 `no such table: ...`——这是预期行为：

```bash
make up                                                       # 起容器
docker compose exec app uv run python -m app.cli initdb       # 建表 + 写入基础数据
docker compose restart app                                    # 让后端重连到已建好的库
```

注意：

- **`initdb` 必须在容器里跑**，不能在宿主机（宿主机会写到宿主机本地 `app_system.sqlite3`，和容器里是两个文件）
- `initdb` 只能在**全新库**上跑一次；之后任何模型变更一律走 `migrate`
- 判断该 `initdb` 还是 `migrate`：`docker compose exec app uv run tortoise history`——报错 / 无输出 → 空库跑 initdb；有历史但不是最新 → 跑 migrate

### 15.4 日常模型变更

推荐流程：**本地生成迁移、提交 git、服务器重建并执行**。

```bash
# --- 本地 ---
make makemigrations                 # 生成 migrations/models/*.py
git add migrations/ app/
git commit -m "feat(xxx): ..."
git push

# --- 服务器 ---
git pull
docker compose up -d --build app    # 重建包含新代码 + 新迁移文件的镜像
docker compose exec app uv run tortoise migrate
docker compose exec app uv run tortoise history   # 确认迁移已应用
```

为什么不在容器里 `makemigrations`：容器内生成的迁移文件在 `docker compose down` 后会随容器销毁，且不会回流到 git。**迁移文件属于代码，必须在本地生成并入库。**

### 15.5 业务模块 `init_data.init()`

不是迁移——是**每次启动由 Redis leader worker 自动执行**的幂等对账（菜单 / 角色 / API / 业务种子数据）。

- 新增业务模块 / 修改 `init_data.py` 后，`docker compose up -d --build` 即可，**不需要**手动触发
- 但表结构变更仍要先 `migrate`，`init_data` 依赖表已存在

### 15.6 数据持久化前置检查

默认 `docker-compose.yml` 仅声明 `redis_data` / `static_data` 两个卷，**SQLite 文件没挂卷**（位于容器内 `/opt/fast-soy-admin/app_system.sqlite3`），`docker compose down` 或 `--build` 重建后会丢。生产二选一：

- **切外部数据库**：把 `.env.docker` 里 `DB_URL` 指向外部 Postgres / MySQL
- **给 SQLite 挂卷**：在 `app` 服务下加 `- sqlite_data:/opt/fast-soy-admin/db`，把 `file_path` 改成 `db/app_system.sqlite3`

### 15.7 回滚

Tortoise 的 `downgrade` 对 SQLite 支持有限，生产回滚推荐：

1. 从备份恢复数据库文件 / 快照
2. `git revert` 对应的代码 + 迁移提交
3. `docker compose up -d --build`

**不要**在生产用 `tortoise downgrade` 回滚结构变更。

### 15.8 手动部署

```bash
# 后端
uv sync --no-dev
uvicorn app:app --host 0.0.0.0 --port 9999 --workers 4

# 前端
cd web && pnpm install && pnpm build
# dist/ 部署到 Web 服务器
```

Nginx 示例：

```nginx
server {
    listen 80;
    root /path/to/web/dist;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:9999;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 16. 命令参考（Make）

### 后端

| Make 命令 | 作用 |
|---|---|
| `make install` | 安装后端依赖（`uv sync`） |
| `make run` | 启动后端（:9999） |
| `make lint` | Ruff 检查（不修改） |
| `make fmt` | Ruff fix + format |
| `make typecheck` | basedpyright |
| `make test` | pytest |
| `make check` | fmt + typecheck + test |

### 数据库

| Make 命令 | 作用 |
|---|---|
| `make initdb` | 首次初始化数据库（建表 + 基础数据） |
| `make makemigrations` | 生成迁移文件 |
| `make migrate` | 应用所有未执行的迁移 |
| `make mm` | makemigrations + migrate |
| `make dbhistory` | 迁移历史 |

### CLI 代码生成

| Make 命令 | 作用 |
|---|---|
| `make cli-init MOD=xxx` | 创建业务模块骨架（只含 `models.py`） |
| `make cli-gen MOD=xxx` | 生成后端 schemas / controllers / api / init_data / services |
| `make cli-gen-web MOD=xxx CN=中文名` | 生成前端 service / typings / views / i18n 片段 |
| `make cli-gen-all MOD=xxx CN=中文名` | cli-gen + cli-gen-web |

### 前端

| Make 命令 | 作用 |
|---|---|
| `make web-install` | 安装前端依赖 |
| `make web-dev` | 启动前端（:9527） |
| `make web-build` | 生产构建 |
| `make web-lint` | ESLint + oxlint |
| `make web-typecheck` | vue-tsc |
| `make web-check` | web-lint + web-typecheck |

### 全栈

| Make 命令 | 作用 |
|---|---|
| `make install-all` | 同时安装后端 + 前端依赖 |
| `make dev` | 同时启动后端（:9999）和前端（:9527） |
| `make check-all` | 后端 + 前端全部质量检查（提交前必跑） |

### Docker

| Make 命令 | 作用 |
|---|---|
| `make up` | `docker compose up -d` |
| `make rebuild` | `docker compose up -d --build` |
| `make down` | 停止并移除容器 |
| `make logs` | 实时查看日志 |

---

## 17. 强制约定清单（PR review checklist）

1. 必须用 `Success` / `SuccessExtra` / `Fail`；不要返回裸 dict、不要手拼 snake_case
2. 业务 schema 继承 `SchemaBase`；分页继承 `PageQueryBase`；ID 用 `SqidId` / `SqidPath`；整型用 `Int16 / 32 / 64`；Update schema 用 `make_optional`
3. 标准 6 路由必须 `CRUDRouter`；自定义用 `@crud.override`；不要绕过 `_OrderedRouter`
4. `controllers` / `services` 不要 import `fastapi.Request` / `Response`
5. 写接口必须挂按钮权限；业务角色种子必须**显式** `data_scope`
6. 不要靠"前端隐藏按钮"做安全；不要在业务里直接判 `role_code == "..."`（用 `has_role_code` / `has_button_code`）
7. 模型继承 `BaseModel + AuditMixin`；文件头 `# pyright: reportIncompatibleVariableOverride=false`；字段加 `description="..."`；类 docstring 写中文名；`Meta.table = biz_<module>_<entity>`；每个 `ForeignKeyField` / `OneToOneField` 上方显式声明 `<name>_id: int`（或 `int | None`）注解；创建 / 更新 / 比较一律用 `obj.<name>_id`
8. 业务模块 import 入口统一 `from app.utils import ...`
9. 跨业务模块联动用事件总线（`emit` / `on`），不要直接 import 兄弟模块
10. 事务用 `in_transaction(get_db_conn(Model))`；**不要**硬编码连接名；事务内**不要**做 HTTP / Redis / 队列
11. 不要 `raise HTTPException`；用 `BizError` / `SchemaValidationError`
12. 业务自有缓存按 `<module>_<resource>:<scope>` 命名，读 → miss → 查 → 写 TTL，变更时主动失效；不要给分页接口加全局 `@cache(...)`
13. 关键节点 / 权限拒绝用 `radar_log(...)`；高频调试 `log.debug`；不要 `print(...)`
14. 所有函数加类型注解；`make check-all` 必须全绿（ruff + basedpyright + pytest + eslint + oxlint + vue-tsc）
15. `@crud.override` 内禁止出现 `in_transaction` / `request.app.state.redis` / 跨模型写 / 事件 / 审计——这些必须在 `services/` 实现，api 层只做参数转发与响应封装；override 数 ≥ 3 或资源是聚合根时，应改为显式 `@router.post(...)` + `services/`，不要硬塞 CRUDRouter

---

## 18. 配置

### 18.1 后端 `.env`

- `SECRET_KEY` — JWT + Sqids 字母表派生
- `DB_URL` — 数据库连接
- `REDIS_URL` — Redis 连接
- `CORS_ORIGINS` — CORS 白名单
- `APP_DEBUG` — 开启则返回详细异常栈
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` / `JWT_REFRESH_TOKEN_EXPIRE_DAYS`
- `GUARD_ENABLED` / `GUARD_*` — fastapi-guard 配置
- `PROXY_HEADERS_ENABLED` / `TRUSTED_HOSTS` — 反代头还原
- `LOG_INFO_RETENTION` — 日志保留

`.env.docker` 同上，变量为容器视角（`DB_URL` 默认 SQLite、`REDIS_URL=redis://redis:6379/0`）。

### 18.2 前端 `.env`

- `VITE_SERVICE_BASE_URL` — API 根路径
- `VITE_SERVICE_SUCCESS_CODE` / `VITE_SERVICE_LOGOUT_CODES` / `VITE_SERVICE_MODAL_LOGOUT_CODES` / `VITE_SERVICE_EXPIRED_TOKEN_CODES`
- `VITE_OTHER_SERVICE_BASE_URL` — 可选附加后端
- `VITE_AUTH_ROUTE_MODE` — `static` / `dynamic`（默认 `dynamic`）

### 18.3 工具链配置

- `ruff.toml` — 行宽 200，规则 E / F / I，双引号
- `pyproject.toml` 的 `[tool.basedpyright]` — `app/` 启用 standard 模式
- 前端：`@soybeanjs/eslint-config-vue` + oxlint + vue-tsc

---

## 19. FAQ（浓缩版）

### 启动 & 安装

- **`python run.py` 报 "no such table"**：首次必须 `make initdb`（或 `make mm`）。启动不会自动建表。
- **Redis 连接失败**：`redis-cli ping` 应返回 `PONG`。临时用本地：`REDIS_URL=redis://localhost:6379/0`。
- **端口被占用**：后端 9999 / 前端 9527 / Nginx 1880。改 `run.py` 或 `web/vite.config.ts`。

### 模块开发

- **重启后我手动建的菜单 / 按钮被清掉了**：`init_data.py` 调了 `reconcile_menu_subtree(...)`——该子树进入 IaC 模式，只接受声明式菜单。想允许动态创建就不要对该子树调 reconcile。
- **启动日志报 `ensure_role 'XXX': missing apis [...]`**：声明的 `(method, path)` 在 `Api` 表里找不到。通常是路由被改了或拼错（method 必须小写）。看到必须修。
- **删了 init_data 里的角色，DB 中的 Role 还在**：`ensure_role` 是 upsert，不会自动删；删除走数据库迁移。
- **业务模块新加的但路由没挂**：检查 `api/__init__.py` 是否导出 `router: APIRouter`。
- **临时屏蔽某个业务模块**：`mv app/business/inventory app/business/_inventory`。
- **CLI 生成的代码里 `// TODO`**：外键 / 自定义枚举的下拉数据源无法自动推导，搜 TODO 补齐 `fetchGetXxxList`。

### 权限

- **改了角色 / 菜单后用户没刷出权限**：权限走 Redis 缓存，CUD 后主动 `load_role_permissions` / `load_user_roles`，或直接重启。
- **用户被踢但 token 还能用**：调 `invalidate_user_session(redis, user_id)`，会 `INCR token_version:{uid}`，旧 token 下次请求返 `2106`。
- **业务接口权限拒绝（`2201`）但角色已挂菜单**：菜单和 API 是两个维度，角色 seed 必须同时给 `menus` 和 `apis`。
- **部门主管看到了全公司的数据**：`data_scope` 没显式声明（默认 `all`）。种子里必须显式 `DataScopeType.department`。

### 前端路由

- **修改 `.env` 不生效**：重启 Vite dev server。
- **路由不在菜单中显示**：检查 `hide_in_menu=True`，或后端没给当前角色加这个 `route_name`。
- **静态 vs 动态路由**：`VITE_AUTH_ROUTE_MODE=static`（前端自定义）/`dynamic`（默认，调 `/api/v1/route/user-routes`）。
- **生产 404**：Nginx 配 `try_files $uri $uri/ /index.html;`。

### API ID

- **前端拿到字符串 `Yc7vN3kE` 不是数字**：那是 sqid，对外 ID 一律 sqid。前端原样发回后端即可（`SqidPath` / `SqidId` 自动解码）。
- **测试里发数字 ID 也通过了？**：兼容期允许——`SqidId._sqid_to_int` 同时接受 int / 数字字符串 / sqid。迁移完成后可收紧。
- **部署后所有外部 sqid 链接都失效**：`SECRET_KEY` 被换了（sqid 字母表由 SECRET_KEY 派生）。

### 部署

- **容器里所有请求都被 guard 误封**：部署在 Nginx 后没开反代头还原。加 `PROXY_HEADERS_ENABLED=true` 和 `TRUSTED_HOSTS=["10.0.0.0/8"]`。
- **切换数据库后启动报 "module not found: asyncpg"**：主库引擎没装对应驱动，`uv add asyncpg / asyncmy / asyncodbc`。
- **多 worker 启动后菜单 / 用户重复创建？**：不会。`_run_init_data` 通过 Redis 锁 `app:init_lock` 选 leader，只有 leader 跑 init。
- **容器内时区不对**：Tortoise 默认 `use_tz=False, timezone=Asia/Shanghai`。改成 UTC 需在 `app/core/config.py` 改 `TORTOISE_ORM["use_tz"]=True` 并 `timezone="UTC"`。

---

## 20. 规范速查

| 类型 | 规则 |
|---|---|
| 文件名 | snake_case（如 `user_service.py`、`employee_search.vue`） |
| 类 / 枚举 | PascalCase |
| 函数 / 变量 | snake_case（Python） / camelCase（TS） |
| URL 路径 | 资源名复数、kebab-case（`/batch-offline`） |
| 角色码 | `R_<MODULE>_<ROLE>`（如 `R_HR_ADMIN`） |
| 按钮码 | `B_<MODULE>_<RESOURCE>_<ACTION>`（如 `B_HR_EMP_CREATE`） |
| 事件名 | `<domain>.<entity>.<action>`（如 `hr.employee.created`） |
| 路由名 | 后端 `ensure_menu` 的 `route_name`，全局唯一（如 `hr_employee`） |
| 前端 view 组件 | `view.<route_name>`（如 `view.hr_employee`） |
| DB 表 | 业务表 `biz_<module>_<entity>`；系统表沿用 `user` / `role` 等 |
| 业务缓存 Key | `<module>_<resource>:<scope>` |

---

## 21. 前端代码同步说明

`web/` 目录源码由独立仓库 [fast-soy-admin-frontend](https://github.com/sleep1223/fast-soy-admin-frontend) 维护，与本仓库**没有共同祖先**。同步上游更新需手动走 `git subtree` 流程。历史可查：`git log --oneline --grep="chore(web): sync with fast-soy-admin-frontend"`。
