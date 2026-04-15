"""代码生成器 — 根据解析后的 ModelInfo 生成业务模块文件。"""

from __future__ import annotations

from pathlib import Path

from app.cli.parser import FieldInfo, ModelInfo, RelationInfo, collect_extra_imports

# Tortoise 整型字段 → 约束类型别名（来自 app.utils.types）
INT_FIELD_CONSTRAINT: dict[str, str] = {
    "SmallIntField": "Int16",
    "IntField": "Int32",
    "BigIntField": "Int64",
}


def _field_type_hint(f: FieldInfo) -> str:
    """根据 Tortoise 字段类型返回带约束的 Python 类型注解字符串。

    - SmallIntField / IntField / BigIntField → Int16 / Int32 / Int64
    - CharField(max_length=N) → Annotated[str, Field(max_length=N)]
    - CharEnumField / IntEnumField → 枚举类型名（由 parser 填入 python_type）
    - 其他字段沿用 python_type
    """
    if f.enum_type:
        return f.enum_type

    constrained_int = INT_FIELD_CONSTRAINT.get(f.field_type)
    if constrained_int:
        return constrained_int

    if f.field_type == "CharField" and f.python_type == "str" and f.max_length:
        return f"Annotated[str, Field(max_length={f.max_length})]"

    return f.python_type


def _schema_field_line(f: FieldInfo, *, optional: bool = False) -> str:
    """生成单个 schema 字段行。"""
    type_hint = _field_type_hint(f)
    title = f.description or f.name

    if optional or not f.required:
        return f'{f.name}: {type_hint} | None = Field(None, title="{title}")'
    return f'{f.name}: {type_hint} = Field(title="{title}")'


def _collect_constrained_types(models: list[ModelInfo]) -> tuple[set[str], bool]:
    """扫描所有字段，返回 (需要从 app.utils 导入的整型别名集合, 是否使用 Annotated)。"""
    int_types: set[str] = set()
    needs_annotated = False
    for model in models:
        for f in model.schema_fields:
            if f.enum_type:
                continue
            if f.field_type in INT_FIELD_CONSTRAINT:
                int_types.add(INT_FIELD_CONSTRAINT[f.field_type])
            elif f.field_type == "CharField" and f.python_type == "str" and f.max_length:
                needs_annotated = True
    return int_types, needs_annotated


def _fk_schema_field(r: RelationInfo, *, optional: bool = False) -> str:
    """外键在 schema 中表示为 xxx_id: int。"""
    title = r.name.replace("_", " ")
    if optional or r.nullable:
        return f'{r.name}_id: int | None = Field(None, title="{title}")'
    return f'{r.name}_id: int = Field(title="{title}")'


# ─── schemas.py ───


def gen_schemas(module_name: str, models: list[ModelInfo]) -> str:
    """生成 schemas.py 内容。"""
    extra_imports = collect_extra_imports(models)
    import_lines = sorted(extra_imports)

    int_types, needs_annotated = _collect_constrained_types(models)
    # 收集被引用的 enum 类型
    enum_types = {f.enum_type for m in models for f in m.schema_fields if f.enum_type}

    lines = [
        "# pyright: reportIncompatibleVariableOverride=false",
        '"""',
        f"{module_name} — 请求/响应 Schema。",
        '"""',
        "",
    ]
    if needs_annotated:
        lines.append("from typing import Annotated")
        lines.append("")
    if import_lines:
        lines.extend(import_lines)
        lines.append("")

    utils_symbols = {"PageQueryBase", "SchemaBase"} | enum_types | int_types
    utils_imports = ", ".join(sorted(utils_symbols))

    lines.extend([
        "from pydantic import Field",
        "",
        f"from app.utils import {utils_imports}",
        "",
    ])

    for model in models:
        schema_fields = model.schema_fields
        fk_relations = [r for r in model.relations if r.relation_type in ("ForeignKeyField", "OneToOneField")]

        # ---- Base ----
        lines.append(f"# {'=' * 60}")
        lines.append(f"# {model.cn_name}")
        lines.append(f"# {'=' * 60}")
        lines.append("")
        lines.append("")
        lines.append(f"class {model.name}Base(SchemaBase):")
        if schema_fields or fk_relations:
            for f in schema_fields:
                lines.append(f"    {_schema_field_line(f, optional=True)}")
            for r in fk_relations:
                lines.append(f"    {_fk_schema_field(r, optional=True)}")
        else:
            lines.append("    pass")
        lines.append("")
        lines.append("")

        # ---- Create ----
        # Create: 必填字段不再是 optional
        create_required_fields = [f for f in schema_fields if f.required]
        create_required_fks = [r for r in fk_relations if not r.nullable]
        if create_required_fields or create_required_fks:
            lines.append(f"class {model.name}Create({model.name}Base):")
            for f in create_required_fields:
                lines.append(f"    {_schema_field_line(f, optional=False)}")
            for r in create_required_fks:
                lines.append(f"    {_fk_schema_field(r, optional=False)}")
        else:
            lines.append(f"class {model.name}Create({model.name}Base):")
            lines.append("    pass")
        lines.append("")
        lines.append("")

        # ---- Update ----
        lines.append(f"class {model.name}Update({model.name}Base): ...")
        lines.append("")
        lines.append("")

        # ---- Search ----
        lines.append(f"class {model.name}Search({model.name}Base, PageQueryBase):")
        lines.append("    pass")
        lines.append("")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# ─── controllers.py ───


