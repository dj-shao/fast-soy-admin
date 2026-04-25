"""
系统 API 资源管理服务。

API 资源由 ``refresh_api_list()`` 全量对账维护（启动时扫描路由），
UI 仅提供只读浏览：列表 / 树 / tags。
"""

from __future__ import annotations

from tortoise.expressions import Q

from app.core.constants import SUPER_ADMIN_ROLE
from app.core.ctx import CTX_ROLE_CODES
from app.system.controllers import api_controller
from app.system.models import Api, Role
from app.system.schemas.admin import ApiSearch


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
    # 默认只展示业务模块接口；勾选后展示全部（含系统接口）
    if not obj_in.include_system:
        q &= Q(api_path__startswith="/api/v1/business/")

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
