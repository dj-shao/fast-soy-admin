# FastSoyAdmin

FastSoyAdmin 是一套开箱即用的全栈后台管理模板。前端基于 Vue3、Vite7、TypeScript、Pinia 和 UnoCSS 构建，后端采用 FastAPI、Pydantic v2 和 Tortoise ORM，并通过 Redis 加速接口响应。

- **源码**：https://github.com/sleep1223/fast-soy-admin
- **在线预览**：https://fast-soy-admin.sleep0.de/
- **API 文档**：https://apifox.com/apidoc/shared-7cd78102-46eb-4701-88b1-3b49c006504b
- **前端上游**：https://github.com/soybeanjs/soybean-admin
- **协议**：MIT

---

## 一、项目总览

### 特性

- **全栈技术栈**：后端 FastAPI + Pydantic v2 + Tortoise ORM，前端 Vue3 + Vite7 + TypeScript + Pinia + UnoCSS
- **完整的权限体系**：基于 RBAC 模型，前后端角色权限严格分离，后端对 API 和按钮级别进行二次鉴权
- **Redis 缓存加速**：集成 fastapi-cache2 + Redis，有效提升接口响应速度
- **清晰的项目结构**：pnpm monorepo 管理，后端分层架构（Router → Controller → CRUD/Model）
- **严格的代码规范**：前端 ESLint + oxlint + simple-git-hooks；后端 Ruff + basedpyright
- **TypeScript 全覆盖**：支持严格类型检查
- **丰富的主题配置**：内置多套主题方案，与 UnoCSS 深度集成
- **国际化支持**：vue-i18n 多语言方案（中文 / English）
- **丰富的页面与组件**：内置异常页面，集成 ECharts、AntV、VChart 等可视化库
- **移动端适配**：响应式布局
- **Docker 一键部署**：Nginx + FastAPI + Redis

### 技术栈

**后端**：Python 3.12+, FastAPI, Pydantic v2, Tortoise ORM 1.x, Redis (fastapi-cache2), Argon2, PyJWT (HS256), uv, Ruff, basedpyright

**前端**：Vue 3.5, Vite 7, TypeScript 5.9, Naive UI 2.44, Pinia 3, UnoCSS, Alova, Elegant Router, vue-i18n, ECharts 6

**部署**：Docker Compose (Nginx + FastAPI + Redis)

### 架构概览

```
┌─────────────────────────────────────────────────┐
│                    Nginx (:1880)                 │
│         静态资源服务 + /api/* 反向代理            │
├─────────────────────┬───────────────────────────┤
│   Frontend (:9527)  │     Backend (:9999)        │
│   Vue3 + Vite7      │     FastAPI                │
│                     │                            │
│   Views             │     Router (api/v1/)       │
│     ↓               │       ↓                    │
│   Store (Pinia)     │     Controller             │
│     ↓               │       ↓                    │
│   Service (Alova)   │     CRUD / Model           │
│     ↓               │       ↓                    │
│   HTTP Request ─────┼──→  API Endpoint           │
│                     │       ↓                    │
│                     │     SQLite / Redis          │
└─────────────────────┴───────────────────────────┘
```

### RBAC 权限模型

```
User ←M2M→ Role ←M2M→ Menu   (菜单权限)
                  ←M2M→ API    (接口权限)
                  ←M2M→ Button (按钮权限)
```

- 超级管理员角色 `R_SUPER` 跳过所有权限检查
- 前端通过动态路由控制菜单可见性
- 后端通过 `PermissionControl` 依赖进行接口鉴权

### 快速开始

**Docker 部署（推荐）**

```bash
git clone https://github.com/sleep1223/fast-soy-admin
cd fast-soy-admin
docker compose up -d
# Nginx :1880, FastAPI :9999, Redis :6379
```

**本地开发**

环境要求：Git, Python >= 3.12, Node.js >= 20.0.0, uv, pnpm >= 10.5

