import pytest
from httpx import AsyncClient

from app.core.code import Code

pytestmark = pytest.mark.asyncio(loop_scope="session")


class TestMenuList:
    async def test_get_menu_list(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/system-manage/menus/search", json={"current": 1, "size": 100})
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        assert "records" in data["data"]

    async def test_get_menu_tree(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/system-manage/menus/tree")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"

    async def test_get_menu_pages(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/system-manage/menus/pages")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"

    async def test_get_menu_buttons_tree(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/system-manage/menus/buttons/tree")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"


class TestMenuCRUD:
    async def test_create_menu(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/v1/system-manage/menus",
            json={
                "menuName": "TestMenu",
                "menuType": "2",
                "routeName": "test_menu",
                "routePath": "/test-menu",
                "status": "1",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        assert "createdId" in data["data"]

    async def test_create_menu_duplicate_route_path(self, auth_client: AsyncClient):
        # First create
        await auth_client.post(
            "/api/v1/system-manage/menus",
            json={
                "menuName": "DupMenu",
                "menuType": "2",
                "routeName": "dup_menu",
                "routePath": "/dup-menu",
                "status": "1",
            },
        )
        # Duplicate
        resp = await auth_client.post(
            "/api/v1/system-manage/menus",
            json={
                "menuName": "DupMenu2",
                "menuType": "2",
                "routeName": "dup_menu2",
                "routePath": "/dup-menu",
                "status": "1",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == Code.DUPLICATE_MENU_ROUTE

    async def test_update_menu(self, auth_client: AsyncClient):
        # Create
        create_resp = await auth_client.post(
            "/api/v1/system-manage/menus",
            json={
                "menuName": "UpdateMe",
                "menuType": "2",
                "routeName": "update_me_menu",
                "routePath": "/update-me",
                "status": "1",
            },
        )
        menu_id = create_resp.json()["data"]["createdId"]

        resp = await auth_client.patch(
            f"/api/v1/system-manage/menus/{menu_id}",
            json={"menuName": "UpdatedMenu"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"

    async def test_delete_menu(self, auth_client: AsyncClient):
        # Create
        create_resp = await auth_client.post(
            "/api/v1/system-manage/menus",
            json={
                "menuName": "DeleteMe",
                "menuType": "2",
                "routeName": "delete_me_menu",
                "routePath": "/delete-me",
                "status": "1",
            },
        )
        menu_id = create_resp.json()["data"]["createdId"]

        resp = await auth_client.delete(f"/api/v1/system-manage/menus/{menu_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"

    async def test_menu_no_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/system-manage/menus/search", json={"current": 1, "size": 10})
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == Code.INVALID_TOKEN
