import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from starlette.staticfiles import StaticFiles

from app.core.autodiscover import discover_business_init_data, discover_business_routers
from app.core.cache import refresh_all_cache
from app.core.exceptions import SettingNotFound
from app.core.init_app import (
    make_middlewares,
    register_db,
    register_exceptions,
    register_routers,
)
from app.core.log import log
from app.core.redis import close_redis, init_redis
from app.system.api.utils import refresh_api_list
from app.system.init_data import init_menus, init_users
from app.system.radar import setup_radar, shutdown_radar, startup_radar

try:
    from app.core.config import APP_SETTINGS
except ImportError:
    raise SettingNotFound("Can not import settings")

# 用于协调多 worker 启动初始化的 Redis 键
_INIT_LOCK_KEY = "app:init_lock"
_INIT_DONE_KEY = "app:init_done"
_INIT_LOCK_TIMEOUT = 120  # 单位秒 — 单个 worker 持有锁的最长时间
_INIT_WAIT_TIMEOUT = 150  # 单位秒 — 其他 worker 等待初始化完成的最长时间


def create_app() -> FastAPI:
    if APP_SETTINGS.APP_DEBUG:
        _app = FastAPI(
            title=APP_SETTINGS.APP_TITLE, description=APP_SETTINGS.APP_DESCRIPTION, version=APP_SETTINGS.VERSION, openapi_url="/openapi.json", middleware=make_middlewares(), lifespan=lifespan
        )
    else:
        _app = FastAPI(title=APP_SETTINGS.APP_TITLE, description=APP_SETTINGS.APP_DESCRIPTION, version=APP_SETTINGS.VERSION, openapi_url=None, middleware=make_middlewares(), lifespan=lifespan)

    # guard_core 初始化��会添加自己的 StreamHandler（导致双��输出）并输出冗长的 pipeline 信息
    # 清掉其 handler（由根 logger 的 InterceptHandler 统一转发即可），并抑制 INFO 级别
    if APP_SETTINGS.GUARD_ENABLED:
        guard_logger = logging.getLogger("guard_core")
        guard_logger.handlers.clear()
        guard_logger.setLevel(logging.WARNING)

    register_db(_app)
    register_exceptions(_app)
    register_routers(_app, prefix="/api")

    # 自动发现并注册业务模块路由
    business_router, business_names = discover_business_routers()
    if business_router.routes:
        _app.include_router(business_router, prefix="/api/v1/business")
    _app.state.business_modules = business_names

    if APP_SETTINGS.RADAR_ENABLED:
        setup_radar(_app)
    return _app


async def _run_init_data(_app: FastAPI) -> bool:
    """初始化种子数据和缓存。多 worker 下仅由一个进程执行，其余等待完成信号。

    若当前 worker 为主导者（执行了初始化），返回 True，否则返回 False。
    """
    redis = _app.state.redis

    acquired = await redis.set(_INIT_LOCK_KEY, "1", nx=True, ex=_INIT_LOCK_TIMEOUT)

    if acquired:
        try:
            await init_menus()
            await refresh_api_list()
            await init_users()

            for init_fn in discover_business_init_data():
                try:
                    await init_fn()
                except Exception:
                    module_name = getattr(init_fn, "__module__", "unknown")
                    log.exception(f"Business: init() failed for module '{module_name}'")
                    if not hasattr(_app.state, "init_errors"):
                        _app.state.init_errors = []
                    _app.state.init_errors.append(module_name)

            await refresh_all_cache(redis)
            await redis.set(_INIT_DONE_KEY, "1", ex=_INIT_LOCK_TIMEOUT)
            return True
        except Exception:
            await redis.delete(_INIT_LOCK_KEY)
            raise
    else:
        elapsed = 0.0
        while elapsed < _INIT_WAIT_TIMEOUT:
            if await redis.exists(_INIT_DONE_KEY):
                return False
            await asyncio.sleep(0.5)
            elapsed += 0.5
        log.warning("Init wait timed out — proceeding anyway")
        return False


@asynccontextmanager
async def lifespan(_app: FastAPI):
    start_time = datetime.now()
    _app.state.redis = await init_redis()
    FastAPICache.init(RedisBackend(_app.state.redis), prefix="fastapi-cache")
    try:
        # 清除上一次启动遗留的锁（新一轮部署）
        await _app.state.redis.delete(_INIT_LOCK_KEY, _INIT_DONE_KEY)
        is_leader = await _run_init_data(_app)

        if APP_SETTINGS.RADAR_ENABLED:
            await startup_radar()

        if is_leader:
            if APP_SETTINGS.GUARD_ENABLED:
                log.info("fastapi-guard 已启动")
            for name in _app.state.business_modules:
                log.info(f"Business: registered routes from '{name}'")
            if APP_SETTINGS.RADAR_ENABLED:
                log.info("Radar: enabled")
            log.info("Init data completed")
        yield

    finally:
        if APP_SETTINGS.RADAR_ENABLED:
            await shutdown_radar()
        end_time = datetime.now()
        runtime = (end_time - start_time).total_seconds() / 60
        log.info(f"App {_app.title} runtime: {runtime} min")  # noqa
        await close_redis(_app.state.redis)


app = create_app()

app.mount("/static", StaticFiles(directory=APP_SETTINGS.STATIC_ROOT), name="static")

# 反向代理支持 — 使用 granian 提供的 wrapper 从 X-Forwarded-* 还原真实客户端 IP / 协议。
# 仅在启用且受信任主机白名单配置正确时生效；必须放在路由挂载之后、最外层。
if APP_SETTINGS.PROXY_HEADERS_ENABLED:
    from granian.utils.proxies import wrap_asgi_with_proxy_headers

    app = wrap_asgi_with_proxy_headers(app, trusted_hosts=APP_SETTINGS.TRUSTED_HOSTS)  # type: ignore[assignment]
