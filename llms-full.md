# FastSoyAdmin

FastSoyAdmin 是一套开箱即用的全栈后台管理模板。

- **后端**：FastAPI · Pydantic v2 · Tortoise ORM · Redis · Argon2 · PyJWT · Sqids · Granian
- **前端**：Vue3 · Vite7 · TypeScript · Naive UI · Pinia · UnoCSS · Alova · Elegant Router
- **基础设施**：Docker Compose (Nginx + FastAPI + Redis)、多 worker 启动锁、fastapi-guard 限流、内置 Radar 监控面板

相关链接：

- 源码：https://github.com/sleep1223/fast-soy-admin
- 在线预览：https://fast-soy-admin.sleep0.de/
- 文档站：https://sleep1223.github.io/fast-soy-admin-docs/
- API 文档（Apifox）：https://apifox.com/apidoc/shared-7cd78102-46eb-4701-88b1-3b49c006504b
- 前端上游：https://github.com/soybeanjs/soybean-admin
- 协议：MIT

---

## 1. 快速开始

### 1.1 环境要求

| 工具 | 版本 |
|---|---|
| Git | — |
| Python | ≥ 3.12 |
| Node.js | ≥ 20.0.0 |
| uv | 最新 |
| pnpm | ≥ 10.5 |
| make | 任意 |

所有常用命令都封装在项目根目录的 `Makefile` 里。

### 1.2 Docker 部署（推荐）

```bash
git clone https://github.com/sleep1223/fast-soy-admin
cd fast-soy-admin
make up           # docker compose up -d
```

启动三个容器：Nginx (`:1880` 反代 + 静态资源)、FastAPI (`:9999`)、Redis (`:6379`)。

### 1.3 本地开发

```bash
make install-all  # 后端 uv sync + 前端 pnpm install
make initdb       # 首次建表 + 基础数据（之后不再需要）
make dev          # 并行启动后端 :9999 + 前端 :9527
```

---

## 2. 顶层仓库结构

```
fast-soy-admin/
├── app/                       # 后端（FastAPI）
│   ├── __init__.py            # App 工厂、lifespan、多 worker init 协调
│   ├── core/                  # 框架基础设施（无业务）
│   ├── system/                # 内置系统模块（auth / user / role / menu / api / dict）
│   ├── business/              # 业务模块（autodiscover 自动加载）
│   │   └── hr/                #   参考实现：员工 / 部门 / 标签
│   ├── cli/                   # 代码生成器（init / gen / gen-web / initdb）
│   └── utils/                 # 业务开发者的统一 import 入口
├── web/                       # 前端（Vue3 + Vite）
│   └── src/
│       ├── views/             # 页面组件（Elegant Router 源）
│       ├── service/api/       # Alova API 封装
│       ├── typings/api/       # TS 类型声明
│       ├── store/modules/     # Pinia 状态管理
│       ├── router/            # Elegant Router + 守卫
│       ├── layouts/           # 基础布局
│       ├── locales/           # vue-i18n（zh-CN / en-US）
│       ├── hooks/             # 组合式函数
│       └── theme/             # 主题设置
├── web/packages/              # 前端内部子包（alova / axios / hooks / utils / color / uno-preset）
├── deploy/                    # Docker 与 Nginx 配置
├── migrations/                # Tortoise ORM 迁移文件（gitignored，按 DB app 分目录）
├── tests/                     # 后端 pytest
├── Makefile                   # 所有命令的统一入口
└── docker-compose.yml
```

---

## 3. 后端架构

### 3.1 包边界与依赖方向

| 包 | 职责 | 依赖方向 |
|---|---|---|
| `app/core/` | 框架基础设施 | 不依赖 system / business |
| `app/system/` | 内置系统模块（认证、RBAC、字典、监控） | 仅依赖 `app/core/` |
| `app/business/<x>/` | 业务模块 | 依赖 `app/utils`；**不得依赖兄弟业务模块**、不得反向依赖 `app.system.*`（少数 system 显式暴露的 service 除外，如 `ensure_menu`） |
| `app/utils/` | 业务开发者对外稳定入口 | 重新导出 `app/core/*` 与少量 `app/system/*` 符号 |
| `app/cli/` | 代码生成器 | 离线使用，不进入运行时 |

