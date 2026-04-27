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

<span><a href="./README.en.md">English</a> | 中文</span>

**FastAPI + Vue3 全栈后台管理模板，开箱即用**

</div>

## 简介

开箱即用的全栈后台管理模板，可作为中后台脚手架，也可作为全栈开发参考。

- **后端** — FastAPI · Pydantic v2 · Tortoise ORM · Redis
- **前端** — Vue3 · Vite7 · TypeScript · Naive UI · UnoCSS · Pinia · Alova · Elegant Router
- **基础设施** — Docker Compose（Nginx + FastAPI + Redis）、多 worker 启动锁、fastapi-guard 限流、内置 Radar 监控面板
- **代码生成器** — `cli-init` 起骨架，编辑 `models.py`，`cli-gen-all` 一键产出前后端 CRUD

## 特性

**AI 驱动**

- **AI Coding 友好** — 内置 [CLAUDE.md](CLAUDE.md) + [llms.txt](llms.txt) / [llms-full.md](llms-full.md)，AI 按项目规范产出代码
- **生成器即 AI 工作面** — `cli-gen-all` 一键加表，AI 只关注 `models.py` 与覆写差异

**工程效率**

- **CLI 端到端生成** — 从 Tortoise 模型一键产出前后端 CRUD（schemas / controllers / api + views / service / typings / i18n）
- **CRUDRouter + `@crud.override`** — 工厂生成 6 条标准路由，按需覆写

**可扩展架构**

- **业务模块自动发现** — 放进 `app/business/<name>/` 即自动注册；跨模块走事件总线（`emit` / `on`）
- **多库友好** — 业务模块可声明独立 `DB_URL`，事务用 `in_transaction(get_db_conn(Model))`
- **多 worker 启动协调** — Redis leader 锁串行初始化，K8s 多副本无重复对账

**安全与权限**

- **三层 RBAC + 行级 `data_scope`** — 菜单 / API / 按钮 + `all / department / self / custom`
- **菜单/角色 IaC 对账** — `ensure_menu` / `reconcile_menu_subtree` / `refresh_api_list` 三档语义
- **Sqid 对外 ID** — 防遍历枚举

**契约与类型**

- **统一响应** — `{code, msg, data}` + HTTP 200 + camelCase；业务异常用 `BizError` 穿透
- **全栈类型安全** — 后端 basedpyright + 前端 vue-tsc，CI 强制全绿
- **i18n 静态可校验** — 生成器输出自动并入语言包，`$t` 键被 vue-tsc 校验

**可观测与稳定性**

- **内置 Radar 面板** — 请求 / SQL / 异常 / 权限拒绝
- **fastapi-guard** — 限流 + IP 封禁
- **Redis 缓存 + 降级** — Redis 故障自动回落 DB
- **状态机 / 事件总线** — 工单、审批、订单等状态流转开箱即用

**部署**

- **Docker 一键部署** — Nginx + FastAPI + Redis，`docker compose up -d` 即上线

## 相关链接

