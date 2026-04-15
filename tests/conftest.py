from contextlib import asynccontextmanager

import pytest_asyncio
from fakeredis import aioredis as fake_aioredis
from httpx import ASGITransport, AsyncClient
from tortoise import Tortoise

TEST_TORTOISE_ORM = {
    "connections": {
        "conn_system": "sqlite://:memory:",
    },
    "apps": {
        "app_system": {
            "models": ["app.system.models", "app.system.radar.models", "app.business.hr.models"],
            "default_connection": "conn_system",
        }
    },
    "use_tz": False,
    "timezone": "Asia/Shanghai",
}


# ===================== App Factory =====================


def _create_test_app():
    """Create a FastAPI app for testing, bypassing Redis and migrations."""
    from app.core.config import APP_SETTINGS

    APP_SETTINGS.TORTOISE_ORM = TEST_TORTOISE_ORM
    APP_SETTINGS.GUARD_ENABLED = False
    APP_SETTINGS.RADAR_ENABLED = False

    @asynccontextmanager
    async def test_lifespan(_app):
        yield

    from fastapi import FastAPI

    from app.core.init_app import make_middlewares, register_exceptions, register_routers

    _app = FastAPI(
        title=APP_SETTINGS.APP_TITLE,
        description=APP_SETTINGS.APP_DESCRIPTION,
        version=APP_SETTINGS.VERSION,
        openapi_url="/openapi.json",
        middleware=make_middlewares(),
        lifespan=test_lifespan,
    )
    register_exceptions(_app)
    register_routers(_app, prefix="/api")

    # Business module routes
    from app.core.autodiscover import discover_business_routers

    business_router, _ = discover_business_routers()
    if business_router.routes:
        _app.include_router(business_router, prefix="/api/v1/business")

    # Radar API routes
    from app.system.radar.api import router as radar_router

    _app.include_router(radar_router)

    return _app


# ===================== Core Fixtures =====================
# All fixtures use loop_scope="session" to share the same event loop and in-memory DB.


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def app():
    await Tortoise.init(config=TEST_TORTOISE_ORM)
    await Tortoise.generate_schemas()

    _app = _create_test_app()
    # fakeredis: in-process Redis, wire compatible with redis.asyncio.Redis.
    # Production also returns bytes (no decode_responses), so keep the default
    # to match real behavior. No explicit close — nothing to release in-process.
    _app.state.redis = fake_aioredis.FakeRedis()

    yield _app

    await Tortoise.close_connections()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def seed_data(app):
    """Seed roles and users, then populate Redis cache."""
    from app.core.cache import load_role_permissions, refresh_user_roles
    from tests.helpers import seed_roles, seed_super_admin

    await seed_roles()
    user = await seed_super_admin()

    redis = app.state.redis
    await refresh_user_roles(redis, user.id)
    await load_role_permissions(redis)

    return user


@pytest_asyncio.fixture(loop_scope="session")
async def client(app):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac


@pytest_asyncio.fixture(loop_scope="session")
async def auth_client(app, seed_data):
    """Client with valid JWT Authorization header (super admin)."""
    from datetime import UTC, datetime, timedelta

    from app.core.config import APP_SETTINGS
    from app.system.schemas.login import JWTPayload
    from app.system.security import create_access_token

    user = seed_data
    payload = JWTPayload(
        data={"userId": user.id, "userName": user.user_name, "tokenType": "accessToken"},
        iat=datetime.now(UTC),
        exp=datetime.now(UTC) + timedelta(minutes=APP_SETTINGS.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    token = create_access_token(data=payload)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers={"Authorization": f"Bearer {token}"},
    ) as ac:
        yield ac


# ===================== HR Fixtures =====================


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def hr_data(app, seed_data):
    """Seed HR test data: department, tags, employee (linked to super admin)."""
    from app.business.hr.models import Department, Employee, Tag

    user = seed_data

    dept = await Department.create(name="Engineering", code="ENG", description="Engineering Department")
    tag_py = await Tag.create(name="Python", category="Language")
    tag_js = await Tag.create(name="JavaScript", category="Language")

    emp = await Employee.create(
        name=user.nick_name or "Soybean",
        employee_no="EMP0001",
        email="admin@admin.com",
        department=dept,
        user_id=user.id,
    )
    await emp.tags.add(tag_py)

    # Set employee as department manager
    await Department.filter(id=dept.id).update(manager_id=emp.id)

    return {"department": dept, "tags": [tag_py, tag_js], "employee": emp, "user": user}