跨业务模块联动通过[事件总线](#_612-事件总线)解耦。

### 3.2 分层

```
HTTP Request
    ↓
api/           FastAPI 路由：薄 HTTP 适配器（鉴权依赖 + 调 service/controller + Success/Fail）
    ↓
services/      多模型编排、事务、缓存、状态机、审计、跨模块事件
    ↓
controllers/   CRUDBase 子类：单资源 CRUD 与 build_search
    ↓
models / schemas
```

| 层 | 写什么 | 不写什么 |
|---|---|---|
| `api/` | URL 接线、依赖（鉴权）、调 service/controller 的薄包装 | 业务规则、跨模型、事务 |
| `services/` | 事务、跨模型、Redis、状态机、审计、事件 | HTTP（Request/Response） |
| `controllers/` | `XxxController(CRUDBase)`、`build_search` | 多模型副作用 |
| `models/` | 表字段、索引、关系、Mixin | 业务校验 |
| `schemas/` | `XxxCreate / XxxUpdate / XxxSearch`，字段级校验 | 跨资源 |

### 3.3 启动生命周期

```
create_app()
  ├─ register_db(app)                  # Tortoise.init(config=TORTOISE_ORM)
  ├─ register_exceptions(app)          # BizError / DoesNotExist / IntegrityError / ValidationError
  ├─ register_routers(app, prefix="/api")
  ├─ discover_business_routers()       # /api/v1/business/<name>/*
  └─ setup_radar(app)

lifespan(app)
  ├─ init_redis() → app.state.redis
  ├─ FastAPICache.init(RedisBackend(redis))
  ├─ delete app:init_lock / app:init_done
  ├─ _run_init_data(app):              # 多 worker 中仅 leader 执行
  │    ├─ init_menus()                 # 系统菜单种子
  │    ├─ refresh_api_list()           # FastAPI 路由 ↔ Api 表全量对账
  │    ├─ init_users()                 # 系统角色 + 默认账号 + 字典
  │    ├─ for each business init():    # 业务模块 init_data.init()
  │    └─ refresh_all_cache()          # 角色权限 / 常量路由刷 Redis
  ├─ startup_radar()
  └─ yield
       ↓ shutdown
  └─ close_redis()
```

多 worker 情况：Leader 通过 `SET app:init_lock 1 NX EX 120` 抢占，成功后执行完整 init，再 `SET app:init_done 1 EX 120`；非 leader 轮询 `app:init_done`，最长等 150s。每次进程启动前 leader 先 `DEL` 锁，因此每次重启都会真的跑一次 init。

### 3.4 中间件栈

按顺序：`CORSMiddleware` → `PrettyErrorsMiddleware` → `BackgroundTaskMiddleware` → `RequestIDMiddleware` → `RadarMiddleware`（可选）→ `fastapi-guard`（可选）。

- `RequestIDMiddleware` 注入 `X-Request-ID` 响应头与 `CTX_X_REQUEST_ID`
- `BackgroundTaskMiddleware` 把 FastAPI 的 `BackgroundTasks` 注入 `CTX_BG_TASKS`
- `PrettyErrorsMiddleware` 美化异常输出
- Radar 捕获请求 / SQL / 异常到内置 Dashboard（`/manage/radar/*`）

### 3.5 路由前缀

| 前缀 | 用途 |
|---|---|
| `/api/v1/auth` | 认证（公开） |
| `/api/v1/route` | 前端拉常量路由 / 用户路由 |
| `/api/v1/system-manage/*` | 系统模块（用户 / 角色 / 菜单 / API / 字典） |
| `/api/v1/business/<module>/*` | 业务模块（autodiscover 自动挂载） |

---

## 4. RBAC 与认证

### 4.1 数据模型

```
User ←M2M→ Role ←M2M→ Menu      (菜单权限：决定前端可见的路由)
                ←M2M→ Button    (按钮权限：决定页面内可执行的操作)
                ←M2M→ Api       (接口权限：决定可调用的后端接口)
                FK    Menu      (角色首页 by_role_home)
              field   data_scope (行级数据范围: all / department / self / custom)
```

- 超级管理员 `R_SUPER` 跳过所有权限校验，自动挂所有非 constant 菜单与所有按钮
- 按钮编码约定 `B_<MODULE>_<RESOURCE>_<ACTION>`，角色编码 `R_<UPPER>`
- 路由名 `route_name` 是前端 vue-router 的 `name`，也是后端 `Menu.route_name` 唯一键——改名意味着所有引用它的角色 seed 都要改

### 4.2 JWT

HS256，payload 携带 `userId / userName / tokenType / tokenVersion / impersonatorId`。

- access token 默认 12h，refresh token 默认 7d
- Redis 维护 `token_version:{uid}`，修改密码 / 超管模拟登录时递增，老 token 失效（码 `2106`）
- Token 过期（`2103`）由前端自动走 `/api/v1/auth/refresh-token` 刷新并重放原请求
- 非法 / 缺失 / 解码失败（`2100` / `2101`）直接登出

### 4.3 鉴权依赖

| 依赖 | 用途 | 失败码 |
|---|---|---|
| `DependAuth` | 解 JWT + 校验 token 版本 + 加载用户/角色/按钮到 ContextVars | `21xx` |
| `DependPermission` | 在 `DependAuth` 之上，按 `(method, path)` 比对 `role.apis` | `2200` / `2201` |
| `require_buttons("B_X", ...)` | 任一通过即可 | `2203` |
| `require_buttons(..., require_all=True)` | 全部通过 | `2202` |
| `require_roles("R_X", ...)` | 任一通过即可 | `2205` |
| `require_roles(..., require_all=True)` | 全部通过 | `2204` |

上下文工具：`get_current_user()` / `get_current_user_id()` / `is_super_admin()` / `has_role_code()` / `has_button_code()`，均从 `app.utils` 导出。

### 4.4 行级 data_scope

`Role.data_scope` 为 `all / department / self / custom`。用户有多个角色时取最宽松的 scope（`all > department > self > custom`）。列表类接口使用 `build_scope_filter(scope, user_id=..., department_id=...)` 返回 `Q` 对象参与查询。

> **强约定**：涉及行级权限的列表接口必须 `@crud.override("list")` 拼 `build_scope_filter`，不要在模型层默认。业务角色种子**必须显式声明** `data_scope`，避免误用默认的 `all`。

---

## 5. API 约定（强制规范）

### 5.1 响应格式

所有成功响应：

```json
{ "code": "0000", "msg": "OK", "data": { ... } }
```

HTTP status 恒为 200，业务结果由 `code` 字段承载。

- ✅ 必须返回 `Success` / `SuccessExtra` / `Fail`（来自 `app.utils`）
- ❌ 不要返回裸 dict、`JSONResponse(...)`、`{"code": "0000", ...}` 字面量
- ❌ 不要手拼 snake_case——`SchemaBase` 与 `Model.to_dict()` 自动 camelCase

### 5.2 路径与方法

| 操作 | 方法 + 路径 | Body / Params |
|---|---|---|
| 列表 / 搜索 | `POST /resources/search` | Body 继承 `PageQueryBase` |
| 单条查询 | `GET /resources/{id}` | — |
| 创建 | `POST /resources` | Body: `XxxCreate` |
| 更新 | `PATCH /resources/{id}` | Body: `XxxUpdate` |
| 单条删除 | `DELETE /resources/{id}` | — |
| 批量删除 | `DELETE /resources` | Body: `CommonIds`（`{ids: [...]}`） |
| 子资源 | `GET/PATCH /resources/{id}/sub` | — |
| 派生查询 | `GET /resources/tree` / `.../options` | — |
| 实例动作 | `POST /resources/{id}/action-name` | 视情况 |
| 集合动作 | `POST /resources/batch-offline` 等 | Body |

约束：

- 资源名一律 **复数**
- 多词路径一律 **kebab-case**（`/batch-offline`、`/user-routes`）
- **不要**带尾斜杠
- 搜索一律 `POST /search`，不要 `GET ?...=...`

### 5.3 字段命名

- 请求 body / query 一律 **camelCase**（Pydantic `validate_by_name=True` 兼容 snake_case，但前端始终发 camelCase）
- 响应 `data` 一律 **camelCase**（`schema.model_dump(by_alias=True)` 或 `model.to_dict()`）

### 5.4 分页

继承 `PageQueryBase`：

| 字段 | 默认 | 说明 |
|---|---|---|
| `current` | `1` | 页码（≥ 1） |
| `size` | `10` | 每页数（1–1000） |
| `orderBy` | `null` | 排序字段列表，`-` 前缀降序，如 `["-createdAt", "id"]` |

响应：

```json
{ "code": "0000", "data": { "records": [...], "total": 42, "current": 1, "size": 10 } }
```

### 5.5 资源 ID 一律 sqid

对外 ID 都是 sqid 字符串（如 `Yc7vN3kE`），不是自增 int。Pydantic 中用 `SqidId`，FastAPI 路径参数用 `SqidPath`：

```python
from app.utils import SqidId, SqidPath, SchemaBase

class DepartmentUpdate(SchemaBase):
    parent_id: SqidId | None = None

@router.get("/departments/{item_id}")
async def get_dept(item_id: SqidPath):
    ...
```

Sqids 的字母表从 `SECRET_KEY` 派生。

### 5.6 响应封装

| 类 | 用途 | 场景 |
|---|---|---|
| `Success(data=...)` | 单条 / 无分页 | get / create / update |
| `SuccessExtra(data={"records": [...]}, total, current, size)` | 分页 | list / search |
| `Fail(code=Code.X, msg="...")` | 业务失败 | 规则不通过 |
| `Custom(code, status_code, msg, data, **kwargs)` | 极少数自定义 status_code 场景 | — |

OpenAPI 需要准确响应模型时在路由上加 `response_model=ResponseModel[UserOut]` 或 `PageResponseModel[UserOut]`。

---

## 6. 核心机制

### 6.1 CRUDBase

单资源 CRUD 的入口，放在 `controllers/`。提供 `list / get / create / update / remove / build_search`，自动从 `CTX_USER_ID` 填 `created_by / updated_by`。不做跨资源副作用——多模型编排走 service 层。

### 6.2 CRUDRouter

6 条标准路由的工厂，一次声明：

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
router = dept_crud.router
```

- 自定义某条路由用 `@crud.override("list")`（key 可选 `list / get / create / update / remove / batch_remove`）；不要在 router 上重新声明同路径——`_OrderedRouter` 会把静态路径排在动态路径前面以避免遮蔽（`GET /resources/{id}` vs `GET /resources/tree`），绕过它会出错
- 标准 6 路由之外的端点直接挂在 `crud.router` 上
- 按钮权限通过 `action_dependencies` 挂载，对 `@override` 的路由同样生效

### 6.3 Schema 基类

- `SchemaBase`：`alias_generator=to_camel_case`、`populate_by_name=True`；自动 snake_case ↔ camelCase
- `PageQueryBase`：分页搜索基类（`current` / `size` / `orderBy`）
- `CommonIds`：`{ids: [...]}` 批量删除 body
- `OfflineByRoleRequest`：按角色下线用户的 body
- `make_optional(XxxCreate, "XxxUpdate")`：从 Create 派生 Update，把所有字段改成 `Optional`，避免冗余字段
- Schema 校验器中要返回业务码时用 `SchemaValidationError(code, msg)`（**不要** `ValueError`——Pydantic 会捕获）
- 字段约束类型：`Int16 / Int32 / Int64`

### 6.4 模型 Mixin

| Mixin | 字段 |
|---|---|
| `BaseModel` | `id`，`to_dict()`（自动 sqid 编码、枚举/datetime 序列化） |
| `AuditMixin` | `created_at / updated_at / created_by / updated_by`（从 `CTX_USER_ID` 自动写入） |
| `TreeMixin` | `parent_id`（`0` 为根） |
| `SoftDeleteMixin` | `deleted_at`，默认 QuerySet 过滤掉已删除 |

约束：

- 模型文件头加 `# pyright: reportIncompatibleVariableOverride=false`（Tortoise + basedpyright 已知误报）
- 字段加 `description="..."`（CLI 生成 schema 时会截断到第一个句号前作为 i18n 中文名）
- 类的 docstring 写中文资源名（`"""部门"""`），作为 API summary 前缀
- `Meta.table` 用 `biz_<module>_<entity>` 前缀；系统模型在 `app/system/models/` 下用语义化表名

### 6.5 app.utils 导出面

业务模块统一从 `app.utils` 导入：

```python
from app.utils import (
    # ORM
    BaseModel, AuditMixin, TreeMixin, SoftDeleteMixin,
    StatusType, IntEnum, StrEnum,
    # Schema / 响应
    SchemaBase, PageQueryBase,
    Success, Fail, SuccessExtra,
    CommonIds, OfflineByRoleRequest,
    ResponseModel, PageResponseModel,
    Custom, make_optional,
    # CRUD
    CRUDBase, get_db_conn,
    CRUDRouter, SearchFieldConfig,
    # 业务码 & 异常
    Code, BizError, SchemaValidationError,
    # 鉴权
    DependAuth, DependPermission,
    require_buttons, require_roles,
    CTX_USER_ID,
    get_current_user, get_current_user_id,
    is_super_admin, has_role_code, has_button_code,
    # 数据权限
    DataScopeType, build_scope_filter,
    # 事件 & 状态机
    emit, on, StateMachine,
    # Sqids
    encode_id, decode_id, SqidId, SqidPath,
    Int16, Int32, Int64,
    # 配置 / 常量 / 日志 / 监控
    APP_SETTINGS, SUPER_ADMIN_ROLE, log, radar_log,
    # 安全
    create_access_token, get_password_hash, verify_password,
)
```

不通过 `app.utils` 暴露的符号（`app.core.cache.*` 业务专用函数、`app.core.redis`、中间件、`init_app`、`app.system.models.*`）按需从原路径导入，但尽量保持"业务不依赖 system 内部"的边界。

### 6.6 事件总线

进程内、同步、单次遍历。失败的 handler 被记录到日志但不阻断发布者：

```python
from app.utils import emit, on

@on("employee.created")
async def _send_welcome(employee_id: int, **_):
    ...

# 另一层
await emit("employee.created", employee_id=emp.id)
```

事件名约定 `<aggregate>.<verb>`（如 `employee.created`、`order.refunded`）。

### 6.7 状态机

```python
from app.utils import StateMachine

EmployeeSM = StateMachine(transitions={
    "active":   ["on_leave", "resigned"],
    "on_leave": ["active", "resigned"],
    "resigned": [],
})

await EmployeeSM.transition(emp, to="on_leave", state_field="status",
                            actor_id=ctx.user_id, log_fn=radar_log)
```

非法流转抛 `BizError(Code.HR_INVALID_TRANSITION, ...)`。

### 6.8 事务

用 `in_transaction(get_db_conn(Model))`；跨模型用 `get_db_conn` 取连接名，不要硬编码 `"conn_system"`（业务模块可能是独立库）。**不要**在事务里做 HTTP、Redis、队列。嵌套事务走 SAVEPOINT。

```python
from tortoise.transactions import in_transaction
from app.utils import get_db_conn

async with in_transaction(get_db_conn(Product)):
    product = await product_controller.create(obj_in=...)
    await stock_controller.create(obj_in={"product_id": product.id, "qty": 0})
```

并发保护：乐观锁用 `version` 字段 + `QuerySet.filter(..., version=v).update(version=v+1)` 的返回值判断冲突；悲观锁用 `select_for_update()`（SQLite 不支持，生产用 PG / MySQL）；跨 worker 协调用 Redis 分布式锁。

---

## 7. 响应码

所有接口（含 200 / 4xx / 5xx）统一返回 `{"code": "xxxx", ...}`，HTTP status 恒 200。源码：`app/core/code.py`。

### 7.1 码段划分

| 码段 | 含义 |
|---|---|
| `0000` | 成功 |
| `1000–1999` | 系统内部错误（异常、入参校验失败） |
| `2000–2999` | 业务逻辑错误（认证、授权、资源冲突、业务失败） |
| `3000–3999` | 框架预留（暂未使用） |
| `4000–9999` | 项目自定义业务码 |

### 7.2 关键码

| 码 | 常量 | 说明 | 前端行为 |
|---|---|---|---|
| `0000` | `SUCCESS` | 成功 | 提取 `data` |
| `1000` | `INTERNAL_ERROR` | 通用异常 | 显示 `msg` |
| `1100` | `INTEGRITY_ERROR` | 唯一键 / 外键冲突 | 显示 `msg` |
| `1101` | `NOT_FOUND` | `DoesNotExist` | 显示 `msg` |
| `1200` | `REQUEST_VALIDATION` | 入参校验失败 | 显示 `msg`，`data.errors` 含字段级详情 |
| `2100` | `INVALID_TOKEN` | Token 缺失 / 格式错 | 跳转登录 |
| `2101` | `INVALID_SESSION` | Token 类型错 / 用户不存在 | 跳转登录 |
| `2102` | `ACCOUNT_DISABLED` | 账号禁用 | 弹窗后登出 |
| `2103` | `TOKEN_EXPIRED` | access token 过期 | 自动刷新 token |
| `2106` | `SESSION_INVALIDATED` | `token_version` 递增，旧 token 失效 | 跳转登录 |
| `2200` | `API_DISABLED` | 接口被禁用 | — |
| `2201` | `PERMISSION_DENIED` | RBAC 接口权限不足 | — |
| `2202` | `MISSING_BUTTON_PERMISSION` | 缺必需按钮（`require_all=True`） | — |
| `2203` | `NEED_ANY_BUTTON_PERMISSION` | 无任一按钮权限 | — |
| `2206` | `SUPER_ADMIN_ONLY` | 仅超管 | — |
| `23xx` | `DUPLICATE_*` | 资源冲突（role_code / email / phone / username / menu_route） | — |
| `2400` | `FAIL` | 兜底（**避免使用**，新增场景请分配新码） |
| `2401` | `WRONG_CREDENTIALS` | 用户名或密码错误 |
| `2500` | `RATE_LIMITED` | 请求过于频繁 |
| `2501` | `IP_BANNED` | IP 被封 |
| `26xx` | `*_REQUIRED` | Schema 必填（`USERNAME_REQUIRED` 等） |
| `27xx` | `HR_*` | HR 业务码示例（`HR_INVALID_TRANSITION` 等） |

### 7.3 抛出方式

```python
from app.utils import BizError, Code, Fail

# 推荐：任意层穿透
raise BizError(code=Code.HR_INVALID_TRANSITION, msg="不允许的状态流转")

# 仅在 api 层用，更直白
return Fail(code=Code.OLD_PASSWORD_WRONG, msg="原密码错误")
```

Schema 校验器中用 `SchemaValidationError(code, msg)`（继承 `BizError`，绕过 Pydantic 对 `ValueError` 的捕获）。

### 7.4 前端码映射（`.env`）

| 变量 | 默认 | 行为 |
|---|---|---|
| `VITE_SERVICE_SUCCESS_CODE` | `0000` | 提取 `data` |
| `VITE_SERVICE_LOGOUT_CODES` | `2100,2101` | 直接登出 |
| `VITE_SERVICE_MODAL_LOGOUT_CODES` | `2102` | 弹窗后登出 |
| `VITE_SERVICE_EXPIRED_TOKEN_CODES` | `2103` | 自动刷新 token 并重试 |

---

## 8. 业务模块：autodiscover 与目录约定

`app/core/autodiscover.py` 在启动时扫描 `app/business/*`（`_` 前缀目录跳过），按约定加载：

| 约定 | 提供的能力 |
|---|---|
| `app/business/<name>/models.py` 或 `models/` | Tortoise 模型 → 注册到 `TORTOISE_ORM["apps"]` |
| `app/business/<name>/api/` 或 `api.py` | 必须导出 `router: APIRouter` → 挂到 `/api/v1/business/<name>/*` |
| `app/business/<name>/init_data.py` | 可选 `async def init()` → 系统初始化后、缓存刷新前执行 |
| `app/business/<name>/config.py` 声明 `DB_URL` | 注册独立连接 `conn_<name>` 与独立 app（多库支持） |

推荐目录结构（参考 `app/business/hr/`）：

```
app/business/<name>/
├── __init__.py
├── config.py          # BIZ_SETTINGS（可选，独立库、环境变量）
├── ctx.py             # 模块上下文变量（按需）
├── dependency.py      # 模块专属依赖
├── models.py          # Tortoise 模型
├── schemas.py         # Pydantic schema（继承 SchemaBase）
├── controllers.py     # CRUDBase 子类（单资源）
├── services.py        # 多模型编排
├── init_data.py       # async def init()：菜单 / 角色 / 种子
└── api/
    ├── __init__.py    # 必须导出汇总后的 router
    ├── manage.py
    └── my.py
```

### 8.1 业务模块开发流程（CLI）

```bash
# 1. 装依赖、首次初始化数据库（仅首次）
make install-all
make initdb

# 2. 创建模块骨架（只含 models.py）
make cli-init MOD=inventory

# 3. 编辑 app/business/inventory/models.py，定义 Tortoise 模型
#    - 继承 BaseModel, AuditMixin
#    - 每字段加 description="..."
#    - 类 docstring 写中文名 """仓库"""
#    - Meta.table = "biz_inventory_warehouse"

# 4. 生成后端 + 前端代码（也可分两步 cli-gen / cli-gen-web）
make cli-gen-all MOD=inventory CN=库存管理

# 5. 合并 i18n 片段（按生成文件头注释指示把 route 与 page 片段粘贴到 langs/zh-cn.ts / en-us.ts）

# 6. 处理 TODO（外键 / 自定义枚举的 options 数据源）

# 7. 迁移数据库
make mm            # == makemigrations + migrate

# 8. 启动并验证
make dev

# 9. 提交前质量检查
make check-all
```

字段类型映射（CLI 根据 Tortoise 字段自动推导前端表单）：

| Tortoise 字段 | TS 类型 | 后端 schema | 前端表单 | 前端搜索 |
|---|---|---|---|---|
| `CharField` | `string` | `str` | `NInput` | `NInput` |
| `TextField` | `string` | `str` | `NInput type="textarea"` | `NInput` |
| `IntField` / `BigIntField` | `number` | `int` | `NInputNumber` | `NInputNumber` |
| `DecimalField` / `FloatField` | `number` | `Decimal` / `float` | `NInputNumber :precision="2"` | 跳过 |
| `BooleanField` | `boolean` | `bool` | `NSwitch` | — |
| `DateField` / `DatetimeField` | `string` | `date` / `datetime` | `NDatePicker` | — |
| `CharEnumField(StatusType)` | `string` | `StatusType` | `NSelect statusTypeOptions` | 同左 |
| `CharEnumField(其他枚举)` | `string` | `str` | `NSelect` + TODO | 同左 |
| `ForeignKeyField` | `number` | `int` | `NSelect` + TODO | 同左 |

### 8.2 init_data 的同步语义

| 数据类型 | 同步方式 | 改字段 | 新增项 | 删除项 | 重命名 |
|---|---|---|---|---|---|
| **API** | `refresh_api_list` 全量对账 | ✅ 自动 | ✅ 自动 | ✅ 自动 | ✅ 自动（删旧建新） |
| **菜单 / 按钮** | `ensure_menu` upsert + 可选 `reconcile_menu_subtree` | ✅ 自动 | ✅ 自动 | ⚠️ 需启用对账 | ⚠️ 需启用对账 |
| **角色** | `ensure_role` upsert；`menus/buttons/apis` clear-and-readd | ✅ 自动 | ✅ 自动 | ❌ 需手动清库 | ❌ 需手动清库 |
| **业务种子数据** | `_safe_update_or_create` 按唯一键 | ✅ 自动 | ✅ 自动 | ❌ 需手动清库 | ❌ 需手动清库 |

一旦对某子树调用 `reconcile_menu_subtree()`，该子树变成 **Infrastructure-as-Code** 模式：通过 Web UI 手工在该子树下创建的菜单 / 按钮会在下次重启时被清除。需要允许用户动态加菜单的子树**不要**对它调用。

`ensure_role` 的漂移告警：声明列表里引用的 `route_name` / `button_code` / `(method, path)` 在数据库找不到时会 log.warning——**看到立即修**，否则角色权限会静默缺失。

### 8.3 init_data 示例

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
        "buttons": [{"button_code": "B_INV_CREATE", "button_desc": "创建仓库"}],
    },
]

