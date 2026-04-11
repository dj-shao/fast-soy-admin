"""
业务模块根目录 — 启动时自动发现。

约定
--------
``app/business/`` 下每个包含 ``__init__.py`` 的子目录都被视为一个业务模块。
``app/core/autodiscover.py`` 会查找以下可选入口点（均为按需启用）：

* ``models.py`` 或 ``models/`` — Tortoise ORM 模型，自动注册到
  ``TORTOISE_ORM["apps"]``。
* ``api/`` 包或 ``api.py`` — 须导出 ``router: APIRouter``，
  挂载到 ``/api/v1/business/``。
* ``init_data.py`` — 可导出 ``async def init()``，在系统初始化之后、
  Redis 缓存刷新之前运行一次。用于初始化模块专属菜单、按钮、角色及演示数据。

以下划线开头的目录会被跳过。

推荐目录结构
------------------
::

    app/business/<name>/
    ├── __init__.py
    ├── config.py          # 模块专属 Pydantic 配置
    ├── ctx.py             # 模块专属上下文变量（按需）
    ├── dependency.py      # 模块专属 FastAPI 依赖
    ├── models.py          # Tortoise 模型
    ├── schemas.py         # Pydantic Schema（继承 SchemaBase）
    ├── controllers.py     # CRUDBase 子类（单资源）
    ├── services.py        # 多模型编排、Redis、事务处理
    ├── init_data.py       # async def init() — 初始化菜单/角色等
    └── api/
        ├── __init__.py    # 须导出聚合子路由的 `router`
        ├── manage.py
        └── my.py

规范
-----
* 业务模块不得被 ``app.system.*`` 导入 — 依赖方向单向流动：
  ``system → utils → business``。业务代码只应从 ``app.utils`` 导入共享辅助函数。
* 所有 Schema 须继承 ``app.core.base_schema.SchemaBase``（已从 ``app.utils`` 重导出），
  以确保请求/响应体为 camelCase 格式。
* 所有 HTTP 路由须遵循项目 API 规范（``CLAUDE.md``）：列表使用
  ``POST /resources/search``，无尾部斜线，请求体为 camelCase，
  响应使用 ``Success``/``Fail``/``SuccessExtra``。
* 不得在业务 init 代码中自动执行 ``makemigrations``，迁移须手动操作
  （``tortoise makemigrations && tortoise migrate``）。
"""
