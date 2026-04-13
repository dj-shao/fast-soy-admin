import pytest
from httpx import AsyncClient

from app.core.code import Code

pytestmark = pytest.mark.asyncio(loop_scope="session")


class TestLogin:
    async def test_login_success(self, client: AsyncClient, seed_data):
        resp = await client.post(
            "/api/v1/auth/login",
            json={
                "userName": "Soybean",
                "password": "123456",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        assert "token" in data["data"]
        assert "refreshToken" in data["data"]

    async def test_login_wrong_password(self, client: AsyncClient, seed_data):
        resp = await client.post(
            "/api/v1/auth/login",
            json={
                "userName": "Soybean",
                "password": "wrong_password",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == Code.WRONG_CREDENTIALS

    async def test_login_nonexistent_user(self, client: AsyncClient, seed_data):
        resp = await client.post(
            "/api/v1/auth/login",
            json={
                "userName": "nonexistent_user_xyz",
                "password": "123456",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == Code.WRONG_CREDENTIALS


class TestRefreshToken:
    async def test_refresh_token_success(self, client: AsyncClient, seed_data):
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "userName": "Soybean",
                "password": "123456",
            },
        )
        tokens = login_resp.json()["data"]

        resp = await client.post(
            "/api/v1/auth/refresh-token",
            json={
                "token": tokens["token"],
                "refreshToken": tokens["refreshToken"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        assert "token" in data["data"]
        assert "refreshToken" in data["data"]

    async def test_refresh_token_invalid(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/refresh-token",
            json={
                "token": "invalid_token",
                "refreshToken": "invalid_token",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == Code.INVALID_TOKEN


class TestUserInfo:
    async def test_get_user_info(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/auth/user-info")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        assert data["data"]["userName"] == "Soybean"
        assert "roles" in data["data"]

    async def test_get_user_info_no_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/user-info")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == Code.INVALID_TOKEN
