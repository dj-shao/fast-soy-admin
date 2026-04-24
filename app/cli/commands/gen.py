"""gen 命令 — 解析 models.py 并生成 schemas / controllers / api 等文件。"""

from __future__ import annotations

import subprocess
from pathlib import Path

import click

from app.cli.generator import generate_all
from app.cli.parser import parse_models

BUSINESS_DIR = Path(__file__).resolve().parents[2] / "business"

GUIDE_TEXT = """\

\033[1;32m✅ 代码生成完成！\033[0m

\033[1;33m📋 后续步骤：\033[0m

  \033[1m1.\033[0m 按需修改 \033[36mservices.py\033[0m 中的业务逻辑
  \033[1m2.\033[0m 按需修改 \033[36minit_data.py\033[0m 添加菜单、角色、种子数据
  \033[1m3.\033[0m 执行数据库迁移：

     \033[36mmake mm\033[0m

  \033[1m4.\033[0m 启动服务验证：

     \033[36mmake dev\033[0m
"""


def _prompt_contains_fields(models: list) -> dict[str, list[str]]:
    """交互式选择每个模型的模糊搜索字段。"""
    contains_map: dict[str, list[str]] = {}
    for model in models:
        # 候选: CharField / TextField 且非 pk
        candidates = [f for f in model.schema_fields if f.field_type in ("CharField", "TextField")]
        if not candidates:
            contains_map[model.name] = []
            continue

        all_names = [f.name for f in candidates]
        default_val = ",".join(all_names)
        fields_display = " | ".join(f"\033[36m{f.name}\033[0m({f.description})" for f in candidates)
        click.echo(f"\n  模型 \033[1m{model.name}\033[0m ({model.cn_name}) 可配置的模糊搜索字段: {fields_display}")

        raw = click.prompt(
            "  选择 (逗号分隔，回车全选)",
            default=default_val,
        )
        selected = {x.strip() for x in raw.split(",")}
        contains_map[model.name] = [name for name in all_names if name in selected]

    return contains_map


@click.command()
@click.argument("module_name")
@click.option("--force", is_flag=True, help="强制覆盖已存在的文件")
@click.option("--no-format", is_flag=True, help="跳过 ruff format")
def gen(module_name: str, force: bool, no_format: bool):
    """根据 models.py 生成 schemas / controllers / api 等文件。

    MODULE_NAME: 业务模块名（app/business/<MODULE_NAME>/）
    """
    module_dir = BUSINESS_DIR / module_name
    models_path = module_dir / "models.py"

    if not module_dir.exists():
        raise click.ClickException(f"模块目录不存在: {module_dir.relative_to(BUSINESS_DIR.parent.parent)}\n  请先运行: uv run python -m app.cli init {module_name}")

    if not models_path.exists():
        raise click.ClickException(f"models.py 不存在: {models_path.relative_to(BUSINESS_DIR.parent.parent)}")

    # 1. 解析模型
    models = parse_models(models_path)
    if not models:
        raise click.ClickException("未在 models.py 中发现任何继承 BaseModel 的模型类")

    click.echo(f"\n  \033[1m✓\033[0m 解析模块: \033[36m{models_path.relative_to(BUSINESS_DIR.parent.parent)}\033[0m")
    click.echo(f"  \033[1m✓\033[0m 发现模型: {', '.join(f'{m.name} ({m.cn_name})' for m in models)}")

    # 2. 交互选择模糊搜索字段
    contains_map = _prompt_contains_fields(models)

    # 3. 生成文件
    click.echo("")
    results = generate_all(module_dir, module_name, models, contains_map, force=force)

    for rel_path, status in results:
        full_path = f"app/business/{module_name}/{rel_path}"
        if status == "created":
            click.echo(f"  \033[32m✓\033[0m {full_path}")
        elif status == "exists":
            click.echo(f"  \033[33m⚠\033[0m {full_path} (已存在，用 --force 覆盖)")
        elif status == "skipped":
            click.echo(f"  \033[90m-\033[0m {full_path} (跳过)")

    # 4. ruff check --fix + ruff format
    if not no_format:
        try:
            subprocess.run(["ruff", "check", "--fix", str(module_dir)], capture_output=True)
            subprocess.run(["ruff", "format", str(module_dir)], capture_output=True, check=True)
            click.echo("\n  \033[32m✓\033[0m ruff lint + format 完成")
        except FileNotFoundError:
            click.echo("\n  \033[33m⚠\033[0m ruff 未安装，跳过格式化")
        except subprocess.CalledProcessError:
            click.echo("\n  \033[33m⚠\033[0m ruff format 失败")

    click.echo(GUIDE_TEXT)
