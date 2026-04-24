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

FastSoyAdmin 是一套开箱即用的全栈后台管理模板：

- **后端** — FastAPI · Pydantic v2 · Tortoise ORM · Redis
- **前端** — Vue3 · Vite7 · TypeScript · Naive UI · UnoCSS · Pinia · Alova · Elegant Router
- **基础设施** — Docker Compose（Nginx + FastAPI + Redis）、多 worker 启动锁、fastapi-guard 限流、内置 Radar 监控面板
- **代码生成器** — `make cli-init` 建骨架 → 编辑 `models.py` → `make cli-gen-all` 一键产出后端 + 前端 CRUD（含 i18n 片段）

适合作为中后台项目脚手架，也适合作为全栈开发参考。

## 特性

- **完整 RBAC** — 菜单 / API / 按钮三层权限 + 行级 `data_scope`（all / department / self / custom），前后端严格分离
- **模块自动发现** — `app/business/<name>/` 放进去就自动注册路由、模型、初始化数据；业务模块之间互相不耦合，跨模块通过事件总线通信
- **CLI 代码生成** — 从 Tortoise 模型一键生成 schemas / controllers / api + 前端 views / service / typings / i18n
- **动态路由** — 菜单 / API / 按钮权限由后端统一管理，用户登录后按角色动态下发
- **统一响应** — 所有接口返回 `{code, msg, data}`，HTTP 状态恒 200；snake_case ↔ camelCase 自动转换
- **Redis 缓存** — 角色权限 / 常量路由 / token 版本号全部走缓存，故障时降级到数据库
- **严格类型** — 前端 vue-tsc、后端 basedpyright（standard 模式），全栈类型安全
- **国际化** — vue-i18n 中 / 英双语，代码生成器自动产出 i18n 片段
- **生产可用** — 内置 Radar 请求 / SQL / 异常追踪、fastapi-guard 限流、Sqids 资源 ID、状态机 / 事件总线
- **Docker 一键部署** — Nginx + FastAPI + Redis 开箱即用

## 相关链接

- [在线预览](https://fast-soy-admin.sleep0.de/)
- [项目文档](https://sleep1223.github.io/fast-soy-admin-docs/)
- [快速开始](https://sleep1223.github.io/fast-soy-admin-docs/guide/quick-start)
- [开发指南](https://sleep1223.github.io/fast-soy-admin-docs/backend/development)
- [命令参考](https://sleep1223.github.io/fast-soy-admin-docs/backend/commands)
- [Apifox 接口文档](https://apifox.com/apidoc/shared-7cd78102-46eb-4701-88b1-3b49c006504b)

## 分支说明

| 分支 | 用途 |
| --- | --- |
| `main` | 默认分支，**带示例**（`app/business/hr/` 员工 / 部门 / 标签全套参考实现） |
| `slim` | 纯净模板骨架，不含任何业务示例模块（即将提供，便于直接在其上起新项目） |

> `slim` 分支还在整理中。当前如需无示例起步，可直接删除 `app/business/hr/` 再启动，autodiscover 会自动跳过。

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

> 启动时**不会**自动迁移。容器内 SQLite 默认**未挂卷**，生产请切外部数据库或为 `app_system.sqlite3` 挂卷。详见 [部署文档](https://sleep1223.github.io/fast-soy-admin-docs/backend/deployment)。

### 本地开发

```bash
git clone https://github.com/sleep1223/fast-soy-admin.git
cd fast-soy-admin
make install-all     # 后端 uv sync + 前端 pnpm install
make initdb          # 首次建表 + 基础数据
make dev             # 并行启动后端(:9999) + 前端(:9527)，Ctrl+C 一起停
```

## 常用命令

项目通过 `Makefile` 封装全部常用命令，运行 `make help` 查看完整列表。

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
make cli-init MOD=inventory                      # 1. 创建模块骨架（仅 models.py）
$EDITOR app/business/inventory/models.py         # 2. 定义 Tortoise 模型
make cli-gen-all MOD=inventory CN=库存管理       # 3. 同时生成后端 + 前端 CRUD
# 4. 把 web/src/locales/langs/_generated/inventory/ 三个 .md 片段合并到对应源文件
make mm                                          # 5. 执行迁移
make dev                                         # 6. 启动验证
make check-all                                   # 7. 提交前
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

分层：`api/` → `services/` → `controllers/` → `models + schemas`。业务模块**不得**反向 import `app.system.*`（少数显式暴露的 service 除外），**不得**互相 import 兄弟模块——跨模块走事件总线。详见 [架构](https://sleep1223.github.io/fast-soy-admin-docs/backend/architecture)。

## 切换数据库

修改 `.env` 的 `DB_URL`，运行 `make initdb` 即可。原生支持 SQLite / PostgreSQL / MySQL / SQL Server。

默认安装仅含 **SQLite** 驱动；切换到其它数据库需安装对应 extra：

```bash
uv sync --extra postgres     # PostgreSQL (asyncpg)
uv sync --extra mysql        # MySQL (asyncmy)
uv sync --extra mssql        # SQL Server (asyncodbc)
uv sync --extra oracle       # Oracle (asyncodbc)
```

业务模块也可在自己的 `config.py` 声明独立 `DB_URL`，autodiscover 会注册为独立连接 `conn_<biz>`，跨模型事务用 `get_db_conn(Model)` 取连接名。详见 [切换数据库](https://sleep1223.github.io/fast-soy-admin-docs/backend/database)。

## 响应码

所有接口返回 `{"code": "xxxx", "msg": "...", "data": ...}`，HTTP 状态恒 200。码段约定：

| 段          | 含义                                           | 前端典型行为             |
| ----------- | ---------------------------------------------- | ------------------------ |
| `0000`      | 成功                                           | 正常处理                 |
| `1xxx`      | 系统内部错误（异常、入参 / 响应序列化）         | 框架自动弹错             |
| `21xx`      | 认证失败（token 缺失 / 过期 / session 失效）    | 登出 / 弹窗 / 自动刷新   |
| `22xx`      | 授权失败（RBAC / 按钮 / 角色 / 超管）           | 显示错误消息             |
| `23xx`      | 资源冲突（唯一键）                             | 显示错误消息             |
| `24xx`      | 通用业务失败                                   | 显示错误消息             |
| `25xx`      | 限流 / 安全策略                                | 显示错误消息             |
| `26xx`      | Schema 必填兜底                                | 显示错误消息             |
| `27xx`      | HR 模块业务码（业务模块码示例）                | 显示错误消息             |
| `4000–9999` | 用户自定义                                     | 业务自行处理             |

详细码表见 [响应码文档](https://sleep1223.github.io/fast-soy-admin-docs/backend/codes)。

## 前端代码同步

`web/` 目录的源码由独立仓库 [fast-soy-admin-frontend](https://github.com/sleep1223/fast-soy-admin-frontend) 维护，与本仓库**没有共同祖先**。同步上游更新需手动走 `git subtree`，可查阅历史 commit `chore(web): sync with fast-soy-admin-frontend@...`。

## 示例图片

![](https://soybeanjs-1300612522.cos.ap-guangzhou.myqcloud.com/uPic/soybean-admin-v1-01.png)
![](https://soybeanjs-1300612522.cos.ap-guangzhou.myqcloud.com/uPic/soybean-admin-v1-04.png)
![](https://soybeanjs-1300612522.cos.ap-guangzhou.myqcloud.com/uPic/soybean-admin-v1-07.png)

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
