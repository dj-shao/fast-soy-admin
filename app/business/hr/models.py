# pyright: reportIncompatibleVariableOverride=false
"""
Business model example — 员工、部门、标签。

启用: 去掉文件名 _ 前缀，运行 tortoise makemigrations && tortoise migrate
"""

from enum import Enum

from tortoise import fields

from app.core.base_model import TreeMixin
from app.core.soft_delete import SoftDeleteMixin
from app.utils import AuditMixin, BaseModel, StatusType


class Department(BaseModel, AuditMixin, TreeMixin, SoftDeleteMixin):
    """多级部门（树形）。

    ``parent_id`` / ``order`` / ``level`` 由 ``TreeMixin`` 提供。
    ``deleted_at`` 由 ``SoftDeleteMixin`` 提供。

    PostgreSQL 建议添加部分索引以在软删除下保持唯一::

        CREATE UNIQUE INDEX biz_department_code_active_uq
            ON biz_department(code) WHERE deleted_at IS NULL;
        CREATE UNIQUE INDEX biz_department_name_active_uq
            ON biz_department(name) WHERE deleted_at IS NULL;
    """

    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100, unique=True, description="部门名称")
    code = fields.CharField(max_length=50, unique=True, description="部门编码")
    description = fields.CharField(max_length=500, null=True, blank=True, description="部门描述")
    status = fields.CharEnumField(enum_type=StatusType, default=StatusType.enable, description="状态")

    # 部门主管 → Employee (用 IntField 避免循环 FK)
    manager_id = fields.IntField(null=True, description="部门主管员工ID")

    class Meta:
        table = "biz_department"


class Skill(BaseModel, AuditMixin):
    """标签

    ``category`` 的允许值通过系统字典管理（dict_type="skill_category"），
    前端可通过 ``GET /api/v1/system-manage/dictionaries/skill_category/options`` 获取。
    """

    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100, unique=True, description="标签名称")
    category = fields.CharField(max_length=50, description="标签分类（引用字典 skill_category）")
    description = fields.CharField(max_length=500, null=True, blank=True, description="标签描述")

    class Meta:
        table = "biz_skill"


class EmployeeStatus(str, Enum):
    """员工状态枚举 — 用于状态机流转。

    状态流转规则::

        pending → onboarding → active → resigned
    """

    pending = "pending"
    onboarding = "onboarding"
    active = "active"
    resigned = "resigned"


class Employee(BaseModel, AuditMixin, SoftDeleteMixin):
    """员工

    ``position`` 的允许值通过系统字典管理（dict_type="employee_position"），
    前端可通过 ``GET /api/v1/system-manage/dictionaries/employee_position/options`` 获取。

    PostgreSQL 建议添加部分索引::

        CREATE UNIQUE INDEX biz_employee_no_active_uq
            ON biz_employee(employee_no) WHERE deleted_at IS NULL;
    """

    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=50, description="员工姓名")
    employee_no = fields.CharField(max_length=20, unique=True, description="工号")
    email = fields.CharField(max_length=100, null=True, blank=True, description="邮箱")
    phone = fields.CharField(max_length=20, null=True, blank=True, description="电话")
    position = fields.CharField(max_length=50, null=True, blank=True, description="职位（引用字典 employee_position）")
    status = fields.CharEnumField(enum_type=EmployeeStatus, default=EmployeeStatus.pending, description="员工状态")

    # FK: 员工 → 系统用户 (一对一)
    user: fields.ForeignKeyNullableRelation = fields.ForeignKeyField("app_system.User", null=True, unique=True, on_delete=fields.SET_NULL, related_name="employee", description="关联系统用户")
    # FK: 员工 → 部门
    department: fields.ForeignKeyRelation[Department] = fields.ForeignKeyField("app_system.Department", related_name="employees", description="所属部门")
    # M2M: 员工 ↔ 标签
    skills: fields.ManyToManyRelation[Skill] = fields.ManyToManyField("app_system.Skill", related_name="employees", description="标签列表")

    class Meta:
        table = "biz_employee"