```bash
git clone https://github.com/sleep1223/fast-soy-admin
cd fast-soy-admin

# 后端
uv sync && uv run python run.py        # 端口 9999

# 前端（新终端）
cd web && pnpm install && pnpm dev      # 端口 9527
```

### 项目结构

```
fast-soy-admin/
├── app/                       # 后端 (FastAPI)
│   ├── __init__.py            # App 工厂，中间件注册，启动钩子
│   ├── api/v1/                # API 路由
│   │   ├── auth/              # 认证（登录、刷新令牌）
│   │   ├── route/             # 动态路由管理
│   │   └── system_manage/     # 系统管理（用户、角色、菜单、API）
│   ├── controllers/           # 业务逻辑层
│   ├── models/system/         # Tortoise ORM 模型
│   ├── schemas/               # Pydantic 请求/响应模型
│   ├── core/                  # 核心（初始化、认证、CRUD、中间件、上下文）
│   ├── settings/config.py     # 环境配置 (pydantic-settings)
│   └── utils/                 # 工具函数（安全、通用）
├── web/                       # 前端 (Vue3)
│   ├── src/
│   │   ├── views/             # 页面组件
│   │   ├── service-alova/     # HTTP 客户端 + API 接口
│   │   ├── store/modules/     # Pinia 状态管理
│   │   ├── router/            # Elegant Router + 路由守卫
│   │   ├── layouts/           # 布局组件
│   │   ├── components/        # 可复用组件
│   │   ├── locales/           # 国际化 (zh-CN, en-US)
│   │   ├── hooks/             # Vue 组合式函数
│   │   └── typings/           # TypeScript 类型声明
│   └── packages/              # 内部 monorepo 包
├── deploy/                    # Docker 部署配置
├── migrations/                # 数据库迁移 (Tortoise ORM built-in)
└── docker-compose.yml         # Docker Compose 编排
```

### 业务响应码

所有接口统一返回格式 `{"code": "xxxx", "msg": "...", "data": ...}`。

| 码值 | 常量名 | 说明 | 前端行为 |
|------|--------|------|----------|
| `0000` | SUCCESS | 请求成功 | 正常处理 |
| `1000` | INTERNAL_ERROR | 未捕获的内部异常 | 显示错误 |
| `1100` | INTEGRITY_ERROR | 数据库约束冲突 | 显示错误 |
| `1101` | NOT_FOUND | 记录不存在 | 显示错误 |
| `1200` | REQUEST_VALIDATION | 请求参数校验失败 | 显示错误 |
| `1201` | RESPONSE_VALIDATION | 响应序列化失败 | 显示错误 |
| `2100` | INVALID_TOKEN | Token 无效 | 跳转登录 |
| `2101` | INVALID_SESSION | Token 类型错误/用户不存在 | 跳转登录 |
| `2102` | ACCOUNT_DISABLED | 账号已被禁用 | 弹窗登出 |
| `2103` | TOKEN_EXPIRED | Token 已过期 | 自动刷新 |
| `2200` | API_DISABLED | API 已停用 | 显示错误 |
| `2201` | PERMISSION_DENIED | 权限不足 | 显示错误 |
| `2300` | DUPLICATE_RESOURCE | 资源重复 | 显示错误 |
| `2400` | FAIL | 通用业务失败 | 显示错误 |
| `4000-9999` | 自定义 | 业务层自定义 | 调用方处理 |

---

## 二、前端

### 路由系统