def gen_controllers(module_name: str, models: list[ModelInfo]) -> str:
    model_names = ", ".join(m.name for m in models)
    controller_lines = [f"{m.snake_name}_controller = CRUDBase(model={m.name})" for m in models]

    lines = [
        '"""',
        f"{module_name} controllers — 基于 CRUDBase 的控制器。",
        '"""',
        "",
        f"from app.business.{module_name}.models import {model_names}",
        "from app.utils import CRUDBase",
        "",
        *controller_lines,
        "",
    ]
    return "\n".join(lines)


# ─── services.py ───


def gen_services(module_name: str, models: list[ModelInfo]) -> str:
    controller_imports = ", ".join(f"{m.snake_name}_controller" for m in models)

    lines = [
        '"""',
        f"{module_name} services — 业务逻辑层。",
        '"""',
        "",
        f"from app.business.{module_name}.controllers import {controller_imports}  # noqa: F401",
        "",
        "",
        "# ---- 在此编写业务逻辑 ----",
        "",
    ]
    return "\n".join(lines)


# ─── api/manage.py ───


def gen_api_manage(module_name: str, models: list[ModelInfo], contains_map: dict[str, list[str]]) -> str:
    lines = [
        '"""',
        f"{module_name} 管理接口 — CRUD。",
        '"""',
        "",
        "from fastapi import APIRouter",
        "",
        "from app.utils import CRUDRouter, DependPermission, SearchFieldConfig",
    ]

    # controller imports
    controller_imports = ", ".join(f"{m.snake_name}_controller" for m in models)
    lines.append(f"from app.business.{module_name}.controllers import {controller_imports}")

    # schema imports
    schema_names = []
    for m in models:
        schema_names.extend([f"{m.name}Create", f"{m.name}Update", f"{m.name}Search"])
    lines.append(f"from app.business.{module_name}.schemas import (")
    for sn in schema_names:
        lines.append(f"    {sn},")
    lines.append(")")
    lines.append("")

    # CRUDRouter per model
    for m in models:
        contains = contains_map.get(m.name, [])
        # exact_fields: 有 enum_type 或 status 字段
        exact = [f.name for f in m.schema_fields if f.enum_type or f.name == "status"]

        lines.append(f"{m.snake_name}_crud = CRUDRouter(")
        lines.append(f'    prefix="/{m.plural_snake}",')
        lines.append(f"    controller={m.snake_name}_controller,")
        lines.append(f"    create_schema={m.name}Create,")
        lines.append(f"    update_schema={m.name}Update,")
        lines.append(f"    list_schema={m.name}Search,")

        sf_parts = []
        if contains:
            sf_parts.append(f"contains_fields={contains}")
        if exact:
            sf_parts.append(f"exact_fields={exact}")
        if sf_parts:
            lines.append(f"    search_fields=SearchFieldConfig({', '.join(sf_parts)}),")

        lines.append(f'    summary_prefix="{m.cn_name}",')
        lines.append(")")
        lines.append("")

    # router
    lines.append(f'router = APIRouter(prefix="/{module_name}", tags=["{module_name}"], dependencies=[DependPermission])')
    for m in models:
        lines.append(f"router.include_router({m.snake_name}_crud.router)")
    lines.append("")

    return "\n".join(lines)


# ─── api/__init__.py ───


def gen_api_init(module_name: str) -> str:
    lines = [
        "from fastapi import APIRouter",
        "",
        f"from app.business.{module_name}.api.manage import router as manage_router",
        "",
        "router = APIRouter()",
        "router.include_router(manage_router)",
        "",
    ]
    return "\n".join(lines)


# ─── init_data.py ───


def gen_init_data(module_name: str) -> str:
    lines = [
        '"""',
        f"{module_name} 初始化数据 — 菜单、角色、种子数据。",
        "",
        "启动时由 autodiscover 自动发现并执行 init()。",
        "所有操作幂等，重复启动不会重复创建。",
        '"""',
        "",
        "# from app.system.services import ensure_menu, ensure_role, reconcile_menu_subtree",
        "",
        "",
        "async def init():",
        '    """模块初始化入口 — 由 autodiscover 调用。"""',
        "    # await _init_menu_data()",
        "    # await _init_role_data()",
        "    pass",
        "",
    ]
    return "\n".join(lines)


# ─── __init__.py ───


def gen_module_init() -> str:
    return ""


# ─── 汇总写入 ───


ALL_FILES: dict[str, str] = {
    "schemas.py": "schemas",
    "controllers.py": "controllers",
    "services.py": "services",
    "init_data.py": "init_data",
    "api/__init__.py": "api_init",
    "api/manage.py": "api_manage",
}


def generate_all(
    module_dir: Path,
    module_name: str,
    models: list[ModelInfo],
    contains_map: dict[str, list[str]],
    *,
    skip: set[str] | None = None,
    force: bool = False,
) -> list[tuple[str, str]]:
    """生成所有文件，返回 [(相对路径, 状态)] 列表。

    状态: "created" / "skipped" (已存在)
    """
    skip = skip or set()
    results: list[tuple[str, str]] = []

    generators = {
        "schemas.py": lambda: gen_schemas(module_name, models),
        "controllers.py": lambda: gen_controllers(module_name, models),
        "services.py": lambda: gen_services(module_name, models),
        "init_data.py": lambda: gen_init_data(module_name),
        "api/__init__.py": lambda: gen_api_init(module_name),
        "api/manage.py": lambda: gen_api_manage(module_name, models, contains_map),
    }

    for rel_path, gen_fn in generators.items():
        if rel_path in skip:
            results.append((rel_path, "skipped"))
            continue

        target = module_dir / rel_path
        if target.exists() and not force:
            results.append((rel_path, "exists"))
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(gen_fn(), encoding="utf-8")
        results.append((rel_path, "created"))

    return results
