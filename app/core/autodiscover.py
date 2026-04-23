"""
业务模块自动发现机制。

扫描 app/business/*/ 下的独立业务模块。每个模块可提供：
- models.py（或 models/）    → Tortoise ORM 模型注册
- api.py（或 api/）          → FastAPI 路由（必须导出 `router`）
- init_data.py               → 启动时数据初始化（必须导出 `async def init()`）

约定：
- app/business/ 下含 __init__.py 的子目录即为业务模块
- 以 `_` 开头的目录将被跳过

目录结构示例：
    app/business/hr/
    ├── __init__.py
    ├── config.py, ctx.py, dependency.py
    ├── models.py, schemas.py, controllers.py, services.py
    ├── init_data.py
    └── api/
        ├── __init__.py  (导出 router)
        ├── manage.py
        └── my.py
"""

import importlib
from collections.abc import Callable
from pathlib import Path

from fastapi import APIRouter

# NOTE: ``app.core.log`` 在 ``discover_business_init_data`` 内部延迟导入，
# 以避免循环导入（``config.py`` 在构建 ``Settings()`` 时会调用 ``discover_business_models()``，
# 而 ``log.py`` 又依赖 ``config.py``）。

BUSINESS_ROOT = Path(__file__).resolve().parent.parent / "business"


def _discover_modules() -> list[str]:
    """获取 app/business/ 下所有业务模块名称。"""
    if not BUSINESS_ROOT.exists():
        return []
    return sorted(p.name for p in BUSINESS_ROOT.iterdir() if p.is_dir() and not p.name.startswith("_") and (p / "__init__.py").exists())


def discover_business_module_names() -> list[str]:
    """返回 app/business/ 下的所有业务模块名称。"""
    return _discover_modules()


def discover_business_models() -> list[str]:
    """返回用于 Tortoise ORM 注册的模型模块路径列表（使用默认连接）。"""
    model_modules = []
    for name in _discover_modules():
        if (BUSINESS_ROOT / name / "models.py").exists() or (BUSINESS_ROOT / name / "models" / "__init__.py").exists():
            model_modules.append(f"app.business.{name}.models")
    return model_modules


def discover_business_db_configs() -> dict[str, dict]:
    """发现业务模块中声明了独立数据库连接的配置。

    每个业务模块的 ``config.py`` 可声明 ``DB_URL`` 字段。若存在且与
    系统默认连接不同，则自动注册为独立的 Tortoise 连接。

    返回::

        {
            "hr": {"db_url": "postgres://...", "models": "app.business.hr.models"},
        }
    """
    configs: dict[str, dict] = {}
    for name in _discover_modules():
        config_path = BUSINESS_ROOT / name / "config.py"
        if not config_path.exists():
            continue
        has_models = (BUSINESS_ROOT / name / "models.py").exists() or (BUSINESS_ROOT / name / "models" / "__init__.py").exists()
        if not has_models:
            continue

        try:
            module = importlib.import_module(f"app.business.{name}.config")
        except ImportError:
            continue

        # 查找模块级 Settings 实例中的 DB_URL
        for attr_name in dir(module):
            obj = getattr(module, attr_name, None)
            if obj is not None and hasattr(obj, "DB_URL"):
                db_url = getattr(obj, "DB_URL", None)
                if db_url:
                    configs[name] = {"db_url": db_url, "models": f"app.business.{name}.models"}
                break
    return configs


def discover_business_routers() -> tuple[APIRouter, list[str]]:
    """自动发现各业务模块 api 模块中的路由。

    返回聚合后的路由对象和已发现的模块名称列表。
    """
    from app.core.log import log  # 延迟导入

    parent_router = APIRouter()
    names: list[str] = []
    for name in _discover_modules():
        module_path = BUSINESS_ROOT / name
        has_api_file = (module_path / "api.py").exists()
        has_api_pkg = (module_path / "api" / "__init__.py").exists()

        if not has_api_file and not has_api_pkg:
            log.warning(f"Business: module '{name}' discovered but has no api.py or api/ package — routes will not be registered")
            continue

        try:
            module = importlib.import_module(f"app.business.{name}.api")
        except ImportError:
            log.warning(f"Business: module '{name}' has api module but failed to import", exc_info=True)
            continue

        router = getattr(module, "router", None)
        if isinstance(router, APIRouter):
            parent_router.include_router(router)
            names.append(name)
        else:
            log.warning(f"Business: module '{name}' api module does not export a valid 'router' (APIRouter) object")
    return parent_router, names


def discover_business_init_data() -> list[Callable]:
    """自动发现各业务模块 init_data 中的 init() 函数。"""
    from app.core.log import log  # 延迟导入——参见模块 docstring 说明

    init_funcs: list[Callable] = []
    for name in _discover_modules():
        try:
            module = importlib.import_module(f"app.business.{name}.init_data")
        except ImportError:
            continue
        init_fn = getattr(module, "init", None)
        if callable(init_fn):
            init_funcs.append(init_fn)
            log.debug(f"Business: found init_data for '{name}'")
    return init_funcs
