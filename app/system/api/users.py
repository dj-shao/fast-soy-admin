from fastapi import Request
from tortoise.expressions import Q
from tortoise.transactions import in_transaction

from app.core.base_schema import CommonIds, Fail, OfflineByRoleRequest, Success, SuccessExtra
from app.core.code import Code
from app.core.crud import get_db_conn
from app.core.router import CRUDRouter, SearchFieldConfig
from app.core.sqids import encode_id
from app.core.types import SqidPath
from app.system.controllers import user_controller
from app.system.models import User
from app.system.schemas.users import UserCreate, UserSearch, UserUpdate
from app.system.services.auth import (
    invalidate_user_session,
    invalidate_users_by_ids,
    invalidate_users_by_role_codes,
)

# 标准 CRUD：list(POST /search), get, delete, batch_delete
# create / update 使用 override 注入密码哈希和角色关联逻辑
crud = CRUDRouter(
    prefix="/users",
    controller=user_controller,
    create_schema=UserCreate,
    update_schema=UserUpdate,
    list_schema=UserSearch,
    search_fields=SearchFieldConfig(
        contains_fields=["user_name", "nick_name", "user_phone", "user_email"],
        exact_fields=["user_gender", "status_type"],
    ),
    summary_prefix="用户",
    exclude_fields=["password"],
)
router = crud.router


# ---- 覆盖 list：需要 join role 查询 + 返回角色编码列表 ----


@crud.override("list")
async def _list_users(obj_in: UserSearch):
    q = user_controller.build_search(
        obj_in,
        contains_fields=["user_name", "nick_name", "user_phone", "user_email"],
        exact_fields=["user_gender", "status_type"],
    )
    if obj_in.by_user_role_code_list:
        q &= Q(by_user_roles__role_code__in=obj_in.by_user_role_code_list)

    total, user_objs = await user_controller.list(page=obj_in.current, page_size=obj_in.size, search=q, order=["id"])
    records = []
    for user_obj in user_objs:
        record = await user_obj.to_dict(exclude_fields=["password"])
        await user_obj.fetch_related("by_user_roles")
        record["byUserRoleCodeList"] = [r.role_code for r in user_obj.by_user_roles]
        records.append(record)
    return SuccessExtra(data={"records": records}, total=total, current=obj_in.current, size=obj_in.size)


# ---- 覆盖 create：需要事务 + 邮箱唯一性 + 角色关联 ----


@crud.override("create")
async def _create_user(user_in: UserCreate):
    assert user_in.user_email is not None  # schema validator 保证
    assert user_in.by_user_role_code_list is not None

    if await user_controller.get_by_email(user_in.user_email):
        return Fail(code=Code.DUPLICATE_USER_EMAIL, msg="该邮箱已被注册")

    async with in_transaction(get_db_conn(User)):
        new_user = await user_controller.create(obj_in=user_in)
        await user_controller.update_roles_by_code(new_user, user_in.by_user_role_code_list)

    return Success(msg="创建成功", data={"createdId": encode_id(new_user.id)})


# ---- 覆盖 update：密码变更需失效 session ----


@crud.override("update")
async def _update_user(item_id: SqidPath, obj_in: UserUpdate, request: Request):
    assert obj_in.by_user_role_code_list is not None

    async with in_transaction(get_db_conn(User)):
        user = await user_controller.update(user_id=item_id, obj_in=obj_in)
        await user_controller.update_roles_by_code(user, obj_in.by_user_role_code_list)

    if obj_in.password:
        await invalidate_user_session(request.app.state.redis, item_id)

    return Success(msg="更新成功", data={"updatedId": encode_id(item_id)})


# ---- 扩展：下线接口 ----


@router.post("/users/{user_id}/offline", summary="用户下线")
async def _(user_id: SqidPath, request: Request):
    """强制单个用户下线"""
    await invalidate_user_session(request.app.state.redis, user_id)
    return Success(msg="操作成功")


@router.post("/users/batch-offline", summary="批量用户下线")
async def _(obj_in: CommonIds, request: Request):
    """按用户 id 列表批量下线"""
    await invalidate_users_by_ids(request.app.state.redis, obj_in.ids)
    return Success(msg="操作成功", data={"offlineCount": len(obj_in.ids)})


@router.post("/users/offline-by-role", summary="按角色下线用户")
async def _(obj_in: OfflineByRoleRequest, request: Request):
    """按角色编码批量下线所有关联用户"""
    count = await invalidate_users_by_role_codes(request.app.state.redis, obj_in.role_codes)
    return Success(msg="操作成功", data={"offlineCount": count})
