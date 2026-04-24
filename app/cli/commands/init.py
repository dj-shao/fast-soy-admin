"""init 命令 — 创建业务模块目录骨架，生成初始 models.py 并输出引导提示。"""

from __future__ import annotations

import re
from pathlib import Path

import click

BUSINESS_DIR = Path(__file__).resolve().parents[2] / "business"

MODELS_TEMPLATE = '''\
# pyright: reportIncompatibleVariableOverride=false
"""
{cn_name} — 业务模型定义。

在此文件中定义 Tortoise ORM 模型，完成后运行:

    make cli-gen-all MOD={module_name} CN={cn_name}

即可一次生成后端 schemas / controllers / api 及前端 service / views / i18n 等文件。
"""

from tortoise import fields

from app.utils import AuditMixin, BaseModel, StatusType


# ---- 在下方定义你的模型 ----
#
# class Example(BaseModel, AuditMixin):
#     """示例"""
#
#     id = fields.IntField(primary_key=True)
#     name = fields.CharField(max_length=100, description="名称")
#     status = fields.CharEnumField(enum_type=StatusType, default=StatusType.enable, description="状态")
#
#     # 外键规范：必须在 FK 字段上方声明 <name>_id: int（非空）或 int | None（可空）
#     # 使用时创建/更新/比较一律用 parent_id，访问关系对象字段前先 prefetch_related("parent")。
#     # parent_id: int | None
#     # parent: fields.ForeignKeyNullableRelation["Example"] = fields.ForeignKeyField(
#     #     "app_{module_name}.Example", null=True, related_name="children", description="父节点",
#     # )
#
#     class Meta:
#         table = "biz_{module_name}_example"
#         table_description = "示例"
'''

GUIDE_TEXT = """\

\033[1;32m✅ 模块 {module_name} 创建成功！\033[0m

  📂 {module_path}/
     ├── __init__.py
     └── models.py          ← 请在这里定义你的模型

\033[1;33m📋 下一步：\033[0m

  \033[1m1.\033[0m 用编辑器打开 \033[36m{models_path}\033[0m
     参照注释中的示例，定义你的 Tortoise ORM 模型。

     几个要点：
     • 继承 \033[36mBaseModel, AuditMixin\033[0m
     • 每个字段加上 \033[36mdescription="..."\033[0m（用于生成 schema 注释）
     • 类的 docstring 写中文名（如 \033[36m\"\"\"仓库\"\"\"\033[0m），将作为 API summary 前缀
     • Meta.table 建议用 \033[36mbiz_{module_name}_xxx\033[0m 前缀
     • 外键字段上方必须声明 \033[36m<name>_id: int\033[0m（或 \033[36mint | None\033[0m）注解；
       使用时一律用 \033[36mobj.<name>_id\033[0m，访问关系对象字段前先 \033[36mprefetch_related(...)\033[0m

  \033[1m2.\033[0m 模型写好后，运行代码生成（后端 + 前端 CRUD 一次生成）：

     \033[36mmake cli-gen-all MOD={module_name} CN={cn_name}\033[0m

     将自动生成后端 schemas.py / controllers.py / services.py / api/，
     以及前端 service / typings / views / i18n 等文件。

  \033[1m3.\033[0m 生成后执行数据库迁移：

     \033[36mmake mm\033[0m

  \033[1m4.\033[0m 启动服务验证：

     \033[36mmake run\033[0m
"""


def _validate_module_name(_ctx: click.Context, _param: click.Parameter, value: str) -> str:
    if not re.match(r"^[a-z][a-z0-9_]*$", value):
        raise click.BadParameter("模块名只能包含小写字母、数字和下划线，且以字母开头")
    if value.startswith("_"):
        raise click.BadParameter("以 _ 开头的目录会被 autodiscover 跳过")
    return value


@click.command()
@click.argument("module_name", callback=_validate_module_name)
@click.option("--cn-name", prompt="模块中文名", help="模块中文名（如：库存管理）")
def init(module_name: str, cn_name: str):
    """创建业务模块目录骨架。

    MODULE_NAME: 模块名（snake_case），将创建到 app/business/<MODULE_NAME>/
    """
    module_dir = BUSINESS_DIR / module_name

    if module_dir.exists():
        raise click.ClickException(f"模块目录已存在: {module_dir.relative_to(BUSINESS_DIR.parent.parent)}")

    # 创建目录
    module_dir.mkdir(parents=True)

    # __init__.py
    (module_dir / "__init__.py").write_text("", encoding="utf-8")

    # models.py
    models_content = MODELS_TEMPLATE.format(module_name=module_name, cn_name=cn_name)
    (module_dir / "models.py").write_text(models_content, encoding="utf-8")

    # 输出引导
    click.echo(
        GUIDE_TEXT.format(
            module_name=module_name,
            cn_name=cn_name,
            module_path=module_dir.relative_to(BUSINESS_DIR.parent.parent),
            models_path=(module_dir / "models.py").relative_to(BUSINESS_DIR.parent.parent),
        )
    )
