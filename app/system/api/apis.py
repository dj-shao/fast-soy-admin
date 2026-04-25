from app.core.base_schema import CommonIds, Success, SuccessExtra
from app.core.router import CRUDRouter, SearchFieldConfig
from app.core.sqids import encode_id
from app.core.types import SqidPath
from app.system.api.utils import generate_tags_recursive_list
from app.system.controllers import api_controller
from app.system.models import Api
from app.system.schemas.admin import ApiCreate, ApiSearch, ApiUpdate
from app.system.services.api import (
    batch_delete_apis,
    build_api_tree,
    create_api,
    delete_api,
    list_apis_with_scope,
    update_api,
)

# 标准 CRUD：get（默认）；其余路由均覆盖以注入权限过滤、tags 兼容、审计日志
crud = CRUDRouter(
    prefix="/apis",
    controller=api_controller,
    create_schema=ApiCreate,
    update_schema=ApiUpdate,
    list_schema=ApiSearch,
    search_fields=SearchFieldConfig(
        contains_fields=["api_path"],
        exact_fields=["summary", "status_type"],
    ),
    summary_prefix="API",
    list_order=["tags", "id"],
    exclude_fields=["created_at", "updated_at"],
    enable_routes={"list", "create", "update", "delete", "batch_delete"},
)
router = crud.router


@crud.override("list")
async def _list_apis(obj_in: ApiSearch):
    total, records, current, size = await list_apis_with_scope(obj_in)
    return SuccessExtra(data={"records": records}, total=total, current=current, size=size)


@crud.override("create")
async def _create_api(api_in: ApiCreate):
    new_api = await create_api(api_in)
    return Success(msg="创建成功", data={"createdId": encode_id(new_api.id)})


@crud.override("update")
async def _update_api(item_id: SqidPath, obj_in: ApiUpdate):
    api_id = await update_api(item_id, obj_in)
    return Success(msg="更新成功", data={"updatedId": encode_id(api_id)})


@crud.override("delete")
async def _delete_api(item_id: SqidPath):
    api_id = await delete_api(item_id)
    return Success(msg="删除成功", data={"deletedId": encode_id(api_id)})


@crud.override("batch_delete")
async def _batch_delete_apis(obj_in: CommonIds):
    deleted_count, ids = await batch_delete_apis(obj_in.ids)
    return Success(msg="删除成功", data={"deletedCount": deleted_count, "deletedIds": ids})


# ---- 扩展：API 树 / tags ----


@router.get("/apis/tree", summary="查看API树")
async def _():
    api_objs = await Api.all()
    return Success(data=build_api_tree(api_objs) if api_objs else [])


@router.get("/apis/tags", summary="查看API tags")
async def _():
    data = await generate_tags_recursive_list()
    return Success(data=data)
