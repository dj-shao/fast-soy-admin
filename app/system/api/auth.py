from fastapi import APIRouter, Request

from app.core.base_schema import Fail, Success
from app.core.code import Code
from app.core.constants import SUPER_ADMIN_ROLE
from app.core.ctx import CTX_BUTTON_CODES, CTX_IMPERSONATOR_ID, CTX_ROLE_CODES, get_current_user_id
from app.core.dependency import DependAuth, DependPermission, check_token
from app.core.exceptions import BizError
from app.core.types import SqidPath
from app.system.controllers import user_controller
from app.system.models import Button, Role, StatusType, User
from app.system.radar.developer import radar_log
from app.system.schemas.login import CaptchaRequest, CodeLoginSchema, CredentialsSchema, JWTOut, RegisterSchema
from app.system.schemas.users import UpdatePassword
from app.system.security import get_password_hash, verify_password
from app.system.services.auth import (
    build_tokens,
    get_token_version,
    impersonate_user,
    invalidate_user_session,
    login_with_credentials,
)
from app.system.services.captcha import send_captcha, verify_captcha

router = APIRouter()


@router.post("/login", summary="登录")
async def _(credentials: CredentialsSchema, request: Request):
    redis = request.app.state.redis
    user_obj, tokens = await login_with_credentials(
        redis,
        user_name=credentials.user_name,
        password=credentials.password,
    )

    radar_log("用户登录成功", data={"userName": user_obj.user_name, "userId": user_obj.id})
    result = tokens.model_dump(by_alias=True)
    result["mustChangePassword"] = user_obj.must_change_password
    return Success(data=result)


@router.get("/error", summary="错误响应测试")
async def _(code: str = "8888", msg: str = "用户状态失效，请重新登录"):
    return Fail(code=code, msg=msg)


@router.post("/captcha", summary="获取验证码")
async def _(captcha_in: CaptchaRequest, request: Request):
    redis = request.app.state.redis
    success = await send_captcha(redis, captcha_in.phone)
    if not success:
        return Fail(code=Code.CAPTCHA_SEND_FAILED, msg="验证码发送失败，请稍后重试")
    return Success(msg="验证码已发送")


@router.post("/code-login", summary="验证码登录")
async def _(login_in: CodeLoginSchema, request: Request):
    redis = request.app.state.redis

    if not await verify_captcha(redis, login_in.phone, login_in.code):
        return Fail(code=Code.CAPTCHA_INVALID, msg="验证码错误或已过期")

    user_obj = await User.filter(user_phone=login_in.phone).first()
    if not user_obj:
        return Fail(code=Code.PHONE_NOT_REGISTERED, msg="该手机号未注册")

    if user_obj.status_type == StatusType.disable:
        return Fail(code=Code.ACCOUNT_DISABLED, msg="该账号已被禁用")

    await user_controller.update_last_login(user_obj.id)

    token_version = await get_token_version(redis, user_obj.id)
    tokens = build_tokens(user_obj, token_version)

    radar_log("验证码登录成功", data={"phone": login_in.phone, "userId": user_obj.id})
    return Success(data=tokens.model_dump(by_alias=True))


@router.post("/register", summary="注册")
async def _(register_in: RegisterSchema, request: Request):
    redis = request.app.state.redis

    if not await verify_captcha(redis, register_in.phone, register_in.code):
        return Fail(code=Code.CAPTCHA_INVALID, msg="验证码错误或已过期")

    if await User.filter(user_phone=register_in.phone).exists():
        return Fail(code=Code.DUPLICATE_USER_PHONE, msg="该手机号已注册")

    user_name = register_in.user_name or register_in.phone
    if await User.filter(user_name=user_name).exists():
        return Fail(code=Code.DUPLICATE_USER_NAME, msg="该用户名已存在")

    default_role = await Role.filter(role_code="R_USER").first()
    user_obj = await User.create(
        user_name=user_name,
        password=get_password_hash(register_in.password),
        nick_name=user_name,
        user_phone=register_in.phone,
    )

    if default_role:
        await user_obj.by_user_roles.add(default_role)

    radar_log("用户注册成功", data={"phone": register_in.phone, "userName": user_name, "userId": user_obj.id})
    return Success(msg="注册成功")


