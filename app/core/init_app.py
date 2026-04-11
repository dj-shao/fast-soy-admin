import orjson
import pretty_errors
from fastapi import FastAPI
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from guard import SecurityConfig
from guard.middleware import SecurityMiddleware
from starlette.responses import Response
from tortoise.contrib.fastapi import register_tortoise

from app.core.code import Code
from app.core.config import APP_SETTINGS
from app.core.exceptions import (
    BizError,
    BizErrorHandle,
    DoesNotExist,
    DoesNotExistHandle,
    IntegrityError,
    IntegrityHandle,
    RequestValidationError,
    RequestValidationHandle,
    ResponseValidationError,
    ResponseValidationHandle,
)
from app.core.middlewares import BackGroundTaskMiddleware, PrettyErrorsMiddleware, RequestIDMiddleware
from app.system.api import system_router
from app.system.api.health import router as health_router
from app.system.radar.middleware import RadarMiddleware


async def _guard_response_modifier(response):
    """将 guard 的错误响应改写为项目统一的 JSON 格式。"""
    status = response.status_code
    if status < 400:
        return response
    if status in (404, 405):
        return response  # 正常路由错误直接透传，不伪装为安全拦截
    if status == 429:
        code, msg = Code.RATE_LIMITED, "请求过于频繁，请稍后再试"
    elif status == 403 and b"banned" in (response.body or b"").lower():
        code, msg = Code.IP_BANNED, "IP已被封禁，请稍后再试"
    elif status == 403:
        code, msg = Code.ACCESS_DENIED, "访问被拒绝"
    else:
        code, msg = Code.ACCESS_DENIED, "请求被安全策略拦截"
    body = orjson.dumps({"code": code, "msg": msg, "data": None})
    response._response = Response(content=body, status_code=200, media_type="application/json")
    return response


def _make_guard_config():
    """根据应用配置构建 fastapi-guard 的 SecurityConfig。"""
    return SecurityConfig(
        rate_limit=APP_SETTINGS.GUARD_RATE_LIMIT,
        rate_limit_window=APP_SETTINGS.GUARD_RATE_LIMIT_WINDOW,
        auto_ban_threshold=APP_SETTINGS.GUARD_AUTO_BAN_THRESHOLD,
        auto_ban_duration=APP_SETTINGS.GUARD_AUTO_BAN_DURATION,
        enable_redis=True,
        redis_url=APP_SETTINGS.REDIS_URL,
        enable_cors=False,  # CORS 已由 CORSMiddleware 处理
        enforce_https=False,
        security_headers=None,  # 安全响应头由 nginx 处理
        custom_log_file=str(APP_SETTINGS.LOGS_ROOT / "guard.log"),
        custom_response_modifier=_guard_response_modifier,
        exclude_paths=["/docs", "/redoc", "/openapi.json", "/favicon.ico", "/static"],
        endpoint_rate_limits={
            "/api/v1/auth/login": (5, 60),  # 每 60 秒最多 5 次请求
            "/api/v1/auth/refresh-token": (10, 60),  # 每 60 秒最多 10 次请求
        },
    )


def make_middlewares():
    middleware = [
        Middleware(
            PrettyErrorsMiddleware,
            line_number_first=True,
            lines_before=5,
            lines_after=2,
            line_color=pretty_errors.RED + "> " + pretty_errors.default_config.line_color,
            code_color="  " + pretty_errors.default_config.line_color,
            truncate_code=True,
            display_locals=True,
            filename_display=pretty_errors.FILENAME_EXTENDED,
        ),
        Middleware(
            CORSMiddleware,
            allow_origins=APP_SETTINGS.CORS_ORIGINS,
            allow_credentials=APP_SETTINGS.CORS_ALLOW_CREDENTIALS,
            allow_methods=APP_SETTINGS.CORS_ALLOW_METHODS,
            allow_headers=APP_SETTINGS.CORS_ALLOW_HEADERS,
        ),
        Middleware(BackGroundTaskMiddleware),
        Middleware(RequestIDMiddleware),
    ]
    if APP_SETTINGS.GUARD_ENABLED:
        middleware.append(Middleware(SecurityMiddleware, config=_make_guard_config()))

    if APP_SETTINGS.RADAR_ENABLED:
        middleware.append(Middleware(RadarMiddleware))
    return middleware


def register_db(app: FastAPI):
    register_tortoise(
        app,
        config=APP_SETTINGS.TORTOISE_ORM,
        generate_schemas=False,
    )


def register_exceptions(app: FastAPI):
    app.add_exception_handler(DoesNotExist, DoesNotExistHandle)
    app.add_exception_handler(BizError, BizErrorHandle)  # type: ignore
    app.add_exception_handler(IntegrityError, IntegrityHandle)
    app.add_exception_handler(RequestValidationError, RequestValidationHandle)  # type: ignore
    app.add_exception_handler(ResponseValidationError, ResponseValidationHandle)  # type: ignore


def register_routers(app: FastAPI, prefix: str = "/api"):
    app.include_router(system_router, prefix=f"{prefix}/v1")
    app.include_router(health_router)
