import pytest
from httpx import AsyncClient

from app.core.code import Code

pytestmark = pytest.mark.asyncio(loop_scope="session")

PREFIX = "/api/v1/business/hr"


# ===================== Department CRUD =====================


class TestDepartmentCRUD:
    async def test_create_department(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            f"{PREFIX}/departments",
            json={"name": "Marketing", "code": "MKT", "description": "Marketing Dept"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        assert "createdId" in data["data"]

    async def test_list_departments(self, auth_client: AsyncClient, hr_data):
        resp = await auth_client.post(
            f"{PREFIX}/departments/search",
            json={"current": 1, "size": 10},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        assert len(data["data"]["records"]) >= 1

    async def test_list_departments_filter_by_name(self, auth_client: AsyncClient, hr_data):
        resp = await auth_client.post(
            f"{PREFIX}/departments/search",
            json={"current": 1, "size": 10, "name": "Engineering"},
        )
        assert resp.status_code == 200
        records = resp.json()["data"]["records"]
        assert any(r["name"] == "Engineering" for r in records)

    async def test_get_department(self, auth_client: AsyncClient, hr_data):
        dept_id = hr_data["department"].id
        resp = await auth_client.get(f"{PREFIX}/departments/{dept_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        assert data["data"]["code"] == "ENG"

    async def test_update_department(self, auth_client: AsyncClient, hr_data):
        dept_id = hr_data["department"].id
        resp = await auth_client.patch(
            f"{PREFIX}/departments/{dept_id}",
            json={"description": "Updated description"},
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == "0000"

    async def test_delete_department(self, auth_client: AsyncClient):
        # Create a temp department to delete
        create_resp = await auth_client.post(
            f"{PREFIX}/departments",
            json={"name": "TempDept", "code": "TMP"},
        )
        dept_id = create_resp.json()["data"]["createdId"]

        resp = await auth_client.delete(f"{PREFIX}/departments/{dept_id}")
        assert resp.status_code == 200
        assert resp.json()["code"] == "0000"

    async def test_department_stats(self, auth_client: AsyncClient, hr_data):
        resp = await auth_client.get(f"{PREFIX}/departments/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        stats = data["data"]
        assert len(stats) >= 1
        eng = next((s for s in stats if s["code"] == "ENG"), None)
        assert eng is not None
        assert eng["employeeCount"] >= 1


# ===================== Tag CRUD =====================


class TestTagCRUD:
    async def test_create_tag(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            f"{PREFIX}/tags",
            json={"name": "Go", "category": "Language"},
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == "0000"

    async def test_list_tags(self, auth_client: AsyncClient, hr_data):
        resp = await auth_client.post(f"{PREFIX}/tags/search", json={"current": 1, "size": 10})
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        assert len(data["data"]["records"]) >= 2  # Python, JavaScript from seed

    async def test_get_tag(self, auth_client: AsyncClient, hr_data):
        tag_id = hr_data["tags"][0].id
        resp = await auth_client.get(f"{PREFIX}/tags/{tag_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        assert data["data"]["name"] == "Python"

    async def test_update_tag(self, auth_client: AsyncClient, hr_data):
        tag_id = hr_data["tags"][0].id
        resp = await auth_client.patch(
            f"{PREFIX}/tags/{tag_id}",
            json={"description": "Programming language"},
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == "0000"

    async def test_delete_tag(self, auth_client: AsyncClient):
        # Create a temp tag to delete
        create_resp = await auth_client.post(
            f"{PREFIX}/tags",
            json={"name": "TempTag", "category": "Temp"},
        )
        tag_id = create_resp.json()["data"]["createdId"]

        resp = await auth_client.delete(f"{PREFIX}/tags/{tag_id}")
        assert resp.status_code == 200
        assert resp.json()["code"] == "0000"


# ===================== Employee CRUD =====================


class TestEmployeeCRUD:
    async def test_list_employees(self, auth_client: AsyncClient, hr_data):
        """List employees — verifies select_related/prefetch_related returns relations."""
        resp = await auth_client.post(
            f"{PREFIX}/employees/search",
            json={"current": 1, "size": 10},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        records = data["data"]["records"]
        assert len(records) >= 1
        # Verify relations are loaded
        emp = records[0]
        assert "departmentName" in emp
        assert "tagNames" in emp

    async def test_list_employees_filter_by_department(self, auth_client: AsyncClient, hr_data):
        dept_id = hr_data["department"].id
        resp = await auth_client.post(
            f"{PREFIX}/employees/search",
            json={"current": 1, "size": 10, "departmentId": dept_id},
        )
        assert resp.status_code == 200
        records = resp.json()["data"]["records"]
        assert len(records) >= 1

    async def test_create_employee(self, auth_client: AsyncClient, hr_data):
        """Create employee — auto-creates system user."""
        dept_id = hr_data["department"].id
        resp = await auth_client.post(
            f"{PREFIX}/employees",
            json={
                "userName": "13800001111",
                "name": "New Employee",
                "email": "newemp@test.com",
                "departmentId": dept_id,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        assert "employee_id" in data["data"]
        assert "raw_password" in data["data"]
        assert "employee_no" in data["data"]

    async def test_create_employee_no_department(self, auth_client: AsyncClient):
        """Super admin must specify department."""
        resp = await auth_client.post(
            f"{PREFIX}/employees",
            json={
                "userName": "13800002222",
                "name": "NoDept",
                "email": "nodept@test.com",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == Code.HR_DEPARTMENT_REQUIRED

    async def test_get_employee(self, auth_client: AsyncClient, hr_data):
        emp_id = hr_data["employee"].id
        resp = await auth_client.get(f"{PREFIX}/employees/{emp_id}")
        assert resp.status_code == 200
        assert resp.json()["code"] == "0000"

    async def test_update_employee(self, auth_client: AsyncClient, hr_data):
        emp_id = hr_data["employee"].id
        tag_ids = [t.id for t in hr_data["tags"]]
        resp = await auth_client.patch(
            f"{PREFIX}/employees/{emp_id}",
            json={"position": "Senior Engineer", "tagIds": tag_ids},
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == "0000"

    async def test_update_employee_too_many_tags(self, auth_client: AsyncClient, hr_data):
        emp_id = hr_data["employee"].id
        # MAX_TAGS_PER_EMPLOYEE default is 10, send 11 fake ids
        resp = await auth_client.patch(
            f"{PREFIX}/employees/{emp_id}",
            json={"tagIds": list(range(1, 12))},
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == Code.HR_TAGS_EXCEED_LIMIT


# ===================== Manager Operations =====================


class TestManagerOperations:
    async def test_view_department_employees(self, auth_client: AsyncClient, hr_data):
        """Manager views all employees in their department."""
        resp = await auth_client.get(f"{PREFIX}/department/employees")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        records = data["data"]
        assert len(records) >= 1
        assert "tagNames" in records[0]

    async def test_edit_subordinate_tags(self, auth_client: AsyncClient, hr_data):
        """Manager edits a subordinate's tags."""
        emp_id = hr_data["employee"].id
        tag_ids = [t.id for t in hr_data["tags"]]
        resp = await auth_client.patch(
            f"{PREFIX}/department/employees/{emp_id}/tags",
            json={"tagIds": tag_ids},
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == "0000"

    async def test_edit_tags_employee_not_in_dept(self, auth_client: AsyncClient, hr_data):
        """Editing tags of an employee not in the manager's department fails."""
        resp = await auth_client.patch(
            f"{PREFIX}/department/employees/99999/tags",
            json={"tagIds": [hr_data["tags"][0].id]},
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == Code.HR_EMPLOYEE_NOT_IN_DEPT


# ===================== Personal Operations =====================


class TestPersonalOperations:
    async def test_my_profile(self, auth_client: AsyncClient, hr_data):
        """Get own profile with department and tags."""
        resp = await auth_client.get(f"{PREFIX}/my/profile")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        profile = data["data"]
        assert "departmentName" in profile
        assert "tags" in profile

    async def test_my_tags(self, auth_client: AsyncClient, hr_data):
        """Edit own tags."""
        tag_ids = [hr_data["tags"][0].id]
        resp = await auth_client.patch(
            f"{PREFIX}/my/tags",
            json={"tagIds": tag_ids},
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == "0000"

    async def test_my_department(self, auth_client: AsyncClient, hr_data):
        """View colleagues in own department."""
        resp = await auth_client.get(f"{PREFIX}/my/department")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        records = data["data"]
        assert len(records) >= 1
        assert "tagNames" in records[0]

    async def test_my_profile_no_auth(self, client: AsyncClient):
        resp = await client.get(f"{PREFIX}/my/profile")
        assert resp.status_code == 200
        assert resp.json()["code"] == Code.INVALID_TOKEN