@router.post("/refresh-token", summary="刷新认证")
async def _(jwt_token: JWTOut, request: Request):
    if not jwt_token.refresh_token:
        return Fail(code=Code.REFRESH_TOKEN_MISSING, msg="刷新令牌无效")
    status, code, data = check_token(jwt_token.refresh_token)
    if not status:
        return Fail(code=code, msg=data)

    user_id = data["data"]["userId"]
    user_obj = await user_controller.get(id=user_id)

    if data["data"]["tokenType"] != "refreshToken":
        return Fail(code=Code.NOT_REFRESH_TOKEN, msg="该令牌不是刷新令牌")

    if user_obj.status_type == StatusType.disable:
        radar_log("刷新令牌失败: 账号已禁用", level="WARNING", data={"userId": user_id})
        return Fail(code=Code.ACCOUNT_DISABLED, msg="该用户已被禁用")

    redis = request.app.state.redis
    token_version_in_jwt = data["data"].get("tokenVersion", 0)
    current_version = await get_token_version(redis, user_id)
    if token_version_in_jwt < current_version:
        return Fail(code=Code.SESSION_INVALIDATED, msg="Token已失效，请重新登录")

    await user_controller.update_last_login(user_id)
    impersonator_id = data["data"].get("impersonatorId") or None
    tokens = build_tokens(user_obj, current_version, impersonator_id=impersonator_id)

    radar_log("刷新令牌成功", data={"userId": user_obj.id})
    return Success(data=tokens.model_dump(by_alias=True))


@router.get("/user-info", summary="查看用户信息", dependencies=[DependAuth])
async def _():
    user_id = get_current_user_id()
    user_obj: User = await user_controller.get(id=user_id)
    data = await user_obj.to_dict(exclude_fields=["id", "password", "created_at", "updated_at", "created_by", "updated_by"])

    role_codes = CTX_ROLE_CODES.get()
    button_codes = [b.button_code for b in await Button.all()] if SUPER_ADMIN_ROLE in role_codes else CTX_BUTTON_CODES.get()

    data.update({"userId": user_id, "roles": role_codes, "buttons": button_codes})

    impersonator_id = CTX_IMPERSONATOR_ID.get()
    if impersonator_id:
        data["impersonating"] = True
        data["impersonatorId"] = impersonator_id

    radar_log("获取用户信息", data={"userId": user_obj.id})
    return Success(data=data)


@router.patch("/password", summary="修改密码", dependencies=[DependAuth])
async def _(body: UpdatePassword, request: Request):
    user_id = get_current_user_id()
    user_obj = await user_controller.get(id=user_id)

    if not verify_password(body.old_password, user_obj.password):
        return Fail(code=Code.OLD_PASSWORD_WRONG, msg="原密码错误")

    await User.filter(id=user_id).update(
        password=get_password_hash(body.new_password),
        must_change_password=False,
    )

    # 递增 token_version 使旧 token 失效
    await invalidate_user_session(request.app.state.redis, user_id)

    radar_log("修改密码", data={"userId": user_id})
    return Success(msg="密码修改成功，请重新登录")


@router.post("/impersonate/{user_id}", summary="模拟登录", dependencies=[DependPermission])
async def _(user_id: SqidPath, request: Request):
    """超级管理员模拟登录为指定用户，无需密码"""
    role_codes = CTX_ROLE_CODES.get()
    if SUPER_ADMIN_ROLE not in role_codes:
        return Fail(code=Code.SUPER_ADMIN_ONLY, msg="仅超级管理员可以模拟登录")

    impersonator_id = get_current_user_id()
    try:
        tokens = await impersonate_user(
            request.app.state.redis,
            target_user_id=user_id,
            impersonator_id=impersonator_id,
        )
    except BizError as e:
        return Fail(code=e.code, msg=e.msg)

    radar_log("管理员模拟登录", data={"impersonatorId": impersonator_id, "targetUserId": user_id})
    return Success(data=tokens.model_dump(by_alias=True))