INVENTORY_ROLE_SEEDS = [
    {
        "role_name": "库存管理员",
        "role_code": "R_INV_MGR",
        "data_scope": "all",
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
        menu_name="库存管理", route_name="inventory", route_path="/inventory",
        icon="mdi:package-variant", order=9,
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

删除模块：直接删 `app/business/<module>/` 整个目录，autodiscover 自动跳过；数据库表不会自动删，需手动 `DROP TABLE` 或写迁移。

---

## 9. 缓存模型

| 数据 | Redis Key | TTL | 写入方 |
|---|---|---|---|
| 常量路由 | `constant_routes` | 永久 | `refresh_all_cache` |
| 角色菜单 ID | `role:{code}:menus` | 永久 | `load_role_permissions` |
| 角色 API | `role:{code}:apis` | 永久 | 同上 |
| 角色按钮 | `role:{code}:buttons` | 永久 | 同上 |
| 角色数据范围 | `role:{code}:data_scope` | 永久 | 同上 |
| 用户角色 | `user:{uid}:roles` | 永久 | `load_user_roles` |
| 用户首页 | `user:{uid}:role_home` | 永久 | 同上 |
| Token 版本 | `token_version:{uid}` | 永久 | 修改密码 / 模拟登录 |
| 业务自有缓存 | 按模块自定义 | 模块自定 | 模块自定 |

Redis 故障时降级到数据库查询（log WARNING）。

业务缓存命名：`<module>_<resource>:<scope>`（如 `hr_dept_stats:all`、`dict_options:tag_category`）；启动协调 key：`app:<purpose>`（如 `app:init_lock` / `app:init_done`）。

**不要**给带分页 / 多参数的接口加全局 `@cache(...)` 装饰器；业务自有热点按"读 → miss → 查 → 写带 TTL"模式手写并**主动失效**。

---

## 10. 多数据库

默认所有模型挂在主连接 `conn_system`。业务模块在自己的 `config.py` 声明独立 `DB_URL` 时，autodiscover 会注册独立连接 `conn_<biz>` 与独立 app。

- 跨模型事务用 `get_db_conn(Model)` 取连接名，**不要硬编码**
- `migrations/app_system/` 放主 + 共享模型的迁移；`migrations/<module>/` 放模块独立库的迁移
- SQLite（开发）/ Postgres / MySQL / SQL Server 都支持

---

## 11. Radar 监控 & Guard

- **Radar**（`app/system/radar/`）：请求、SQL 查询、异常、用户埋点（`radar_log(...)`），Dashboard 在 `/manage/radar/*` 五个页面。
- **fastapi-guard**：限流 / 自动封禁。触发时前端收到 `2500` / `2501` / `2502`。

---

## 12. 命令参考

### 12.1 后端

| Make 命令 | 原始命令 | 作用 |
|---|---|---|
| `make install` | `uv sync` | 安装后端依赖 |
| `make run` | `uv run python run.py` | 启动后端（:9999） |
| `make lint` | `uv run ruff check app/` + `uv run ruff format --check app/` | Ruff 检查（不修改） |
| `make fmt` | `uv run ruff check --fix` + `uv run ruff format` | Ruff 自动修复 + 格式化 |
| `make typecheck` | `uv run basedpyright app` | 静态类型检查 |
| `make test` | `uv run pytest tests/ -v` | 单元测试 |
| `make check` | — | fmt + typecheck + test |

### 12.2 数据库

| Make 命令 | 原始命令 | 作用 |
|---|---|---|
| `make initdb` | `uv run python -m app.cli initdb` | 首次初始化（建表 + 基础数据） |
| `make makemigrations` | `uv run tortoise makemigrations` | 生成迁移文件 |
| `make migrate` | `uv run tortoise migrate` | 应用未执行的迁移 |
| `make mm` | — | makemigrations + migrate |
| `make dbhistory` | `uv run tortoise history` | 查看迁移历史 |

启动时**不会**自动建表或执行迁移。全新克隆的仓库先 `make initdb`，之后模型变更手动 `make mm`。

### 12.3 代码生成

| Make 命令 | 原始命令 | 作用 |
|---|---|---|
| `make cli-init MOD=xxx` | `uv run python -m app.cli init <MOD>` | 创建业务模块骨架 |
| `make cli-gen MOD=xxx` | `uv run python -m app.cli gen <MOD>` | 生成后端 schemas/controllers/api |
| `make cli-gen-web MOD=xxx [CN=中文名]` | `uv run python -m app.cli gen-web <MOD>` | 生成前端 service/typings/views/i18n |
| `make cli-gen-all MOD=xxx [CN=中文名]` | — | 一次跑完 cli-gen + cli-gen-web |

### 12.4 前端

| Make 命令 | 原始命令 | 作用 |
|---|---|---|
| `make web-install` | `cd web && pnpm install` | 安装前端依赖 |
| `make web-dev` | `cd web && pnpm dev` | 启动前端（:9527） |
| `make web-build` | `cd web && pnpm build` | 生产构建 |
| `make web-lint` | `cd web && pnpm lint` | ESLint + oxlint |
| `make web-typecheck` | `cd web && pnpm typecheck` | vue-tsc 类型检查 |
| `make web-check` | — | web-lint + web-typecheck |

### 12.5 全栈 & Docker

| 命令 | 作用 |
|---|---|
| `make install-all` | 同时装后端 + 前端依赖 |
| `make dev` | 并行启动后端（:9999）+ 前端（:9527） |
| `make check-all` | 后端 + 前端所有质量检查 |
| `make up` | `docker compose up -d`（nginx :1880 + fastapi :9999 + redis） |
| `make down` | `docker compose down` |
| `make logs` | `docker compose logs -f` |

---

## 13. 前端架构

### 13.1 技术栈

Vue 3.5 + Vite 7 + TypeScript 5.9 + Naive UI 2.44 + Pinia 3 + UnoCSS + Alova（HTTP）+ vue-router 4 + Elegant Router + vue-i18n + ECharts 6。`web/` 是 pnpm workspace；`web/packages/` 是内部子包（alova / axios / hooks / utils / color / uno-preset）。

### 13.2 路由

- **动态路由**：登录后由后端 `GET /api/v1/route/user-routes` 下发；按角色过滤
- **常量路由**：内置（登录、403/404/500、home），`meta.constant=true`；由 `GET /api/v1/route/constant-routes` 下发
- **Elegant Router**：根据 `web/src/views/` 文件结构自动生成路由，`views/hr/employee/index.vue` → 路径 `/hr/employee`、name `hr_employee`；`[id].vue` → `:id` 参数；`_` 前缀目录会展平层级
- **守卫**：`beforeEach` 完成首次初始化（拉 user-info / 用户路由 / 常量路由），校验登录与角色后放行；`afterEach` 走 NProgress 与同步 `document.title`
- **useRouterPush**：类型安全路由（`routerPushByKey('route_name', params)` / `toHome()` / `toLogin()` / `routerBack()`）
- **keep-alive**：组件用 `defineOptions({ name: '...' })` + 路由 `meta.keepAlive=true`；重新激活时用 `onActivated()` 做刷新
- **Layout 组件**：`layout.base`（含侧栏）/ `layout.blank`（空白）/ `view.xxx`（纯页面）/ `layout.base$view.xxx`（组合）；由路由结构自动推断

### 13.3 请求层

- 基于 **Alova**；`createRequest()` 返回 `Promise<data>`，`createFlatRequest()` 返回 `{data, error}`
- 自动注入 Authorization 头；收到 `2103` 自动拉 refresh-token 并重放；`2100/2101` 直接登出；`2102` 弹窗后登出
- API 函数放在 `web/src/service/api/<module>.ts`，命名 `fetchXxx*`；类型在 `web/src/typings/api/<module>.d.ts`（`Api.<Module>.<Type>`）
- 资源 ID 透传 sqid 字符串（前端不解码）
- 代理：开发走 Vite `server.proxy` → `http://127.0.0.1:9999`；生产走 Nginx → `http://app:9999`。前端始终用相对路径 `/api/v1/...`
- 多后端：在 `.env` 加 `VITE_OTHER_SERVICE_BASE_URL`，创建独立的请求工厂

### 13.4 Pinia

| 模块 | 内容 |
|---|---|
| `auth` | token / user-info / 登录态 |
| `route` | 动态路由树、扁平路由、已访问路由 |
| `tab` | 多页签状态 |
| `theme` | 颜色 / 布局 / 暗色模式 |
| `app` | 全局状态（语言、加载） |

### 13.5 主题

- 默认配置在 `web/src/theme/settings.ts` → 存 localStorage → 应用到 Naive UI 与 UnoCSS
- 5 种语义色（primary / info / success / warning / error），每种 11 级（50–950）
- 暗色模式：`<html class="dark">` 切换，UnoCSS `dark:` 前缀，自动作用到 Naive UI
- 布局模式：vertical / horizontal / vertical-mix / horizontal-mix
- UnoCSS 类：`text-primary`、`bg-primary-100`、`border-primary` 由主题自动生成

### 13.6 图标

- Iconify（在线 / 离线）：`icon-mdi-home`、`icon-material-symbols-settings-rounded`
- 本地 SVG：`web/src/assets/svg-icon/*.svg` → `icon-local-<name>`
- 前缀由 `.env` 的 `VITE_ICON_PREFIX` / `VITE_ICON_LOCAL_PREFIX` 配置
- 使用方式：直接组件（编译时校验）、`<svg-icon icon="..." />`（运行时动态）、`useSvgIconRender()` 渲染函数
- 菜单图标：后端 `Menu.icon` + `Menu.icon_type`（`1` = iconify，`2` = local）

### 13.7 表格与 CRUD Hooks

- `useNaivePaginatedTable`：分页 / 列 / loading / 搜索参数，参数变化自动拉数据；返回 `{ data, columns, loading, getData, getDataByPage, ... }`
- `useTableOperate`：CRUD 抽屉状态，`{ drawerVisible, operateType, editingData, handleAdd, handleEdit, handleBatchDelete, ... }`
- `hasAuth(button_code)`：按钮权限判断

---

## 14. 命名规范

### 14.1 文件 / 目录

| 位置 | 规范 | 示例 |
|---|---|---|
| 前端 | `kebab-case` | `user-list.vue`、`hooks/use-table.ts` |
| 后端 | `snake_case` | `init_helper.py`、`hr/api/manage.py` |
| 业务模块名 | `snake_case` 单词 | `hr` / `inventory` |

### 14.2 Python

| 类型 | 规范 | 示例 |
|---|---|---|
| 类 | `PascalCase` | `UserController` / `EmployeeCreate` |
| 函数 / 方法 | `snake_case` | `get_user()` |
| 模块级常量 | `UPPER_SNAKE_CASE` | `SECRET_KEY` / `SUPER_ADMIN_ROLE` |
| 模块级私有 | `_snake_case` | `_safe_update_or_create()` |
| 字段（DB / Schema 内部） | `snake_case` | `user_name` / `created_at` |
| 字段（HTTP 边界） | **camelCase** | `userName` / `createdAt` |
| Pydantic 模型 | `PascalCase` + `Create/Update/Search/Out` | `EmployeeCreate` |
| Tortoise 模型 | `PascalCase` 单数 | `Employee` / `Department` |
| `Meta.table` | `<scope>_<module>_<entity>` | `biz_hr_employee` / `sys_dictionary` |

### 14.3 TypeScript

| 类型 | 规范 | 示例 |
|---|---|---|
| 组件 | `PascalCase` | `UserCard` |
| Composable | `useXxx` | `useTable` |
| 函数 | `camelCase` | `getUser()` |
| 常量 | `UPPER_SNAKE_CASE` | `MAX_COUNT` |
| API 请求函数 | `fetchXxx` | `fetchUserList()` |
| 类型 / 接口 | `Api.<Module>.<Type>` | `Api.User.UserOut` |

### 14.4 URL

| 类型 | 规范 | 示例 |
|---|---|---|
| 资源段 | 复数 + `kebab-case` | `/users` / `/system-manage/users` |
| 子资源 | 复数 + 父 ID | `/roles/{id}/menus` |
| 集合动作 | 资源 + `/<verb-noun>` | `/roles/batch-offline` |
| 实例动作 | `/{id}/<verb-noun>` | `/employees/{id}/transition` |
| 派生 | `/<noun>` | `/menus/tree` |
| ❌ | 尾斜杠、camelCase、复数单数混用 | ❌ `/users/` / ❌ `/userList` |

### 14.5 业务码 / 路由名 / 事件名

```
B_<MODULE>_<RESOURCE>_<ACTION>      # 按钮编码
R_<UPPER>                           # 角色编码
<module>_<page>[_<sub>]             # 路由名（vue-router name = Menu.route_name）
<aggregate>.<verb>                  # 事件名（employee.created）
```

i18n key：`route.<route_name>` / `page.<module>.<key>` / `common.<key>`。
缓存 key：系统级 `role:{code}:*` / `user:{uid}:*`；业务级 `<module>_<resource>:<scope>`；启动协调 `app:<purpose>`。

---

## 15. 后端风格（PR review checklist）

1. **响应**：必须用 `Success / SuccessExtra / Fail`；不要返回裸 dict；每个失败场景分配唯一业务码，避免 `Code.FAIL` 兜底；业务异常用 `raise BizError(code, msg)`，`Fail(...)` 仅在 api 层用
2. **Schema**：业务 schema 继承 `SchemaBase`；分页搜索继承 `PageQueryBase`；ID 用 `SqidId / SqidPath`；整型用 `Int16/32/64`；Update schema 用 `make_optional`；校验器内用 `SchemaValidationError` 而非 `ValueError`
3. **API 路径**：列表 `POST /resources/search`、单条 `GET/PATCH/DELETE /resources/{id}`、创建 `POST /resources`、批量删除 `DELETE /resources` + `CommonIds`；kebab-case 多词路径；复数资源名；不带尾斜杠；不要 `GET ?...=...` 复杂搜索
4. **CRUD**：标准 6 路由必须用 `CRUDRouter`；自定义用 `@crud.override`；不要绕过 `_OrderedRouter`；controller / service 不导入 `fastapi.Request/Response`
5. **分层职责**：严格遵守 api/services/controllers/models/schemas 的边界
6. **权限**：写接口必须挂按钮权限；角色种子必须显式 `data_scope`；涉及行级权限的列表必须 `@override("list")` 拼 `build_scope_filter`；不要靠前端隐藏按钮做安全；不要在业务里直接判 `role_code == "..."`，用 `has_role_code` / `has_button_code`
7. **模型**：继承 `BaseModel + AuditMixin`；`# pyright: reportIncompatibleVariableOverride=false` 头；字段加 `description=...`；类 docstring 写中文名；`Meta.table = biz_<module>_<entity>`
8. **业务模块边界**：import 入口统一走 `app.utils`；跨模块用事件总线；不得反向依赖 `app.system.*`；模块之间互相不 import
9. **异常**：用 `BizError / SchemaValidationError`；不要 `raise HTTPException`；不要 catch `Exception` 后吞掉；事务用 `in_transaction(get_db_conn(Model))`；不要硬编码连接名
10. **缓存**：业务自有热点手写 + 主动失效；不要给分页 / 多参数接口加全局 `@cache(...)`；按 `<module>_<resource>:<scope>` 命名
11. **日志与监控**：关键节点 / 权限拒绝 / 异常分支用 `radar_log`；高频调试用 `log.debug`；不要 `print(...)`
12. **类型注解与格式化**：所有函数加类型注解；提交前跑 `make fmt`、`make typecheck`、`make test`、`make check`；行宽 200，双引号；basedpyright standard 模式必须通过
13. **提交前**：`make check-all`（含 ruff + basedpyright + pytest + eslint + oxlint + vue-tsc）

---

## 16. 前端风格

- SFC 用 `<script setup lang="ts">`；keep-alive 页面必须 `defineOptions({ name: '...' })`，name 与路由 name 一致
- 列表页统一 `useNaivePaginatedTable` + `useTableOperate`，不要手写分页逻辑
- 不要硬编码中文；文案走 `$t('...')` / `t('...')`；i18n key：`route.xxx` / `page.<module>.<key>` / `common.<key>`
- `<Transition>` 包含内容必须是**单根节点**
- 使用相对路径 `/api/v1/...`，不要写完整 URL
- 资源 ID 透传 sqid 字符串，不要 `parseInt`

---

## 17. 配置（`.env`）

关键项（完整列表见 `app/core/config.py`）：

- `SECRET_KEY` — JWT 签名 + Sqids 字母表来源
- `DB_URL` — 主库连接（SQLite / Postgres / MySQL / SQL Server）
- `REDIS_URL` — Redis 连接
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`（默认 720，12h）/ `JWT_REFRESH_TOKEN_EXPIRE_MINUTES`（默认 10080，7d）
- `CORS_ORIGINS` — 允许的前端来源
- `APP_DEBUG` — debug 模式
- `PROXY_HEADERS_ENABLED` — 让 Granian 还原 `X-Forwarded-*`
- `GUARD_*` — fastapi-guard 限流参数
- `LOG_INFO_RETENTION` — 日志保留

前端 `.env`：

- `VITE_SERVICE_SUCCESS_CODE` / `VITE_SERVICE_LOGOUT_CODES` / `VITE_SERVICE_MODAL_LOGOUT_CODES` / `VITE_SERVICE_EXPIRED_TOKEN_CODES`
- `VITE_OTHER_SERVICE_BASE_URL`（多后端场景）
- `VITE_ICON_PREFIX` / `VITE_ICON_LOCAL_PREFIX`

---

## 18. 部署

### 18.1 Docker Compose

```bash
make up       # nginx (:1880) + fastapi (:9999) + redis
make logs     # 实时日志
make down     # 停止并移除
```

架构：Nginx 托管前端静态资源 + 反代 `/api/*` 到 FastAPI；Redis 提供缓存；编排文件在 `docker-compose.yml`，相关 Dockerfile / nginx.conf 在 `/deploy/`。

### 18.2 手动部署

- `uv sync --no-dev && uv run granian --interface asgi --workers 4 app:app --host 0.0.0.0 --port 9999`
- 生产用 Postgres / MySQL + Redis（SQLite 仅开发）
- 静态资源交给 Nginx；前端构建产物在 `web/dist/`

---

## 19. 关键端点速查

### 19.1 认证（`/api/v1/auth`，公开）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/login` | 用户名密码登录 |
| POST | `/captcha` | 发送手机验证码 |
| POST | `/code-login` | 验证码登录 |
| POST | `/register` | 注册（默认角色 `R_USER`） |
| POST | `/refresh-token` | 刷新 access token |
| GET | `/user-info` | 当前用户信息 + 角色 + 按钮（`DependAuth`） |
| PATCH | `/password` | 修改密码（递增 token 版本） |
| POST | `/impersonate/{user_id}` | 超管模拟登录 |

### 19.2 路由（`/api/v1/route`）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/constant-routes` | 公共路由（从 Redis） |
| GET | `/user-routes` | 当前用户菜单树（`DependAuth`） |
| GET | `/exists?name=xxx` | 校验路由名是否存在 |

### 19.3 系统管理（`/api/v1/system-manage`，全部 `DependPermission`）

所有资源遵循 5.2 标准 6 路由：

| 资源 | 前缀 | 备注 |
|---|---|---|
| 用户 | `/users` | create / update 注入密码哈希 + 角色关联 |
| 角色 | `/roles` | 含 `GET /roles/{id}/menus` 等子资源 |
| 菜单 | `/menus` | 含 `GET /menus/tree` / `GET /menus/pages` |
| API | `/apis` | 含 `POST /apis/refresh`（手动触发对账） |
| 字典 | `/dictionaries` | 含 `GET /dictionaries/{type}/options`（5 分钟 Redis 缓存） |

### 19.4 业务模块（`/api/v1/business/<name>`）

按模块自治。HR 模块的完整路由见 `/api/v1/business/hr/...`（员工、部门、标签）。

---

## 20. 参考

- 源码：https://github.com/sleep1223/fast-soy-admin
- 文档：https://sleep1223.github.io/fast-soy-admin-docs/
- API（Apifox）：https://apifox.com/apidoc/shared-7cd78102-46eb-4701-88b1-3b49c006504b
- 前端上游 SoybeanAdmin：https://github.com/soybeanjs/soybean-admin
- FastAPI：https://fastapi.tiangolo.com/
- Tortoise ORM：https://tortoise.github.io
