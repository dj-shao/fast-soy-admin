from tortoise.expressions import Q

from app.core.base_schema import CommonIds, Success, SuccessExtra
from app.core.constants import SUPER_ADMIN_ROLE
from app.core.ctx import CTX_ROLE_CODES
from app.core.router import CRUDRouter, SearchFieldConfig
from app.core.sqids import encode_id
from app.core.types import SqidPath
from app.system.api.utils import generate_tags_recursive_list, refresh_api_list
from app.system.controllers import api_controller
from app.system.models import Api, Role
from app.system.radar.developer import radar_log
from app.system.schemas.admin import ApiCreate, ApiSearch, ApiUpdate

# 标准 CRUD：get, create, update, batch_delete（delete 被覆盖以加审计日志）
# list 被覆盖以支持权限过滤和 tag IN 查询
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
)
router = crud.router


# ---- 覆盖 list：权限过滤 + tags IN 查询 ----


@crud.override("list")
async def _list_apis(obj_in: ApiSearch):
    q = api_controller.build_search(
        obj_in,
        contains_fields=["api_path"],
        exact_fields=["summary", "status_type"],
    )
    if obj_in.tags:
        q &= Q(*[Q(tags__icontains=f"|{tag}|") for tag in obj_in.tags], join_type="OR")

    role_codes = CTX_ROLE_CODES.get()
    if SUPER_ADMIN_ROLE in role_codes:
        total, api_objs = await api_controller.list(page=obj_in.current, page_size=obj_in.size, search=q, order=["tags", "id"])
    else:
        role_objs = await Role.filter(role_code__in=role_codes).prefetch_related("by_role_apis")
        all_apis: list[Api] = []
        for role_obj in role_objs:
            all_apis.extend([api_obj for api_obj in await role_obj.by_role_apis.filter(q)])
        unique_apis = sorted(set(all_apis), key=lambda x: x.id)
        start = ((obj_in.current or 1) - 1) * (obj_in.size or 10)
        end = start + (obj_in.size or 10)
        api_objs = unique_apis[start:end]
        total = len(unique_apis)

    records = [await obj.to_dict(exclude_fields=["created_at", "updated_at"]) for obj in api_objs]
    return SuccessExtra(data={"records": records}, total=total, current=obj_in.current, size=obj_in.size)


# ---- 覆盖 create / update：tags 兼容 str|list + 审计日志 ----


@crud.override("create")
async def _create_api(api_in: ApiCreate):
    if isinstance(api_in.tags, str):
        api_in.tags = api_in.tags.split("|")
    new_api = await api_controller.create(obj_in=api_in)
    radar_log("创建API", data={"apiId": new_api.id, "apiPath": api_in.api_path, "summary": api_in.summary})
    return Success(msg="创建成功", data={"createdId": encode_id(new_api.id)})


@crud.override("update")
async def _update_api(item_id: SqidPath, obj_in: ApiUpdate):
    if isinstance(obj_in.tags, str):
        obj_in.tags = obj_in.tags.split("|")
    await api_controller.update(id=item_id, obj_in=obj_in)
    radar_log("编辑API", data={"apiId": item_id, "apiPath": obj_in.api_path, "summary": obj_in.summary})
    return Success(msg="更新成功", data={"updatedId": encode_id(item_id)})


# ---- 覆盖 delete / batch_delete：审计日志 ----


@crud.override("delete")
async def _delete_api(item_id: SqidPath):
    api_obj = await api_controller.get(id=item_id)
    radar_log("删除API", data={"apiId": item_id, "apiPath": api_obj.api_path, "summary": api_obj.summary})
    await api_controller.remove(id=item_id)
    return Success(msg="删除成功", data={"deletedId": encode_id(item_id)})


@crud.override("batch_delete")
async def _batch_delete_apis(obj_in: CommonIds):
    api_objs = await Api.filter(id__in=obj_in.ids)
    radar_log("批量删除API", data={"apiIds": obj_in.ids, "apiPaths": [a.api_path for a in api_objs]})
    deleted_count = await api_controller.batch_remove(obj_in.ids)
    return Success(msg="删除成功", data={"deletedCount": deleted_count, "deletedIds": obj_in.ids})


# ---- 扩展：API 树 / 刷新 / tags ----


def build_api_tree(apis: list[Api]):
    parent_map: dict[str, dict] = {"root": {"id": "root", "children": []}}
    for api in apis:
        tags = api.tags
        parent_id = "root"
        for tag in tags:
            node_id = f"{parent_id}>{tag}"
            if node_id not in parent_map:
                node = {"id": node_id, "summary": tag, "children": []}
                parent_map[node_id] = node
                parent_map[parent_id]["children"].append(node)
            parent_id = node_id
        parent_map[parent_id]["children"].append({
            "id": api.id,
            "summary": api.summary,
        })
    return parent_map["root"]["children"]


@router.get("/apis/tree", summary="查看API树")
async def _():
    api_objs = await Api.all()
    return Success(data=build_api_tree(api_objs) if api_objs else [])


@router.post("/apis/refresh", summary="刷新API列表")
async def _():
    await refresh_api_list()
    radar_log("刷新API列表")
    return Success()


@router.get("/apis/tags", summary="查看API tags")
async def _():
    data = await generate_tags_recursive_list()
    return Success(data=data)
