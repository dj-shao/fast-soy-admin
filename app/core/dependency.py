from typing import Any

import jwt
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from jwt.types import Options as JwtOptions

from app.core.cache import get_role_apis, get_user_button_codes, get_user_role_codes
from app.core.code import Code
from app.core.config import APP_SETTINGS
from app.core.constants import SUPER_ADMIN_ROLE
from app.core.ctx import CTX_BUTTON_CODES, CTX_IMPERSONATOR_ID, CTX_ROLE_CODES, CTX_USER, CTX_USER_ID, CTX_X_REQUEST_ID
from app.core.exceptions import BizError
from app.core.tools import check_url
from app.system.models import StatusType, User
from app.system.radar.ctx import CTX_RADAR
from app.system.radar.developer import radar_log

oauth2_schema = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def check_token(token: str) -> tuple[bool, str, Any]:
    try:
        options: JwtOptions = {"verify_signature": True, "verify_aud": False, "verify_exp": True}
        decode_data = jwt.decode(token, APP_SETTINGS.SECRET_KEY, algorithms=[APP_SETTINGS.JWT_ALGORITHM], options=options)
        return True, Code.SUCCESS, decode_data
    except jwt.DecodeError:
        return False, Code.INVALID_TOKEN, "无效的Token"
    except jwt.ExpiredSignatureError:
        return False, Code.TOKEN_EXPIRED, "登录已过期"
    except Exception as e:
        return False, Code.INVALID_TOKEN, f"{repr(e)}"


class AuthControl:
    @classmethod
    async def is_authed(cls, request: Request, token: str = Depends(oauth2_schema)) -> User | None:
        if not token:
            raise BizError(code=Code.INVALID_TOKEN, msg="认证失败，请求中不存在令牌")
        user_id = CTX_USER_ID.get()
        if user_id is None:
            status, code, decode_data = check_token(token)
            if not status:
                raise BizError(code=code, msg=decode_data)

            if decode_data["data"]["tokenType"] != "accessToken":
                raise BizError(code=Code.INVALID_SESSION, msg="该令牌不是访问令牌")

            user_id = decode_data["data"]["userId"]

            impersonator_id = decode_data["data"].get("impersonatorId", 0)
            if impersonator_id:
                CTX_IMPERSONATOR_ID.set(impersonator_id)

            # 校验 token 版本号
            redis = request.app.state.redis
            try:
                token_version_in_jwt = decode_data["data"].get("tokenVersion", 0)
                current_version = int(await redis.get(f"token_version:{user_id}") or 0)
                if token_version_in_jwt < current_version:
                    raise BizError(code=Code.SESSION_INVALIDATED, msg="Token已失效，请重新登录")
            except BizError:
                raise
            except Exception:
                radar_log(f"Redis unavailable during token version check for user {user_id}, skipping version validation", level="WARNING")

        user = await User.filter(id=user_id).first()
        if not user:
            raise BizError(code=Code.INVALID_SESSION, msg=f"认证失败，用户ID {user_id} 不存在")

        uid = int(user_id)
        CTX_USER_ID.set(uid)
        CTX_USER.set(user)

        # 从 Redis 加载角色、按钮权限到上下文，Redis 不可用时从数据库降级加载
        redis = request.app.state.redis
        try:
            role_codes = await get_user_role_codes(redis, uid)
            button_codes = await get_user_button_codes(redis, uid)
        except Exception:
            radar_log(f"Redis unavailable, loading permissions from database for user {uid}", level="WARNING")
            await user.fetch_related("by_user_roles")
            role_codes = [r.role_code for r in user.by_user_roles]
            button_codes = []
            for role in user.by_user_roles:
                await role.fetch_related("by_role_buttons")
                button_codes.extend([b.button_code for b in role.by_role_buttons])
        CTX_ROLE_CODES.set(role_codes)
        CTX_BUTTON_CODES.set(button_codes)

        # 写入 radar 上下文，记录操作人信息
        radar_ctx = CTX_RADAR.get()
        if radar_ctx is not None:
            radar_ctx.user_id = uid
            radar_ctx.user_name = user.user_name
        return user


class PermissionControl:
    @classmethod
    async def has_permission(cls, request: Request, current_user: User = Depends(AuthControl.is_authed)) -> None:
        role_codes = CTX_ROLE_CODES.get()
        if SUPER_ADMIN_ROLE in role_codes:
            return

        if not role_codes:
            raise BizError(code=Code.USER_NO_ROLE, msg="该用户未绑定角色")

        method = request.method.lower()
        path = request.url.path
        redis = request.app.state.redis

        # 从 Redis 汇总所有角色的 API 权限
        permission_apis: set[tuple[str, str, str]] = set()
        for role_code in role_codes:
            apis = await get_role_apis(redis, role_code)
            for api in apis:
                permission_apis.add((api["method"], api["path"], api["status"]))

        for api_method, api_path, api_status in permission_apis:
            if api_method == method and check_url(api_path, path):
                if api_status == StatusType.disable.value:
                    raise BizError(code=Code.API_DISABLED, msg=f"该接口已被禁用，method: {method} path: {path}")
                return

        radar_log("权限拒绝", level="ERROR", data={"method": method.upper(), "path": path, "xRequestId": CTX_X_REQUEST_ID.get()})
        raise BizError(code=Code.PERMISSION_DENIED, msg=f"权限不足，method: {method} path: {path}")


DependAuth = Depends(AuthControl.is_authed)
DependPermission = Depends(PermissionControl.has_permission)


def require_buttons(*button_codes: str, require_all: bool = False):
    """工厂函数：生成校验按钮权限的 FastAPI 依赖。

    用法::

        @router.post("/employees", dependencies=[require_buttons("B_HR_CREATE")])
        async def create_emp(...): ...

        # 任意一个通过即可
        @router.patch("/x", dependencies=[require_buttons("B_A", "B_B")])

        # 必须全部通过
        @router.patch("/y", dependencies=[require_buttons("B_A", "B_B", require_all=True)])

    超级管理员 (``R_SUPER``) 自动通过所有按钮权限校验，不需要单独列出。
    """

    async def _checker(_: User = Depends(AuthControl.is_authed)) -> None:
        role_codes = CTX_ROLE_CODES.get()
        if SUPER_ADMIN_ROLE in role_codes:
            return
        owned = set(CTX_BUTTON_CODES.get() or [])
        if require_all:
            missing = [c for c in button_codes if c not in owned]
            if missing:
                raise BizError(code=Code.MISSING_BUTTON_PERMISSION, msg=f"缺少按钮权限: {', '.join(missing)}")
        else:
            if not any(c in owned for c in button_codes):
                raise BizError(code=Code.NEED_ANY_BUTTON_PERMISSION, msg=f"需要任一按钮权限: {', '.join(button_codes)}")

    return Depends(_checker)


def require_roles(*role_codes_required: str, require_all: bool = False):
    """工厂函数：生成校验角色的 FastAPI 依赖。

    超级管理员 (``R_SUPER``) 自动通过。
    """

    async def _checker(_: User = Depends(AuthControl.is_authed)) -> None:
        owned = set(CTX_ROLE_CODES.get() or [])
        if SUPER_ADMIN_ROLE in owned:
            return
        if require_all:
            missing = [c for c in role_codes_required if c not in owned]
            if missing:
                raise BizError(code=Code.MISSING_ROLE, msg=f"缺少角色: {', '.join(missing)}")
        else:
            if not any(c in owned for c in role_codes_required):
                raise BizError(code=Code.NEED_ANY_ROLE, msg=f"需要任一角色: {', '.join(role_codes_required)}")

    return Depends(_checker)
