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

FastSoyAdmin 是一套开箱即用的全栈后台模板：

- **后端**：FastAPI · Pydantic v2 · Tortoise ORM · Redis
- **前端**：Vue3 · Vite7 · TypeScript · Naive UI · UnoCSS · Pinia
- **代码生成器**：`make cli-init` → 写模型 → `make cli-gen` → 生成 schemas / controllers / api / 前端 views 全链路

适合作为中后台项目起步脚手架，也适合学习全栈开发。

## 特性

- **RBAC 权限体系** · 菜单 / API / 按钮三级权限
- **CLI 代码生成** · 从 Tortoise ORM 模型一键生成后端 API 与前端 CRUD 页面（含 i18n）
- **模块自动发现** · `app/business/` 下的模块零注册，启动时自动加载
- **Redis 缓存** · fastapi-cache2 + Redis，加速接口响应
- **统一响应** · 所有接口返回 `{code, msg, data}`，snake_case ↔ camelCase 自动转换
- **严格类型** · 前端 vue-tsc、后端 basedpyright，全栈类型安全
- **国际化** · vue-i18n 中 / 英双语，代码生成器自动产出 i18n 片段
- **Docker 一键部署** · Nginx + FastAPI + Redis 开箱即用

## 相关链接

- [在线预览](https://fast-soy-admin.sleep0.de/)
- [项目文档](https://sleep1223.github.io/fast-soy-admin-docs/)
- [开发指南](https://sleep1223.github.io/fast-soy-admin-docs/backend/development)
- [命令参考](https://sleep1223.github.io/fast-soy-admin-docs/backend/commands)
- [Apifox 接口文档](https://apifox.com/apidoc/shared-7cd78102-46eb-4701-88b1-3b49c006504b)

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
make up              # docker compose up -d
```

访问 `http://localhost:1880`。

### 本地开发

```bash
git clone https://github.com/sleep1223/fast-soy-admin.git
cd fast-soy-admin
make install-all     # 安装后端 + 前端依赖
make initdb          # 首次初始化数据库
make dev             # 同时起后端(:9999) 和前端(:9527)
```

## 常用命令

项目通过 `Makefile` 封装全部常用命令。运行 `make help` 可查看完整列表。

| 命令                                   | 作用                                             |
| -------------------------------------- | ------------------------------------------------ |
| `make dev`                             | 同时启动后端 + 前端开发服务器                    |
| `make check-all`                       | 跑完后端 + 前端所有质量检查（提交前）            |
| `make mm`                              | 生成并应用数据库迁移（makemigrations + migrate） |
| `make cli-init MOD=xxx`                | 创建业务模块骨架                                 |
| `make cli-gen MOD=xxx`                 | 根据 `models.py` 生成后端代码                    |
| `make cli-gen-web MOD=xxx [CN=中文名]` | 根据 `models.py` 生成前端代码                    |
| `make cli-gen-all MOD=xxx [CN=中文名]` | 一次生成前后端代码                               |
| `make up` / `make down` / `make logs`  | Docker 启停与日志                                |

完整清单参见 [命令参考文档](https://sleep1223.github.io/fast-soy-admin-docs/backend/commands)。

## 新增业务模块

以新增 `inventory`（库存管理）模块为例：

```bash
make cli-init MOD=inventory                      # 1. 创建模块骨架
$EDITOR app/business/inventory/models.py         # 2. 定义 Tortoise 模型
make cli-gen-all MOD=inventory CN=库存管理       # 3. 生成前后端代码（== cli-gen + cli-gen-web）
make mm                                          # 4. 执行迁移
make dev                                         # 5. 启动验证
```

详细流程与字段类型映射见 [开发指南](https://sleep1223.github.io/fast-soy-admin-docs/backend/development)。

## 业务响应码

所有接口返回统一格式 `{"code": "xxxx", "msg": "...", "data": ...}`。码段约定：

| 段          | 含义                                 | 前端行为                 |
| ----------- | ------------------------------------ | ------------------------ |
| `0000`      | 成功                                 | 正常处理                 |
| `1xxx`      | 系统内部错误（校验、数据库、序列化） | 框架自动弹错             |
| `21xx`      | 认证失败                             | 跳转登录或自动刷新 token |
| `22xx`      | 授权失败（RBAC）                     | 显示错误消息             |
| `23xx`      | 资源冲突（唯一键）                   | 显示错误消息             |
| `24xx`      | 通用业务失败                         | 显示错误消息             |
| `4000–9999` | 用户自定义                           | 业务自行处理             |

详细码表见 [响应码文档](https://sleep1223.github.io/fast-soy-admin-docs/backend/codes)。

## 前端代码同步

`web/` 目录的源码由独立仓库 [fast-soy-admin-frontend](https://github.com/sleep1223/fast-soy-admin-frontend) 维护，与本仓库**没有共同祖先**。同步上游更新时需要走手动流程，详见 [前端同步文档](.extra_repo/fast-soy-admin-docs/src/guide/frontend-sync.md)（即将整理）或查阅历史 commit `chore(web): sync with fast-soy-admin-frontend@...`。

## 示例图片

![](https://soybeanjs-1300612522.cos.ap-guangzhou.myqcloud.com/uPic/soybean-admin-v1-01.png)
![](https://soybeanjs-1300612522.cos.ap-guangzhou.myqcloud.com/uPic/soybean-admin-v1-04.png)
![](https://soybeanjs-1300612522.cos.ap-guangzhou.myqcloud.com/uPic/soybean-admin-v1-07.png)

## TODO

- [x] 使用 Redis 优化响应速度
- [x] Docker 一键部署
- [x] CLI 代码生成器（后端 + 前端）
- [ ] 端对端测试

## 贡献

欢迎提交 [Pull Request](https://github.com/sleep1223/fast-soy-admin/pulls) 或创建 [Issue](https://github.com/sleep1223/fast-soy-admin/issues/new)。

<a href="https://github.com/sleep1223/fast-soy-admin/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=sleep1223/fast-soy-admin" />
</a>

## 开源协议

[MIT © 2024](./LICENSE)