基于 [Elegant Router](https://github.com/soybeanjs/elegant-router) 插件，从 `src/views/` 目录自动生成路由。

**路由结构示例**：
- 一级路由：`views/about/index.vue` → `/about`
- 二级路由：`views/manage/user/index.vue` → `/manage/user`
- 多级路由：`views/manage_user_detail/index.vue` → `/manage/user/detail`（下划线避免深嵌套）
- 参数路由：`views/user/[id].vue` → `/user/:id`

**路由 Meta 属性**：

```typescript
interface RouteMeta {
  title: string;                           // 路由标题
  i18nKey?: App.I18n.I18nKey;             // 国际化 key
  roles?: string[];                        // 允许的角色（空 = 无限制）
  keepAlive?: boolean;                     // 缓存
  constant?: boolean;                      // 常量路由（无需登录）
  icon?: string;                           // Iconify 图标
  localIcon?: string;                      // 本地 SVG 图标
  order?: number;                          // 菜单排序
  href?: string;                           // 外链
  hideInMenu?: boolean;                    // 菜单中隐藏
  activeMenu?: RouteKey;                   // 激活的菜单项
  multiTab?: boolean;                      // 多标签页
  fixedIndexInTab?: number;                // 固定标签页
  query?: { key: string; value: string }[];// 自动查询参数
}
```

**权限模式**：
- 静态路由 (`VITE_AUTH_ROUTE_MODE=static`)：前端定义，`roles` 过滤
- 动态路由 (`VITE_AUTH_ROUTE_MODE=dynamic`)：后端 API 返回

### 请求系统

**环境配置**：

```
VITE_SERVICE_SUCCESS_CODE=0000
VITE_SERVICE_LOGOUT_CODES=2100,2101
VITE_SERVICE_MODAL_LOGOUT_CODES=2102
VITE_SERVICE_EXPIRED_TOKEN_CODES=2103
VITE_SERVICE_BASE_URL=/api/v1
```

**请求函数**：
- `createRequest`：返回 Axios 响应数据
- `createFlatRequest`：包装为 `{ data, error }` 格式

**Token 刷新**：后端返回 `2103` 时，自动使用 refresh token 刷新并重试。

**API 接口** (`service-alova/api/`)：
- `auth.ts`：login, getUserInfo, refreshToken
- `system-manage.ts`：用户/角色/菜单 CRUD
- `route.ts`：动态路由

### 主题系统

1. 定义主题变量（颜色、布局参数）
2. 生成 Naive UI 主题（`GlobalThemeOverrides`）
3. 生成 CSS 变量注入 UnoCSS

**主题 Token**：primary、info、success、warning、error 及色阶，boxShadow。

**UnoCSS 集成**：`text-primary`、`bg-primary-100`，暗黑模式通过 `class="dark"`。

### 图标系统

- **Iconify 图标**：`<icon-mdi-emoticon />` 或 `<svg-icon icon="mdi-emoticon" />`
- **本地图标**：`<icon-local-xxx />` 或 `<svg-icon local-icon="xxx" />`
- 来源：https://icones.js.org/

### 状态管理 (Pinia)

| Store | 说明 |
|-------|------|
| auth | token, userInfo (roles, buttons), login/logout |
| route | 动态路由加载与过滤 |
| tab | 多标签页管理 |
| theme | 主题配置（颜色、布局、暗黑模式） |
| app | 全局状态（重载、菜单折叠） |

### 路由守卫

```
页面跳转 → 常量路由？→ 放行
         → 已登录？ → 否 → 登录页
                    → 是 → 路由已加载？→ 加载 → 有权限？→ 放行
                                                      → 403
```

### 国际化

vue-i18n 支持 zh-CN / en-US，路由 meta 中设置 `i18nKey` 自动翻译菜单。

### Hooks

- **useTable**：表格数据管理（分页、列配置、数据转换）
- **useNaiveTable / useNaivePaginatedTable**：Naive UI 表格扩展
- **useTableOperate**：CRUD 操作状态
- **useRouterPush**：类型安全路由跳转

### 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 文件/目录 | kebab-case | `demo-page/` |
| Vue 组件 | PascalCase | `AppProvider` |
| 函数 | camelCase | `getUser()` |
| 常量 | UPPER_SNAKE_CASE | `MAX_COUNT` |
| 请求函数 | fetchXxx | `fetchUserList()` |

### 前端命令

```bash
cd web
pnpm dev                # 开发服务器
pnpm build              # 生产构建
pnpm lint               # ESLint + oxlint
pnpm typecheck          # vue-tsc 类型检查
pnpm gen-route          # 生成路由文件
```

---

## 三、后端

### 分层架构

```
Router (api/v1/) → Controller (controllers/) → CRUD Base (core/crud.py) → Model (models/)
```

### 数据模型

**User**：user_name, password (Argon2), nick_name, gender, email, phone, status_type
- M2M: by_user_roles (User ↔ Role)

**Role**：role_name, role_code (唯一), description, status_type
- M2M: by_role_menus, by_role_apis, by_role_buttons
- FK: by_role_home (默认首页)

**Menu**：menu_name, route_path, component, parent_id, icon, i18n_key, constant, hide_in_menu, keep_alive, status_type
- M2M: by_menu_buttons

**Api**：api_path, api_method, summary, tags, status_type
- 启动时自动从路由注册

**Button**：button_code, button_desc, status_type
- M2M: by_button_menus, by_button_roles

### API 路由

**认证 `/auth`**：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /login | 登录，返回 access + refresh token |
| POST | /refresh-token | 刷新 access token |
| GET | /getUserInfo | 获取用户信息 + 角色 + 按钮 |

**系统管理 `/system-manage`**：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /users/all/ | 搜索用户（分页） |
| GET/POST/PATCH/DELETE | /users/{id} | 用户 CRUD |
| DELETE | /users | 批量删除 |
| POST | /roles/all/ | 搜索角色（分页） |
| GET/POST/PATCH/DELETE | /roles/{id} | 角色 CRUD |
| GET/POST/PATCH/DELETE | /menus/{id} | 菜单 CRUD |
| GET | /menus/pages/ | 获取所有页面 |

**动态路由 `/route`**：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /routes | 当前用户可访问路由 |

### 认证与授权

**JWT**：HS256，access token 12h，refresh token 7d。

**RBAC**：
1. AuthControl：JWT 解码 → 查用户 → 存上下文
2. PermissionControl：查角色 → R_SUPER 放行 → 匹配 API method+path → 检查状态

### 通用 CRUD 基类

```python
class CRUDBase(Generic[ModelType]):
    get(id) → ModelType
    list(page, page_size, **filters) → (count, items)
    create(obj_in) → ModelType
    update(id, obj_in) → ModelType
    delete(id) → None
```

### Schema

统一响应封装：`Success(code="0000")`, `Fail(code="2400")`, `SuccessExtra(total, current, size)`。

所有字段使用 camelCase 别名，与前端保持一致。

### 中间件

| 中间件 | 说明 |
|--------|------|
| CORSMiddleware | 跨域 |
| PrettyErrorsMiddleware | 错误美化 |
| BackgroundTaskMiddleware | 后台任务 |
| RequestIDMiddleware | X-Request-ID |
| RadarMiddleware | 请求调试（可选） |

### 异常处理

| 异常 | 码值 | 说明 |
|------|------|------|
| IntegrityError | 1100 | 约束冲突 |
| DoesNotExist | 1101 | 记录不存在 |
| RequestValidationError | 1200 | 参数校验失败 |
| ResponseValidationError | 1201 | 响应序列化失败 |
| 其他 | 1000 | 内部错误 |

### 配置

```python
# .env
SECRET_KEY=your-secret-key
APP_DEBUG=true
CORS_ORIGINS=["http://localhost:9527"]
REDIS_URL=redis://localhost:6379/0
DB_PATH=app_system.sqlite3
```

### 后端命令

```bash
uv sync                     # 安装依赖
uv run python run.py         # 启动 (:9999)
ruff check app/              # lint
ruff format app/             # format
basedpyright app             # 类型检查
pytest tests/ -v             # 测试
tortoise makemigrations      # 生成迁移
tortoise migrate             # 执行迁移
```