- [在线预览](https://fast-soy-admin.sleep0.de/)
- [项目文档](https://sleep1223.github.io/fast-soy-admin-docs/)
- [快速开始](https://sleep1223.github.io/fast-soy-admin-docs/guide/quick-start)
- [开发指南](https://sleep1223.github.io/fast-soy-admin-docs/backend/development)
- [命令参考](https://sleep1223.github.io/fast-soy-admin-docs/backend/commands)
- [Apidog 接口文档](https://fast-soy-admin.apidog.io)

## 分支说明

| 分支 | 用途 |
| --- | --- |
| `main` | 默认分支，带 HR 示例（`app/business/hr/` 员工 / 部门 / 标签） |
| `slim` | 纯净骨架，无业务示例（整理中） |

> 临时无示例起步：删除 `app/business/hr/` 即可，autodiscover 会自动跳过。

## 快速开始

### 环境要求

| 工具             | 版本    |
| ---------------- | ------- |
| Python           | >= 3.12 |
| Node.js          | >= 20   |
| uv · pnpm · make | 最新    |

### Docker 部署（推荐）

```bash
git clone https://github.com/sleep1223/fast-soy-admin.git
cd fast-soy-admin
make up                                                       # docker compose up -d
docker compose exec app uv run python -m app.cli initdb       # 首次必须手动建表 + 基础数据
docker compose restart app
```

访问 `http://localhost:1880`。

> 启动**不会**自动迁移；容器内 SQLite **未挂卷**，生产请切外部数据库或挂卷 `app_system.sqlite3`。详见 [部署文档](https://sleep1223.github.io/fast-soy-admin-docs/backend/deployment)。

### 本地开发

```bash
git clone https://github.com/sleep1223/fast-soy-admin.git
cd fast-soy-admin
make install-all     # 后端 uv sync + 前端 pnpm install
make initdb          # 首次建表 + 基础数据
make dev             # 并行启动后端(:9999) + 前端(:9527)，Ctrl+C 一起停
```

## 常用命令

全部命令封装在 `Makefile`，运行 `make help` 查看完整列表。

| 命令                                   | 作用                                             |
| -------------------------------------- | ------------------------------------------------ |
| `make dev`                             | 同时启动后端 + 前端开发服务器                    |
| `make check-all`                       | 跑完后端 + 前端所有质量检查（提交前必跑）        |
| `make mm`                              | `makemigrations` + `migrate`                     |
| `make cli-init MOD=xxx`                | 创建业务模块骨架                                 |
| `make cli-gen MOD=xxx`                 | 根据 `models.py` 生成后端代码                    |
| `make cli-gen-web MOD=xxx CN=中文名`   | 根据 `models.py` 生成前端代码                    |
| `make cli-gen-all MOD=xxx CN=中文名`   | 一次生成前后端代码                               |
| `make up` / `make down` / `make logs`  | Docker 启停与日志                                |

完整清单参见 [命令参考](https://sleep1223.github.io/fast-soy-admin-docs/backend/commands)。

## 新增业务模块

以 `inventory`（库存管理）为例：

```bash
make cli-init MOD=inventory                      # 1. 创建模块骨架
$EDITOR app/business/inventory/models.py         # 2. 定义 Tortoise 模型
make cli-gen-all MOD=inventory CN=库存管理       # 3. 生成前后端 CRUD（i18n 自动并入）
make mm                                          # 4. 迁移
make dev                                         # 5. 启动验证
make check-all                                   # 6. 提交前检查
```

完整流程与字段类型映射见 [开发指南](https://sleep1223.github.io/fast-soy-admin-docs/backend/development)。

## 架构

```
app/
├── core/          # 框架基础设施（CRUDBase / CRUDRouter / Schema / 鉴权 / 缓存 / 事件 / Sqids）
├── system/        # 系统模块（auth / user / role / menu / api / dictionary / radar）
├── business/      # 业务模块（autodiscover 自动加载）
│   └── hr/        #   参考实现
├── cli/           # 代码生成器
└── utils/         # 业务模块对外统一 import 入口
web/src/
├── views/         # 页面（Elegant Router 源）
├── service/api/   # Alova HTTP 封装
├── typings/api/   # TS 类型
├── store/modules/ # Pinia
├── router/        # Elegant Router + 守卫
└── locales/       # vue-i18n
```

分层：`api/` → `services/` → `controllers/` → `models + schemas`。业务模块**禁止**反向 import `app.system.*`（少数显式暴露的 service 除外），**禁止**互相 import；跨模块走事件总线。详见 [架构](https://sleep1223.github.io/fast-soy-admin-docs/backend/architecture)。

## 切换数据库

修改 `.env` 中的 `DB_URL`，运行 `make initdb`。支持 SQLite / PostgreSQL / MySQL / SQL Server。

默认仅装 SQLite 驱动，其他数据库按需安装：

```bash
uv sync --extra postgres     # PostgreSQL (asyncpg)
uv sync --extra mysql        # MySQL (asyncmy)
uv sync --extra mssql        # SQL Server (asyncodbc)
uv sync --extra oracle       # Oracle (asyncodbc)
```

业务模块可在自己的 `config.py` 声明独立 `DB_URL`，autodiscover 会注册为 `conn_<biz>`；跨模型事务用 `get_db_conn(Model)` 取连接名。详见 [切换数据库](https://sleep1223.github.io/fast-soy-admin-docs/backend/database)。

## 响应码

所有接口返回 `{"code": "xxxx", "msg": "...", "data": ...}`，HTTP 状态恒 200。

| 段          | 含义                                | 前端典型行为             |
| ----------- | ----------------------------------- | ------------------------ |
| `0000`      | 成功                                | 正常处理                 |
| `1xxx`      | 系统内部错误 / 序列化失败            | 框架自动弹错             |
| `21xx`      | 认证失败（token / session）         | 登出 / 弹窗 / 自动刷新   |
| `22xx`      | 授权失败（RBAC / 按钮 / 角色）       | 显示错误消息             |
| `23xx`      | 资源冲突（唯一键）                   | 显示错误消息             |
| `24xx`      | 通用业务失败                         | 显示错误消息             |
| `25xx`      | 限流 / 安全策略                     | 显示错误消息             |
| `26xx`      | Schema 必填兜底                     | 显示错误消息             |
| `4000–9999` | 用户自定义（业务模块从 `4000` 起）   | 业务自行处理             |

详细码表见 [响应码文档](https://sleep1223.github.io/fast-soy-admin-docs/backend/codes)。

## 前端代码同步

`web/` 由独立仓库 [fast-soy-admin-frontend](https://github.com/sleep1223/fast-soy-admin-frontend) 维护，与本仓库**无共同祖先**。同步上游需手动 `git subtree`，参考历史 commit `chore(web): sync with fast-soy-admin-frontend@...`。

## 示例图片

![首页-中文](https://sleep1223.github.io/fast-soy-admin-docs/screenshots/home-zh.png)
![首页-英文](https://sleep1223.github.io/fast-soy-admin-docs/screenshots/home-en.png)
![性能监控-仪表盘](https://sleep1223.github.io/fast-soy-admin-docs/screenshots/radar-dashboard.png)
![性能监控-请求列表](https://sleep1223.github.io/fast-soy-admin-docs/screenshots/radar-requests.png)
![性能监控-SQL查询](https://sleep1223.github.io/fast-soy-admin-docs/screenshots/radar-sql.png)
![性能监控-异常列表](https://sleep1223.github.io/fast-soy-admin-docs/screenshots/radar-exceptions.png)

## TODO

- [x] Redis 优化
- [x] Docker 一键部署
- [x] CLI 代码生成器（后端 + 前端）
- [x] 内置 Radar 监控（请求 / SQL / 异常 / 埋点）
- [ ] `slim` 纯净分支
- [ ] 端到端测试

## 贡献

欢迎提交 [Pull Request](https://github.com/sleep1223/fast-soy-admin/pulls) 或创建 [Issue](https://github.com/sleep1223/fast-soy-admin/issues/new)。

<a href="https://github.com/sleep1223/fast-soy-admin/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=sleep1223/fast-soy-admin" />
</a>

## 开源协议

[MIT © 2024](./LICENSE)
