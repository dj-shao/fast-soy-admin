"""AST 解析器 — 从 models.py 提取模型、字段、关系信息。"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

# Tortoise field → Python type 映射
FIELD_TYPE_MAP: dict[str, str] = {
    "CharField": "str",
    "TextField": "str",
    "IntField": "int",
    "BigIntField": "int",
    "SmallIntField": "int",
    "BooleanField": "bool",
    "DecimalField": "Decimal",
    "FloatField": "float",
    "DatetimeField": "datetime",
    "DateField": "date",
    "TimeField": "time",
    "JSONField": "dict",
    "UUIDField": "str",
    "CharEnumField": "str",
    "IntEnumField": "int",
}

RELATION_FIELDS = {"ForeignKeyField", "ManyToManyField", "OneToOneField"}

# 自动跳过的字段（由 BaseModel / AuditMixin 提供）
SKIP_FIELDS = {"id", "created_by", "created_at", "updated_by", "updated_at"}


@dataclass
class FieldInfo:
    name: str
    field_type: str  # CharField, IntField, ...
    python_type: str  # str, int, ...
    description: str = ""
    required: bool = True
    max_length: int | None = None
    default: str | None = None
    unique: bool = False
    primary_key: bool = False
    # CharEnumField 专用
    enum_type: str | None = None


@dataclass
class RelationInfo:
    name: str
    relation_type: str  # ForeignKeyField, ManyToManyField, OneToOneField
    related_model: str = ""  # "models.Warehouse"
    related_name: str = ""
    nullable: bool = False


@dataclass
class ModelInfo:
    name: str
    cn_name: str  # 来自 docstring 或 Meta.table_description
    table: str = ""
    has_audit_mixin: bool = False
    fields: list[FieldInfo] = field(default_factory=list)
    relations: list[RelationInfo] = field(default_factory=list)

    @property
    def schema_fields(self) -> list[FieldInfo]:
        """用于生成 schema 的普通字段（排除 pk 和跳过字段）。"""
        return [f for f in self.fields if not f.primary_key and f.name not in SKIP_FIELDS]

    @property
    def snake_name(self) -> str:
        """PascalCase → snake_case"""
        result = []
        for i, ch in enumerate(self.name):
            if ch.isupper() and i > 0:
                result.append("_")
            result.append(ch.lower())
        return "".join(result)

    @property
    def plural_snake(self) -> str:
        """简单复数: skill → skills, category → categories"""
        s = self.snake_name
        if s.endswith("y") and not s.endswith(("ay", "ey", "oy", "uy")):
            return s[:-1] + "ies"
        if s.endswith(("s", "x", "sh", "ch")):
            return s + "es"
        return s + "s"


def _get_keyword_value(node: ast.Call, keyword_name: str) -> ast.expr | None:
    """从 fields.CharField(..., description="xxx") 中提取指定关键字参数值。"""
    for kw in node.keywords:
        if kw.arg == keyword_name:
            return kw.value
    return None


def _eval_const(node: ast.expr | None) -> object:
    """安全地提取常量值。"""
    if node is None:
        return None
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Attribute):
        # e.g. StatusType.enable
        return f"{_eval_const(node.value)}.{node.attr}"
    if isinstance(node, ast.Name):
        return node.id
    return None


def _parse_field(name: str, call: ast.Call) -> FieldInfo | RelationInfo | None:
    """解析一条 fields.XxxField(...) 赋值。"""
    # 获取 field 类型名
    if isinstance(call.func, ast.Attribute):
        field_type = call.func.attr
    elif isinstance(call.func, ast.Name):
        field_type = call.func.id
    else:
        return None

    if field_type in RELATION_FIELDS:
        related_model = str(_eval_const(call.args[0]) if call.args else "")
        return RelationInfo(
            name=name,
            relation_type=field_type,
            related_model=related_model,
            related_name=str(_eval_const(_get_keyword_value(call, "related_name")) or ""),
            nullable=_eval_const(_get_keyword_value(call, "null")) is True,
        )

    python_type = FIELD_TYPE_MAP.get(field_type, "str")
    has_null = _eval_const(_get_keyword_value(call, "null")) is True
    has_default = _get_keyword_value(call, "default") is not None
    is_pk = _eval_const(_get_keyword_value(call, "primary_key")) is True
    description = str(_eval_const(_get_keyword_value(call, "description")) or "")
    max_length = _eval_const(_get_keyword_value(call, "max_length"))
    default_val = _eval_const(_get_keyword_value(call, "default"))
    unique = _eval_const(_get_keyword_value(call, "unique")) is True

    # CharEnumField / IntEnumField: 提取 enum_type
    enum_type = None
    if field_type in ("CharEnumField", "IntEnumField"):
        enum_node = _get_keyword_value(call, "enum_type")
        enum_type = str(_eval_const(enum_node)) if enum_node else None
        # 如果有 enum_type，python_type 改成该类型名
        if enum_type:
            python_type = enum_type

    return FieldInfo(
        name=name,
        field_type=field_type,
        python_type=python_type,
        description=description,
        required=not has_null and not has_default and not is_pk,
        max_length=int(str(max_length)) if max_length is not None else None,
        default=str(default_val) if default_val is not None else None,
        unique=unique,
        primary_key=is_pk,
        enum_type=enum_type,
    )


def _extract_meta(class_node: ast.ClassDef) -> dict[str, str]:
    """从 class Meta 中提取 table, table_description。"""
    meta: dict[str, str] = {}
    for node in class_node.body:
        if isinstance(node, ast.ClassDef) and node.name == "Meta":
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name) and isinstance(item.value, ast.Constant):
                            meta[target.id] = str(item.value.value)
    return meta


def _extract_docstring(class_node: ast.ClassDef) -> str:
    """提取类的 docstring。"""
    if class_node.body and isinstance(class_node.body[0], ast.Expr) and isinstance(class_node.body[0].value, ast.Constant):
        return str(class_node.body[0].value.value).strip()
    return ""


def _has_base(class_node: ast.ClassDef, base_name: str) -> bool:
    """检查类是否继承了指定基类。"""
    for base in class_node.bases:
        if isinstance(base, ast.Name) and base.id == base_name:
            return True
        if isinstance(base, ast.Attribute) and base.attr == base_name:
            return True
    return False


def parse_models(models_path: Path) -> list[ModelInfo]:
    """解析 models.py，返回所有模型定义。"""
    source = models_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    models: list[ModelInfo] = []

    for node in ast.iter_child_nodes(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        # 只处理继承了 BaseModel 的类
        if not _has_base(node, "BaseModel"):
            continue

        meta = _extract_meta(node)
        cn_name = _extract_docstring(node) or meta.get("table_description", node.name)

        model = ModelInfo(
            name=node.name,
            cn_name=cn_name,
            table=meta.get("table", ""),
            has_audit_mixin=_has_base(node, "AuditMixin"),
        )

        for item in node.body:
            # 普通赋值: name = fields.CharField(...)
            if isinstance(item, ast.Assign) and len(item.targets) == 1 and isinstance(item.targets[0], ast.Name):
                target_name = item.targets[0].id
                if isinstance(item.value, ast.Call):
                    parsed = _parse_field(target_name, item.value)
                    if isinstance(parsed, FieldInfo):
                        model.fields.append(parsed)
                    elif isinstance(parsed, RelationInfo):
                        model.relations.append(parsed)

            # 带类型注解的赋值: user: fields.ForeignKeyRelation[...] = fields.ForeignKeyField(...)
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name) and item.value and isinstance(item.value, ast.Call):
                target_name = item.target.id
                parsed = _parse_field(target_name, item.value)
                if isinstance(parsed, FieldInfo):
                    model.fields.append(parsed)
                elif isinstance(parsed, RelationInfo):
                    model.relations.append(parsed)

        models.append(model)

    return models


def collect_extra_imports(models: list[ModelInfo]) -> set[str]:
    """收集 schema 文件需要的额外 import（如 Decimal, datetime）。"""
    imports: set[str] = set()
    type_import_map = {
        "Decimal": "from decimal import Decimal",
        "datetime": "from datetime import datetime",
        "date": "from datetime import date",
        "time": "from datetime import time",
        "dict": "",
    }
    for model in models:
        for f in model.schema_fields:
            imp = type_import_map.get(f.python_type)
            if imp:
                imports.add(imp)
    imports.discard("")
    return imports
