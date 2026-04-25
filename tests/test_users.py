import pytest
from httpx import AsyncClient

from app.core.code import Code

pytestmark = pytest.mark.asyncio(loop_scope="session")


class TestUserList:
    async def test_get_user_list(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/v1/system-manage/users/search",
            json={
                "current": 1,
                "size": 10,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        assert "records" in data["data"]

    async def test_get_user_list_with_filter(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/v1/system-manage/users/search",
            json={
                "current": 1,
                "size": 10,
                "userName": "Soybean",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        records = data["data"]["records"]
        assert len(records) >= 1
        assert any(r["userName"] == "Soybean" for r in records)


class TestUserCRUD:
    async def test_create_user(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/v1/system-manage/users",
            json={
                "userName": "new_test_user",
                "password": "test123456",
                "userEmail": "newtest@test.com",
                "byUserRoleCodeList": ["R_USER"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        assert "createdId" in data["data"]

    async def test_create_user_duplicate_email(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/v1/system-manage/users",
            json={
                "userName": "dup_email_user",
                "password": "test123456",
                "userEmail": "admin@admin.com",
                "byUserRoleCodeList": ["R_USER"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == Code.DUPLICATE_USER_EMAIL

    async def test_create_user_no_email(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/v1/system-manage/users",
            json={
                "userName": "no_email_user",
                "password": "test123456",
                "byUserRoleCodeList": ["R_USER"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == Code.USER_EMAIL_REQUIRED

    async def test_create_user_no_role(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/v1/system-manage/users",
            json={
                "userName": "no_role_user",
                "password": "test123456",
                "userEmail": "norole@test.com",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == Code.USER_ROLE_REQUIRED

    async def test_update_user(self, auth_client: AsyncClient):
        # First create a user to update
        create_resp = await auth_client.post(
            "/api/v1/system-manage/users",
            json={
                "userName": "update_me",
                "password": "test123456",
                "userEmail": "updateme@test.com",
                "byUserRoleCodeList": ["R_USER"],
            },
        )
        user_id = create_resp.json()["data"]["createdId"]

        resp = await auth_client.patch(
            f"/api/v1/system-manage/users/{user_id}",
            json={
                "nickName": "UpdatedNick",
                "password": "newpass123",
                "byUserRoleCodeList": ["R_USER"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"

    async def test_delete_user(self, auth_client: AsyncClient):
        # First create a user to delete
        create_resp = await auth_client.post(
            "/api/v1/system-manage/users",
            json={
                "userName": "delete_me",
                "password": "test123456",
                "userEmail": "deleteme@test.com",
                "byUserRoleCodeList": ["R_USER"],
            },
        )
        user_id = create_resp.json()["data"]["createdId"]

        resp = await auth_client.delete(f"/api/v1/system-manage/users/{user_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
