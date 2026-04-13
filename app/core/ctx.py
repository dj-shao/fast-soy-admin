from __future__ import annotations

import contextvars
from typing import TYPE_CHECKING

from starlette.background import BackgroundTasks

from app.core.constants import SUPER_ADMIN_ROLE

if TYPE_CHECKING:
    from app.system.models import User

CTX_USER_ID: contextvars.ContextVar[int | None] = contextvars.ContextVar("user_id", default=None)
CTX_X_REQUEST_ID: contextvars.ContextVar[str] = contextvars.ContextVar("x_request_id", default="")
CTX_BG_TASKS: contextvars.ContextVar[BackgroundTasks | None] = contextvars.ContextVar("bg_task", default=None)

CTX_USER: contextvars.ContextVar[User | None] = contextvars.ContextVar("user", default=None)
CTX_ROLE_CODES: contextvars.ContextVar[list[str]] = contextvars.ContextVar("role_codes", default=[])
CTX_BUTTON_CODES: contextvars.ContextVar[list[str]] = contextvars.ContextVar("button_codes", default=[])
CTX_IMPERSONATOR_ID: contextvars.ContextVar[int | None] = contextvars.ContextVar("impersonator_id", default=None)


def get_current_user_id() -> int:
    """获取当前请求的用户 ID，仅在已认证的上下文中调用。

    未认证时抛出 LookupError。
    """
    user_id = CTX_USER_ID.get()
    if user_id is None:
        raise LookupError("CTX_USER_ID is not set — called outside authenticated context")
    return user_id


def get_current_user() -> User | None:
    """获取当前请求的用户对象"""
    return CTX_USER.get()


def is_super_admin() -> bool:
    """判断当前用户是否是超级管理员"""
    return SUPER_ADMIN_ROLE in CTX_ROLE_CODES.get()


def has_role_code(code: str) -> bool:
    """判断当前用户是否拥有指定角色，超级管理员直接返回 True"""
    role_codes = CTX_ROLE_CODES.get()
    return SUPER_ADMIN_ROLE in role_codes or code in role_codes


def has_button_code(code: str) -> bool:
    """判断当前用户是否拥有指定按钮权限，超级管理员直接返回 True"""
    if SUPER_ADMIN_ROLE in CTX_ROLE_CODES.get():
        return True
    return code in CTX_BUTTON_CODES.get()
