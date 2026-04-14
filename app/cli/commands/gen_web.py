"""gen-web 命令 — 根据 models.py 生成前端 service / typings / views / i18n。"""

from __future__ import annotations

import subprocess
from pathlib import Path

import click

from app.cli.parser import parse_models
from app.cli.web_generator import generate_web

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BUSINESS_DIR = PROJECT_ROOT / "app" / "business"
WEB_ROOT = PROJECT_ROOT / "web"

GUIDE = """\

\033[1;32m✅ 前端代码生成完成！\033[0m

\033[1;33m📋 后续步骤：\033[0m

  \033[1m1.\033[0m 按提示合并 i18n 片段到 zh-cn.ts / en-us.ts：
     \033[36mweb/src/locales/langs/_generated/{module}/zh-cn.ts\033[0m
     \033[36mweb/src/locales/langs/_generated/{module}/en-us.ts\033[0m

  \033[1m2.\033[0m 搜索生成代码中的 \033[33mTODO\033[0m 注释，补充外键 / 枚举的 options 数据源

  \033[1m3.\033[0m 启动前端验证：

     \033[36mcd web && pnpm dev\033[0m
"""


def _prompt_fields(models, label: str, candidates_fn) -> dict[str, list[str]]:
    """通用字段选择交互。"""
    result: dict[str, list[str]] = {}
    for model in models:
        candidates = candidates_fn(model)
        if not candidates:
            result[model.name] = []
            continue
        all_names = [f.name for f in candidates]
        default_val = ",".join(all_names)
        display = " | ".join(f"\033[36m{f.name}\033[0m({f.description or f.name})" for f in candidates)
        click.echo(f"\n  模型 \033[1m{model.name}\033[0m ({model.cn_name}) 可配置的{label}: {display}")
        raw = click.prompt(f"  选择{label} (逗号分隔，回车全选)", default=default_val)
        selected = {x.strip() for x in raw.split(",")}
        result[model.name] = [name for name in all_names if name in selected]
    return result


def _format_generated_files(results: list[tuple[str, str]]) -> None:
    """对生成/追加的前端文件执行 oxfmt 格式化 + eslint --fix。"""
    targets = [
        str(WEB_ROOT / rel_path)
        for rel_path, status in results
        if status in ("created", "appended")
    ]
    if not targets:
        return

    # oxfmt 格式化
    try:
        subprocess.run(
            ["pnpm", "exec", "oxfmt", *targets],
            cwd=WEB_ROOT,
            capture_output=True,
            check=True,
        )
        click.echo("\n  \033[32m✓\033[0m oxfmt 格式化完成")
    except FileNotFoundError:
        click.echo("\n  \033[33m⚠\033[0m pnpm 未找到，跳过格式化")
        return
    except subprocess.CalledProcessError as e:
        click.echo(f"\n  \033[33m⚠\033[0m oxfmt 失败: {e.stderr.decode(errors='ignore')[:200]}")

    # eslint --fix 修复 import 排序等
    try:
        subprocess.run(
            ["pnpm", "exec", "eslint", "--fix", *targets],
            cwd=WEB_ROOT,
            capture_output=True,
            check=False,  # eslint 有警告也会返回非零，不 raise
        )
        click.echo("  \033[32m✓\033[0m eslint --fix 完成")
    except FileNotFoundError:
        pass


@click.command()
@click.argument("module_name")
@click.option("--cn-name", default=None, help="模块中文名（用于 i18n）")
@click.option("--force", is_flag=True, help="强制覆盖已存在的文件")
@click.option("--no-format", is_flag=True, help="跳过前端格式化")
def gen_web(module_name: str, cn_name: str | None, force: bool, no_format: bool):
    """根据 models.py 生成前端代码（service / typings / views / i18n）。"""
    module_dir = BUSINESS_DIR / module_name
    models_path = module_dir / "models.py"

    if not models_path.exists():
        raise click.ClickException(f"找不到 {models_path.relative_to(PROJECT_ROOT)}\n  请先运行: python -m app.cli init {module_name}")

    if not WEB_ROOT.exists():
        raise click.ClickException(f"找不到前端目录 {WEB_ROOT}")

    # 1. 解析模型
    models = parse_models(models_path)
    if not models:
        raise click.ClickException("未在 models.py 中发现任何继承 BaseModel 的模型类")

    click.echo(f"\n  \033[1m✓\033[0m 解析模块: \033[36m{models_path.relative_to(PROJECT_ROOT)}\033[0m")
    click.echo(f"  \033[1m✓\033[0m 发现模型: {', '.join(f'{m.name} ({m.cn_name})' for m in models)}")

    # 2. 模块中文名
    module_cn: str = cn_name or click.prompt("\n  模块中文名 (用于 i18n)", default=module_name)

    # 3. 列表展示字段
    list_fields = _prompt_fields(
        models,
        "列表展示字段",
        lambda m: [f for f in m.schema_fields if f.field_type not in ("TextField",)][:6],
    )

    # 4. 搜索字段
    search_fields = _prompt_fields(
        models,
        "搜索字段",
        lambda m: [f for f in m.schema_fields if f.field_type in ("CharField", "TextField") or f.enum_type],
    )

    # 5. 生成
    click.echo("")
    results = generate_web(
        WEB_ROOT,
        module_name,
        module_cn,
        models,
        list_fields_map=list_fields,
        search_fields_map=search_fields,
        force=force,
    )

    for rel_path, status in results:
        full = f"web/{rel_path}"
        if status == "created":
            click.echo(f"  \033[32m✓\033[0m {full}")
        elif status == "appended":
            click.echo(f"  \033[32m✓\033[0m {full} (已追加 export)")
        elif status == "exists":
            click.echo(f"  \033[33m⚠\033[0m {full} (已存在，用 --force 覆盖)")
        elif status == "not-found":
            click.echo(f"  \033[31m✗\033[0m {full} (文件不存在，请手动处理)")

    # 6. 格式化
    if not no_format:
        _format_generated_files(results)

    click.echo(GUIDE.format(module=module_name))
