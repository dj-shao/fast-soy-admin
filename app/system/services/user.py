"""
系统用户服务。

这里放置 system 领域自己的用户编排逻辑。
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass

from redis.asyncio import Redis
from tortoise.expressions import Q
from tortoise.transactions import in_transaction

from app.core.cache import refresh_user_roles
from app.core.code import Code
from app.core.crud import get_db_conn
from app.core.exceptions import BizError
from app.system.controllers import role_controller
from app.system.controllers.user import UserCreate, user_controller
from app.system.models import User
from app.system.schemas.users import UserSearch, UserUpdate
from app.system.services.auth import invalidate_user_session


@dataclass
class CreateUserResult:
    user: User
    raw_password: str


async def create_system_user(
    redis: Redis,
    *,
    user_name: str,
    nick_name: str,
    user_email: str,
    user_gender: str | None = None,
    user_phone: str | None = None,
    role_codes: list[str] | None = None,
) -> CreateUserResult:
    """
    创建系统用户。

    - 自动生成随机密码
    - 设置 must_change_password = True
    - 分配角色（默认 R_USER）
    - 刷新 Redis 缓存

    Returns:
        CreateUserResult(user, raw_password)

    Raises:
        ValueError: 用户名或邮箱已存在
    """
    if await user_controller.get_by_username(user_name):
        raise ValueError(f"用户名 {user_name} 已存在")
    if await user_controller.get_by_email(user_email):
        raise ValueError(f"邮箱 {user_email} 已被使用")

    raw_password = secrets.token_urlsafe(10)

    new_user = await user_controller.create(
        UserCreate.model_validate({
            "user_name": user_name,
            "nick_name": nick_name,
            "user_email": user_email,
            "user_gender": user_gender,
            "user_phone": user_phone,
            "password": raw_password,
            "by_user_role_code_list": role_codes or ["R_USER"],
        })
    )

    await User.filter(id=new_user.id).update(must_change_password=True)

    for code in role_codes or ["R_USER"]:
        role = await role_controller.get_by_code(code)
        if role:
            await new_user.by_user_roles.add(role)

    await refresh_user_roles(redis, new_user.id)

    return CreateUserResult(user=new_user, raw_password=raw_password)


# ---- 后台用户管理（api/users.py 调用入口）----


async def list_users_with_roles(obj_in: UserSearch) -> tuple[int, list[dict], int, int]:
    """后台用户列表：搜索 + 角色编码列表回填。

    返回 (total, records, current, size)。
    """
    q = user_controller.build_search(
        obj_in,
        contains_fields=["user_name", "nick_name", "user_phone", "user_email"],
        exact_fields=["user_gender", "status_type"],
    )
    if obj_in.by_user_role_code_list:
        q &= Q(by_user_roles__role_code__in=obj_in.by_user_role_code_list)

    current = obj_in.current or 1
    size = obj_in.size or 10
    total, user_objs = await user_controller.list(page=current, page_size=size, search=q, order=["id"])

    records: list[dict] = []
    for user_obj in user_objs:
        record = await user_obj.to_dict(exclude_fields=["password"])
        await user_obj.fetch_related("by_user_roles")
        record["byUserRoleCodeList"] = [r.role_code for r in user_obj.by_user_roles]
        records.append(record)
    return total, records, current, size


async def create_managed_user(user_in: UserCreate) -> User:
    """后台创建用户：邮箱唯一性 + 事务内建用户并关联角色。"""
    assert user_in.user_email is not None  # schema validator 保证
    assert user_in.by_user_role_code_list is not None

    if await user_controller.get_by_email(user_in.user_email):
        raise BizError(code=Code.DUPLICATE_USER_EMAIL, msg="该邮箱已被注册")

    async with in_transaction(get_db_conn(User)):
        new_user = await user_controller.create(obj_in=user_in)
        await user_controller.update_roles_by_code(new_user, user_in.by_user_role_code_list)

    return new_user


async def update_managed_user(redis: Redis, user_id: int, obj_in: UserUpdate) -> int:
    """后台更新用户：事务内更新 + 角色重绑；密码变更则失效 session。"""
    assert obj_in.by_user_role_code_list is not None

    async with in_transaction(get_db_conn(User)):
        user = await user_controller.update(user_id=user_id, obj_in=obj_in)
        await user_controller.update_roles_by_code(user, obj_in.by_user_role_code_list)

    if obj_in.password:
        await invalidate_user_session(redis, user_id)

    return user_id
