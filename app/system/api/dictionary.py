"""
系统字典管理接口 — CRUD + 按类型获取选项列表（带缓存）。
"""

from fastapi import Request

from app.core.base_schema import Success
from app.core.router import CRUDRouter, SearchFieldConfig
from app.core.sqids import encode_id
from app.core.types import SqidPath
from app.system.controllers.dictionary import dictionary_controller
from app.system.models.dictionary import Dictionary
from app.system.schemas.dictionary import DictionaryCreate, DictionarySearch, DictionaryUpdate

crud = CRUDRouter(
    prefix="/dictionaries",
    controller=dictionary_controller,
    create_schema=DictionaryCreate,
    update_schema=DictionaryUpdate,
    list_schema=DictionarySearch,
    search_fields=SearchFieldConfig(
        contains_fields=["label"],
        exact_fields=["dict_type", "status"],
    ),
    summary_prefix="字典",
    list_order=["dict_type", "order", "id"],
)

router = crud.router


@router.get("/dictionaries/{dict_type}/options", summary="获取字典选项列表")
async def get_dict_options(dict_type: str, request: Request):
    """获取指定类型的字典选项（前端下拉框）。

    结果缓存在 Redis 中（5 分钟 TTL），字典变更时自动失效。
    """
    redis = request.app.state.redis
    cache_key = f"dict_options:{dict_type}"
    import json

    cached = await redis.get(cache_key)
    if cached:
        return Success(data=json.loads(cached))

    items = await Dictionary.filter(dict_type=dict_type, status="1").order_by("order", "id")
    options = [{"label": it.label, "value": it.value} for it in items]

    await redis.set(cache_key, json.dumps(options, ensure_ascii=False), ex=300)
    return Success(data=options)


async def invalidate_dict_cache(redis, dict_type: str | None = None) -> None:
    """清除字典缓存。dict_type 为 None 时清除所有字典缓存。"""
    if dict_type:
        await redis.delete(f"dict_options:{dict_type}")
    else:
        cursor = 0
        while True:
            cursor, keys = await redis.scan(cursor=cursor, match="dict_options:*", count=100)
            if keys:
                await redis.delete(*keys)
            if cursor == 0:
                break


@crud.override("create")
async def _create_dict(obj_in: DictionaryCreate, request: Request):
    new_obj = await dictionary_controller.create(obj_in=obj_in)
    await invalidate_dict_cache(request.app.state.redis, obj_in.dict_type)
    return Success(msg="创建成功", data={"createdId": encode_id(new_obj.id)})


@crud.override("update")
async def _update_dict(item_id: SqidPath, obj_in: DictionaryUpdate, request: Request):
    old_obj = await dictionary_controller.get(id=item_id)
    await dictionary_controller.update(id=item_id, obj_in=obj_in)
    await invalidate_dict_cache(request.app.state.redis, old_obj.dict_type)
    if obj_in.dict_type and obj_in.dict_type != old_obj.dict_type:
        await invalidate_dict_cache(request.app.state.redis, obj_in.dict_type)
    return Success(msg="更新成功", data={"updatedId": encode_id(item_id)})


@crud.override("delete")
async def _delete_dict(item_id: SqidPath, request: Request):
    obj = await dictionary_controller.get(id=item_id)
    await dictionary_controller.remove(id=item_id)
    await invalidate_dict_cache(request.app.state.redis, obj.dict_type)
    return Success(msg="删除成功", data={"deletedId": encode_id(item_id)})
