"""E2E 用：直接从当前模型生成 schema，不走迁移、不污染 migrations/ 目录。

需要外部已设置 DB_URL 指向 e2e 专用的库（默认配置里指向 PG/线上库时千万别误用）。
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tortoise import Tortoise  # noqa: E402

from app.core.config import APP_SETTINGS  # noqa: E402


async def main() -> None:
    db_url = APP_SETTINGS.DB_URL
    if "e2e" not in db_url:
        sys.exit(f"[e2e_init_db] 拒绝执行：DB_URL 未包含 'e2e' 标记，当前={db_url!r}")

    await Tortoise.init(config=APP_SETTINGS.TORTOISE_ORM)
    await Tortoise.generate_schemas(safe=True)
    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
