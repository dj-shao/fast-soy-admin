"""
系统认证服务 —— token 构建、session 失效、登录编排、impersonation。

API 层只做 HTTP 适配，凡是涉及 Redis、token_version 双写、多模型事务的
逻辑都应该通过这里调用。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from redis.asyncio import Redis

from app.core.code import Code
from app.core.config import APP_SETTINGS
from app.core.exceptions import BizError
from app.system.controllers import user_controller
from app.system.models import StatusType, User
from app.system.radar.developer import radar_log
from app.system.schemas.login import CredentialsSchema, JWTOut, JWTPayload
from app.system.security import create_access_token

# ---------------------------------------------------------------------------
# Token 构建
# ---------------------------------------------------------------------------


def build_tokens(user_obj: User, token_version: int, *, impersonator_id: int | None = None) -> JWTOut:
    """构建 access_token + refresh_token。"""
    data: dict = {
        "userId": user_obj.id,
        "userName": user_obj.user_name,
        "tokenType": "accessToken",
        "tokenVersion": token_version,
    }
    if impersonator_id is not None:
        data["impersonatorId"] = impersonator_id
    payload = JWTPayload(data=data, iat=datetime.now(UTC), exp=datetime.now(UTC))

    access_payload = payload.model_copy(deep=True)
    access_payload.exp += timedelta(minutes=APP_SETTINGS.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_payload = payload.model_copy(deep=True)
    refresh_payload.data["tokenType"] = "refreshToken"
    refresh_payload.exp += timedelta(minutes=APP_SETTINGS.JWT_REFRESH_TOKEN_EXPIRE_MINUTES)

    return JWTOut(
        token=create_access_token(data=access_payload),
        refresh_token=create_access_token(data=refresh_payload),
    )


async def get_token_version(redis: Redis, user_id: int) -> int:
    """读取 Redis 中的 token_version（未设置时返回 0）。"""
    return int(await redis.get(f"token_version:{user_id}") or 0)


# ---------------------------------------------------------------------------
# Session 失效
# ---------------------------------------------------------------------------


async def invalidate_user_session(redis: Redis, user_id: int) -> int:
    """递增单个用户的 token_version，使其已签发的 access/refresh token 全部失效。

    DB + Redis 双写，返回新的 token_version。
    """
    user = await User.get(id=user_id)
    user.token_version += 1
    await user.save(update_fields=["token_version"])
    await redis.set(f"token_version:{user_id}", user.token_version)
    return user.token_version


async def invalidate_users_by_ids(redis: Redis, user_ids: list[int]) -> int:
    """按用户 id 列表批量失效 session，返回处理成功的条数。"""
    count = 0
    for uid in user_ids:
        await invalidate_user_session(redis, int(uid))
        count += 1
    return count


async def invalidate_users_by_role_codes(redis: Redis, role_codes: list[str]) -> int:
    """失效所有绑定了指定角色编码的用户 session，返回被下线的用户数。"""
    users = await User.filter(by_user_roles__role_code__in=role_codes).distinct()
    for user in users:
        await invalidate_user_session(redis, user.id)
    return len(users)


# ---------------------------------------------------------------------------
# 模拟登录（Impersonation）
# ---------------------------------------------------------------------------


async def impersonate_user(redis: Redis, *, target_user_id: int, impersonator_id: int) -> JWTOut:
    """为目标用户生成一对 token，并在 payload 中写入 impersonatorId。

    调用方负责校验 impersonator 是否有超管权限。
    """
    target = await User.filter(id=target_user_id).first()
    if not target:
        raise BizError(code=Code.TARGET_USER_NOT_FOUND, msg="目标用户不存在")
    if target.status_type == StatusType.disable:
        raise BizError(code=Code.ACCOUNT_DISABLED, msg="目标用户已被禁用")

    token_version = await get_token_version(redis, target.id)
    tokens = build_tokens(target, token_version, impersonator_id=impersonator_id)
    radar_log(
        "管理员模拟登录",
        data={"impersonatorId": impersonator_id, "targetUserId": target.id, "targetUserName": target.user_name},
    )
    return tokens


# ---------------------------------------------------------------------------
# 登录编排
# ---------------------------------------------------------------------------


async def login_with_credentials(
    redis: Redis,
    *,
    user_name: str | None,
    password: str | None,
) -> tuple[User, JWTOut]:
    """校验密码 + 更新 last_login + 构建 tokens。失败抛 BizError。"""
    user = await user_controller.authenticate(CredentialsSchema(user_name=user_name, password=password))
    await user_controller.update_last_login(user.id)
    token_version = await get_token_version(redis, user.id)
    tokens = build_tokens(user, token_version)
    return user, tokens
