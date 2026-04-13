import pytest
from httpx import AsyncClient

from app.core.code import Code
from app.system.models import Menu

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture
async def home_menu_id(seed_data) -> int:
    menu = await Menu.filter(route_name="home").first()
    assert menu is not None
    return menu.id


class TestRoleList:
    async def test_get_role_list(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/v1/system-manage/roles/search",
            json={
                "current": 1,
                "size": 10,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        assert "records" in data["data"]
        assert len(data["data"]["records"]) >= 3  # R_SUPER, R_ADMIN, R_USER

    async def test_get_role_list_filter_by_name(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/v1/system-manage/roles/search",
            json={
                "current": 1,
                "size": 10,
                "roleName": "超级",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        records = data["data"]["records"]
        assert len(records) >= 1


class TestRoleCRUD:
    async def test_create_role(self, auth_client: AsyncClient, home_menu_id: int):
        resp = await auth_client.post(
            "/api/v1/system-manage/roles",
            json={
                "roleName": "测试角色",
                "roleCode": "R_TEST",
                "roleDesc": "测试角色描述",
                "byRoleHomeId": home_menu_id,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        assert "createdId" in data["data"]

    async def test_create_role_duplicate_code(self, auth_client: AsyncClient, home_menu_id: int):
        # R_SUPER already exists
        resp = await auth_client.post(
            "/api/v1/system-manage/roles",
            json={
                "roleName": "重复角色",
                "roleCode": "R_SUPER",
                "roleDesc": "重复",
                "byRoleHomeId": home_menu_id,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == Code.DUPLICATE_ROLE_CODE

    async def test_get_role(self, auth_client: AsyncClient, seed_data):
        from app.system.controllers import role_controller

        role = await role_controller.get_by_code("R_SUPER")
        assert role is not None
        resp = await auth_client.get(f"/api/v1/system-manage/roles/{role.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        assert data["data"]["roleCode"] == "R_SUPER"

    async def test_update_role(self, auth_client: AsyncClient, home_menu_id: int):
        # Create a role first
        create_resp = await auth_client.post(
            "/api/v1/system-manage/roles",
            json={
                "roleName": "待更新角色",
                "roleCode": "R_UPDATE_TEST",
                "roleDesc": "待更新",
                "byRoleHomeId": home_menu_id,
            },
        )
        role_id = create_resp.json()["data"]["createdId"]

        resp = await auth_client.patch(
            f"/api/v1/system-manage/roles/{role_id}",
            json={
                "roleDesc": "已更新描述",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"

    async def test_delete_role(self, auth_client: AsyncClient, home_menu_id: int):
        # Create a role first
        create_resp = await auth_client.post(
            "/api/v1/system-manage/roles",
            json={
                "roleName": "待删除角色",
                "roleCode": "R_DELETE_TEST",
                "roleDesc": "待删除",
                "byRoleHomeId": home_menu_id,
            },
        )
        role_id = create_resp.json()["data"]["createdId"]

        resp = await auth_client.delete(f"/api/v1/system-manage/roles/{role_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"

    async def test_get_role_list_no_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/system-manage/roles/search", json={"current": 1, "size": 10})
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == Code.INVALID_TOKEN
