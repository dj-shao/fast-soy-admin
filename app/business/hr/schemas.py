# pyright: reportIncompatibleVariableOverride=false
"""
Business schema example — 员工、部门、标签的请求/响应 Schema。
"""

from datetime import datetime

from pydantic import Field

from app.business.hr.models import EmployeeStatus
from app.utils import PageQueryBase, SchemaBase, SqidId, StatusType

# ============================================================
# Department
# ============================================================


class DepartmentBase(SchemaBase):
    name: str | None = Field(None, title="部门名称")
    code: str | None = Field(None, title="部门编码")
    description: str | None = Field(None, title="部门描述")
    manager_id: SqidId | None = Field(None, title="主管员工ID")
    status: StatusType | None = Field(None, title="状态")


class DepartmentCreate(DepartmentBase):
    name: str = Field(title="部门名称")
    code: str = Field(title="部门编码")
    parent_id: SqidId | None = Field(0, title="父部门ID，0表示顶级")
    order: int = Field(0, title="排序")
    level: int = Field(1, title="层级深度")


class DepartmentUpdate(DepartmentBase):
    parent_id: SqidId | None = Field(None, title="父部门ID")
    order: int | None = Field(None, title="排序")
    level: int | None = Field(None, title="层级深度")


class DepartmentSearch(DepartmentBase, PageQueryBase):
    parent_id: SqidId | None = Field(None, title="父部门ID")


# ============================================================
# Tag
# ============================================================


class TagBase(SchemaBase):
    name: str | None = Field(None, title="标签名称")
    category: str | None = Field(None, title="标签分类")
    description: str | None = Field(None, title="标签描述")


class TagCreate(TagBase):
    name: str = Field(title="标签名称")
    category: str = Field(title="标签分类")


class TagUpdate(TagBase): ...


class TagSearch(TagBase, PageQueryBase):
    pass


# ============================================================
# Employee
# ============================================================


class EmployeeBase(SchemaBase):
    name: str | None = Field(None, title="员工姓名")
    email: str | None = Field(None, title="邮箱")
    phone: str | None = Field(None, title="电话")
    position: str | None = Field(None, title="职位")
    avatar: str | None = Field(None, title="员工头像URL")
    status: EmployeeStatus | None = Field(None, title="员工状态")


class EmployeeCreate(EmployeeBase):
    user_name: str = Field(title="用户名 (手机号)")
    name: str = Field(title="昵称/姓名")
    email: str = Field(title="邮箱")
    user_gender: str | None = Field(None, title="性别 (1男 2女)")
    department_id: SqidId | None = Field(None, title="部门ID (主管创建时自动继承)")
    tag_ids: list[SqidId] | None = Field(None, title="标签ID列表")


class EmployeeUpdate(EmployeeBase):
    tag_ids: list[SqidId] | None = Field(None, title="标签ID列表")


class TagIds(SchemaBase):
    tag_ids: list[SqidId] = Field(title="标签ID列表")


class MyProfileUpdate(SchemaBase):
    """员工自助维护资料 — 仅暴露电话与邮箱。"""

    phone: str | None = Field(None, title="电话")
    email: str | None = Field(None, title="邮箱")


class EmployeeSearch(EmployeeBase, PageQueryBase):
    department_id: SqidId | None = Field(None, title="部门ID")
    created_at_start: datetime | None = Field(None, title="创建时间起始")
    created_at_end: datetime | None = Field(None, title="创建时间结束")


class EmployeeTransition(SchemaBase):
    """员工状态流转请求"""

    to_state: str = Field(title="目标状态", description="pending / onboarding / active / resigned")
