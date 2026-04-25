"""
系统 API 资源管理服务。

负责后台 `/manage/apis/*` 端点的搜索、创建、更新、删除编排，
api 层只做参数转发与响应封装。
"""

from __future__ import annotations

from tortoise.expressions import Q

from app.core.constants import SUPER_ADMIN_ROLE
from app.core.ctx import CTX_ROLE_CODES
from app.system.controllers import api_controller
from app.system.models import Api, Role
from app.system.radar.developer import radar_log
from app.system.schemas.admin import ApiCreate, ApiSearch, ApiUpdate


async def list_apis_with_scope(obj_in: ApiSearch) -> tuple[int, list[dict], int, int]:
    """API 列表：按角色权限过滤 + tags IN 查询。

    超管走全表分页；其他角色基于 `role.by_role_apis` 聚合后再分页。
    返回 (total, records, current, size)。
    """
    q = api_controller.build_search(
        obj_in,
        contains_fields=["api_path"],
        exact_fields=["summary", "status_type"],
    )
    if obj_in.tags:
        q &= Q(*[Q(tags__icontains=f"|{tag}|") for tag in obj_in.tags], join_type="OR")

    current = obj_in.current or 1
    size = obj_in.size or 10

    role_codes = CTX_ROLE_CODES.get()
    if SUPER_ADMIN_ROLE in role_codes:
        total, api_objs = await api_controller.list(page=current, page_size=size, search=q, order=["tags", "id"])
    else:
        role_objs = await Role.filter(role_code__in=role_codes).prefetch_related("by_role_apis")
        all_apis: list[Api] = []
        for role_obj in role_objs:
            all_apis.extend([api_obj for api_obj in await role_obj.by_role_apis.filter(q)])
        unique_apis = sorted(set(all_apis), key=lambda x: x.id)
        start = (current - 1) * size
        end = start + size
        api_objs = unique_apis[start:end]
        total = len(unique_apis)

    records = [await obj.to_dict(exclude_fields=["created_at", "updated_at"]) for obj in api_objs]
    return total, records, current, size


def _normalize_tags(api_in: ApiCreate | ApiUpdate) -> None:
    if isinstance(api_in.tags, str):
        api_in.tags = api_in.tags.split("|")


async def create_api(api_in: ApiCreate) -> Api:
    """创建 API 记录，并写审计日志。"""
    _normalize_tags(api_in)
    new_api = await api_controller.create(obj_in=api_in)
    radar_log("创建API", data={"apiId": new_api.id, "apiPath": api_in.api_path, "summary": api_in.summary})
    return new_api


async def update_api(api_id: int, obj_in: ApiUpdate) -> int:
    """更新 API 记录，并写审计日志。"""
    _normalize_tags(obj_in)
    await api_controller.update(id=api_id, obj_in=obj_in)
    radar_log("编辑API", data={"apiId": api_id, "apiPath": obj_in.api_path, "summary": obj_in.summary})
    return api_id


async def delete_api(api_id: int) -> int:
    """删除单条 API，并写审计日志。"""
    api_obj = await api_controller.get(id=api_id)
    radar_log("删除API", data={"apiId": api_id, "apiPath": api_obj.api_path, "summary": api_obj.summary})
    await api_controller.remove(id=api_id)
    return api_id


async def batch_delete_apis(ids: list[int]) -> tuple[int, list[int]]:
    """批量删除 API，并写审计日志。返回 (删除数, ids)。"""
    api_objs = await Api.filter(id__in=ids)
    radar_log("批量删除API", data={"apiIds": ids, "apiPaths": [a.api_path for a in api_objs]})
    deleted_count = await api_controller.batch_remove(ids)
    return deleted_count, ids


def build_api_tree(apis: list[Api]) -> list[dict]:
    """根据 tags 链构建 API 树形结构。"""
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
