from fastapi import Request

from app.core.base_schema import CommonIds, Success, SuccessExtra
from app.core.router import CRUDRouter, SearchFieldConfig
from app.core.sqids import encode_id
from app.core.types import SqidPath
from app.system.controllers import user_controller
from app.system.schemas.users import UserCreate, UserSearch, UserUpdate
from app.system.services.auth import (
    invalidate_user_session,
    invalidate_users_by_ids,
)
from app.system.services.user import (
    create_managed_user,
    list_users_with_roles,
    update_managed_user,
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
    enable_routes={"list", "create", "update", "delete", "batch_delete"},
)
router = crud.router


@crud.override("list")
async def _list_users(obj_in: UserSearch):
    total, records, current, size = await list_users_with_roles(obj_in)
    return SuccessExtra(data={"records": records}, total=total, current=current, size=size)


@crud.override("create")
async def _create_user(user_in: UserCreate):
    new_user = await create_managed_user(user_in)
    return Success(msg="创建成功", data={"createdId": encode_id(new_user.id)})


@crud.override("update")
async def _update_user(item_id: SqidPath, obj_in: UserUpdate, request: Request):
    user_id = await update_managed_user(request.app.state.redis, item_id, obj_in)
    return Success(msg="更新成功", data={"updatedId": encode_id(user_id)})


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
