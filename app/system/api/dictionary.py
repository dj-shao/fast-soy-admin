"""
系统字典管理接口 — 仅暴露按类型获取选项列表（带缓存）。
"""

import json

from fastapi import APIRouter, Request

from app.core.base_schema import Success
from app.system.models.dictionary import Dictionary

router = APIRouter()


@router.get("/dictionaries/{dict_type}/options", summary="获取字典选项列表")
async def get_dict_options(dict_type: str, request: Request):
    """获取指定类型的字典选项（前端下拉框）。

    结果缓存在 Redis 中（5 分钟 TTL）。
    """
    redis = request.app.state.redis
    cache_key = f"dict_options:{dict_type}"

    cached = await redis.get(cache_key)
    if cached:
        return Success(data=json.loads(cached))

    items = await Dictionary.filter(dict_type=dict_type, status="1").order_by("order", "id")
    options = [{"label": it.label, "value": it.value} for it in items]

    await redis.set(cache_key, json.dumps(options, ensure_ascii=False), ex=300)
    return Success(data=options)
